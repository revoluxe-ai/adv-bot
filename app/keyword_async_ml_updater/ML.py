import datetime
import os.path
import typing
from . import data_managers
import joblib
import xgboost

import settings
import asyncio
import logging
from ast import literal_eval
from app.session_maker import get_async_session_maker
import sqlalchemy
import numpy as np
import pandas as pd
from sklearn.model_selection import  cross_validate, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import sessionmaker, joinedload, selectinload
from xgboost import XGBRegressor
from sqlalchemy import select, and_
from app.wildberries.models import AdvSetting, WBCard, WBCategory, KeywordSetting
from app.keyword_async_ml_updater.models import KeywordFeature, ItemFeature
import json

from .data_managers import DataGetter
from app.keyword_async_ml_updater.ABC_manager import AbcManager
fit_logger = logging.getLogger('fit_logger')

sm = get_async_session_maker()

logger = logging.getLogger(__name__)


model_folder = 'app/keyword_async_ml_updater/model'


global_model: typing.Union[xgboost.XGBModel, None] = None

path = 'app/keyword_async_ml_updater/model/'

def save_model(model: xgboost.XGBModel, time_stamp = None):
    model_path = os.path.join(path, 'model.json')
    joblib.dump(model, model_path)

    if time_stamp:
        with open(f'{path}/time_stamp.txt', 'w') as file:
            file.write(time_stamp)

def load_model():
    model = joblib.load(os.path.join(path, 'model.json'))
    # with open(f'{path}/time_stamp.txt', 'r') as file:
    #     time_stamp = file.read()
    return model



class Fitter(AbcManager):

    data_getter = DataGetter()


    @staticmethod
    def __get_average_vector(nmids:str, df_vectors):
        nmids = literal_eval(nmids)
        vectors = df_vectors[df_vectors['nmid'].isin(nmids)].iloc[:,
                  1:].values  # Предполагаем, что векторы начинаются с 2-го столбца
        if vectors.size == 0:
            return None
        return np.mean(vectors, axis=0)

    def fill_average_vector(self, df_stat: pd.DataFrame, df_vectors: pd.DataFrame):
        # Вычисляем средние векторы, исключая None
        averaged_vectors = df_stat['nmids'].apply(
            lambda nmids: self.__get_average_vector(nmids, df_vectors)).dropna()

        # Находим первый не None вектор для определения длины вектора
        first_valid_vector = next((vec for vec in averaged_vectors if vec is not None), None)
        vector_length = len(first_valid_vector) if first_valid_vector is not None else 0

        # Обрабатываем случаи с None, заменяя их на список None соответствующей длины
        averaged_vectors = averaged_vectors.apply(
            lambda x: x if x is not None else [None] * vector_length)

        # Создаем DataFrame для новых столбцов, учитывая возможные None значения
        new_columns_data = {}
        for i in range(vector_length):
            new_columns_data[f'item_f_{i}'] = averaged_vectors.apply(lambda x: x[i] if x is not None else None)

        new_columns_df = pd.DataFrame(new_columns_data)

        # Объединяем новые столбцы с df_stat и удаляем строки с None в новых столбцах
        df_items_keywords_stat = pd.concat([df_stat.reset_index(drop=True), new_columns_df.reset_index(drop=True)],
                                           axis=1).dropna(subset=[f'item_f_{i}' for i in range(vector_length)])

        return df_items_keywords_stat



    def __read_files_for_fit(self):
        # Загрузка данных
        df_items_keywords_stat = pd.read_csv(self.keyword_stat_df_path)
        fit_logger.debug('Данные загружены')
        df_nmids_vectors = pd.read_csv(self.nmids_vectors_path)
        df_keyword_vectors = pd.read_csv(self.keywords_vectors_path)
        df_items_keywords_stat = self.fill_average_vector(df_items_keywords_stat, df_nmids_vectors)
        # Объединение с df_keyword_vectors
        df_final = df_items_keywords_stat.merge(df_keyword_vectors, how='left', on='keyword')

        return df_final

    async def getGradientBoostingFullFitModel(self, update_model_on_new_features):
        await self._fit_modelGradientBoosting(update_model_on_new_features)
        fit_logger.debug('Модель обучена')


    def _get_enough_views(self, ctr):
         return int(1/ctr)



    async def _bayesian_apply(self, df: pd.DataFrame):
        category_name_to_min_ctr = await data_managers.get_category_name_min_ctr_final_data()
        def calculate_ctr(row):
            clicks = row['clicks']
            views = row['views']
            wb_category_name = row['wb_category_name']
            min_ctr = category_name_to_min_ctr.get(wb_category_name, 0)
            if min_ctr > 0:
                 enough_views = self._get_enough_views(min_ctr)
            else:
                if views > 0:
                    return clicks / views
                else:
                    return 0
            clicks = clicks + 1
            views = views + enough_views
            ctr = clicks / views
            return ctr
        # Предположим, что adv_id_to_min_ctr - это ваш словарь с минимальными CTR для каждого adv_id
        df['ctr'] = df.apply(calculate_ctr, axis=1)
        return df

    async def _get_df_for_fit(self)-> pd.DataFrame:
        keyword_text_keyword_features = {}
        async with sm() as sess:
            result = await sess.execute(
                select(AdvSetting)
                .options(
                    selectinload(AdvSetting.adv_keywords),
                    # Убедитесь, что есть связь для wb_cards и wb_category, и что они правильно определены в моделях
                    selectinload(AdvSetting.wb_cards).selectinload(WBCard.wb_category),
                    selectinload(AdvSetting.keyword_settings).selectinload(KeywordSetting.adv_keywords),
                )
            )
            # Используйте unique() для удаления дубликатов перед получением списка объектов
            adv_settings = result.scalars().unique().all()

        data_rows = []
        for adv in adv_settings:
            wb_category = await data_managers.get_wb_category(adv)
            nmid_featers = {}
            keyword_stats = await data_managers.get_keyword_statistic(adv)
            keyword_text_to_keyword_stat = {}
            for keyword_stat in keyword_stats:
                keyword_text_to_keyword_stat[keyword_stat.text] = keyword_stat
            item_features_list = []
            for nmid in adv.nmids:
                if nmid in nmid_featers:
                    item_feature = nmid_featers[nmid]
                else:
                    async with sm() as session:
                        item_feature = await session.execute(
                            select(ItemFeature).where(ItemFeature.nmid == nmid)
                        )
                        item_feature = item_feature.scalars().one()
                    nmid_featers[nmid] = item_feature
                if item_feature:
                    item_features_list.append(item_feature.vector)
            if not item_features_list:
                continue

            # Вычисляем средние значения фичей товаров, если они есть

            avg_item_features = pd.DataFrame(item_features_list).mean().to_dict()
            avg_item_features = {f'item_feature_{i}': avg_item_features[i] for i in avg_item_features.keys()}

            keyword_settings: list[KeywordSetting] = adv.keyword_settings

            for keyword_setting in keyword_settings:
                text = keyword_setting.text
                if text in keyword_text_keyword_features:
                    keyword_feature = keyword_text_keyword_features[text]
                else:
                    async with sm() as sess:
                        keyword_feature = await sess.execute(
                            select(KeywordFeature).where(KeywordFeature.keyword == text)
                        )
                        keyword_feature = keyword_feature.scalars().first()
                    keyword_text_keyword_features[text] = keyword_feature
                if not keyword_feature:
                    continue
                keyword_features = keyword_feature.vector
                keyword_stat = keyword_text_to_keyword_stat.get(text)
                if keyword_stat:
                    row = {
                        'adv_id': adv.adv_id,
                        'keyword': keyword_setting.text,
                        'views': keyword_stat.views,
                        'clicks': keyword_stat.clicks,
                        'spend': keyword_stat.spend,
                        'nmids': adv.nmids,
                        'wb_category_name': wb_category.wb_category_name,
                        **avg_item_features,
                        **{f'keyword_feature_{i}': keyword_features[i] for i in  range(len(keyword_features))},
                    }
                    data_rows.append(row)


        df = pd.DataFrame(data_rows)
        if len(df) > 0:
            df = df[df.views > 0]
            df['ctr'] = df['clicks'] / df['views']
        return df

    async def _fit_modelGradientBoosting(self, update_model_on_new_features):
        fit_logger.debug('Поток обучения запущен, получение данных')
        df = await self._get_df_for_fit()
        fit_logger.debug('Данные получены')
        if len(df) == 0:
            logger.debug('Нет данных для обучения')
            return
        df:pd.DataFrame = await self._bayesian_apply(df)
        await asyncio.to_thread(df.to_csv, 'work_folder/df_for_fit.csv', index=False)
        y = df['ctr']
        X = df.drop(['keyword', 'views', 'ctr', 'clicks', 'adv_id', 'spend', 'nmids', 'wb_category_name'],
                    axis=1)
        fit_logger.debug('Данные подготовлены')
        # Создание модели градиентного бустинга
        model = make_pipeline(StandardScaler(), XGBRegressor(n_jobs=-1))
        if settings.cv:
            fit_logger.debug('Начало кросс-валидации')
            cv = KFold(n_splits=5, random_state=42, shuffle=True)
            scores = cross_validate(model, X, y, scoring='neg_mean_squared_error', cv=cv)
            fit_logger.debug('Кросс-валидация завершена')
            mse_scores = -scores['test_score']
            # Вычисление и вывод метрик
            mean_mse = mse_scores.mean()
            std_dev_mse = mse_scores.std()
            max_difference = mse_scores.max() - mse_scores.min()

            print("CV MSE scores:", mse_scores)
            print(f"Mean CV MSE: {mean_mse}")
            print(f"Standard Deviation of CV MSE: {std_dev_mse}")
            print(f"Max difference between CV MSE scores: {max_difference}")
        fit_logger.debug('Обучение модели на полных данных')
        model.fit(X, y)
        fit_logger.debug('Модель обучена')
        model = typing.cast(xgboost.XGBModel, model.named_steps['xgbregressor'])
        await asyncio.to_thread(save_model, model, time_stamp= None)
        update_model_on_new_features.set()



class Predictor:

    def _predict(self, df: pd.DataFrame)-> typing.Union[pd.DataFrame, None]:
        model = load_model()
        X = df.drop(['keyword', 'adv_id'], axis=1)
        y = model.predict(X)
        df['predicted_ctr'] = y
        return df

    async def predict_ctr_for_keywords(self,  predicted: asyncio.Event):

        async with sm() as session:
            stmt = select(AdvSetting).options(
                selectinload(AdvSetting.adv_keywords),
                selectinload(AdvSetting.keyword_settings)
            )
            result = await session.execute(stmt)
            all_adv_settings = result.scalars().unique().all()

        predicted.clear()
        async with sm() as session:
            df_for_predict = await self._get_df_for_predict(all_adv_settings, session)
        predict_df = await asyncio.to_thread(self._predict, df_for_predict)
        predict_df['predicted_ctr'] = predict_df['predicted_ctr'].apply(lambda ctr: ctr if ctr >=0 else 0)
        await asyncio.to_thread(predict_df.to_csv, 'work_folder/предсказания.csv')
        async with sm() as session:
            for n, row in predict_df.iterrows():
                adv_id = row['adv_id']
                keyword = row['keyword']
                predict_ctr = row['predicted_ctr']
                stmt = select(KeywordSetting).join(
                    AdvSetting, KeywordSetting.adv_setting
                ).filter(
                    and_(
                        KeywordSetting.text == keyword,
                        AdvSetting.adv_id == adv_id  # Используйте AdvSetting.adv_id напрямую
                    )
                )
                result = await session.execute(stmt)
                keyword_setting = result.scalar()
                keyword_setting.predict_ctr = predict_ctr
            await session.commit()
            logger.debug('Предсказания обновлены')






    async def _get_df_for_predict(self, adv_settings: list[AdvSetting], session)-> pd.DataFrame:
       data_rows = []
       for adv in adv_settings:
           item_features_list = []
           for nmid in adv.nmids:
               item_feature = await session.execute(
                   select(ItemFeature).where(ItemFeature.nmid == nmid)
               )
               item_features = item_feature.scalars().all()
               for item_feature in item_features:
                   item_features_list.append(item_feature.vector)

           # Вычисляем средние значения фичей товаров, если они есть

           avg_item_features = pd.DataFrame(item_features_list).mean().to_dict()
           avg_item_features = {f'item_feature_{i}': avg_item_features[i] for i in avg_item_features.keys()}

           for keyword in adv.keyword_settings:
               keyword_feature = await session.execute(
                   select(KeywordFeature).where(KeywordFeature.keyword == keyword.text)
               )
               keyword_feature = keyword_feature.scalars().first()
               if not keyword_feature:
                   continue
               keyword_features = keyword_feature.vector



               row = {
                   'adv_id': adv.adv_id,
                   'keyword': keyword.text,
                   **avg_item_features,
                   **{f'keyword_feature_{i}': keyword_features[i] for i in range(len(keyword_features))},
               }
               data_rows.append(row)

       df = pd.DataFrame(data_rows)
       return df







