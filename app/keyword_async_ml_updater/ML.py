import datetime
import typing
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
from sqlalchemy import select
from app.wildberries.models import AdvSetting, WBCard, WBCategory
from app.keyword_async_ml_updater.models import KeywordFeature, ItemFeature
import json

from .data_managers import DataGetter
from app.keyword_async_ml_updater.ABC_manager import AbcManager
fit_logger = logging.getLogger('fit_logger')

sm = get_async_session_maker()


model_folder = 'app/keyword_async_ml_updater/model'


global_model: typing.Union[xgboost.XGBModel, None] = None


def save_model(model: xgboost.XGBModel, time_stamp, path):
    model.save_model('app/keyword_async_ml_updater/model')
    with open(f'{path}/time_stamp.txt', 'w') as file:
        file.write(time_stamp)


class Fitter(AbcManager):

    data_getter = DataGetter()

    def __init__(self):

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

    async def getGradientBoostingFullFitModel(self):
        model = await self._fit_modelGradientBoosting()
        fit_logger.debug('Модель обучена')
        return model

    def _get_enough_views(self, ctr, n):
         return int(1/ctr/n)



    async def get_min_str_settings(self):
        async with sm() as session:  # session: AsyncSession
            result = await session.execute(
                select(AdvSetting).options(selectinload(AdvSetting.wb_cabinet),
                                           selectinload(AdvSetting.wb_cards))
            )
            settings = result.scalars().all()
        adv_id_min_ctr = {}
        shop_category_min_ctr = {}

        for setting in settings:
            min_ctr = setting.min_ctr
            if min_ctr:
                adv_id_min_ctr[setting.adv_id] = min_ctr
            wb_category_name = setting.wb_category_name
            cabinet = setting.wb_cabinet
            if cabinet not in shop_category_min_ctr:
                shop_category_min_ctr[cabinet] = {}
            if wb_category_name not in shop_category_min_ctr[cabinet]:
                shop_category_min_ctr[cabinet][wb_category_name] = []
            shop_category_min_ctr[cabinet][wb_category_name].append(setting.min_ctr)


        for cabinet in shop_category_min_ctr:
            for wb_category_name in shop_category_min_ctr[cabinet]:
                min_ctrs = shop_category_min_ctr[cabinet][wb_category_name]
                min_ctrs = [ctr for ctr in min_ctrs if ctr is not None]
                avg_min_ctr = sum(min_ctrs) / len(min_ctrs) if min_ctrs else 0
                shop_category_min_ctr[cabinet][wb_category_name] = avg_min_ctr
        shop_avg_min_ctr = {}
        for cabinet in shop_category_min_ctr:
            category_avg_ctrs = list(shop_category_min_ctr[cabinet].values())
            shop_avg_min_ctr[cabinet] = sum(category_avg_ctrs) / len(category_avg_ctrs)

        # Вычисление общего среднего ctr
        global_base_ctr = 5
        all_avg_ctrs = list(shop_avg_min_ctr.values())
        overall_avg_ctr = sum(all_avg_ctrs) / len(all_avg_ctrs)/100 if all_avg_ctrs else global_base_ctr/100
        async with sm() as session:  # session: AsyncSession
            result = await session.execute(
                select(WBCard).options(selectinload(WBCard.wb_cabinet))
            )
            wbcards:list[WBCard] = result.scalars().all()

        nmid_cabitet_category_refs = {}
        for card in wbcards:
            wb_category: WBCategory = card.wb_category
            nmid_cabitet_category_refs[card.nmid] = {'cabinet': card.wb_cabinet,
                                                     'wb_category_name': wb_category.wb_category_name}

        return adv_id_min_ctr, shop_category_min_ctr, shop_avg_min_ctr, overall_avg_ctr, nmid_cabitet_category_refs



    async def _bayesian_apply(self, df: pd.DataFrame):
        adv_id_min_ctr, shop_category_min_ctr, shop_avg_min_ctr, overall_avg_ctr, nmid_cabitet_category_refs = \
            await self.get_min_str_settings()
        def get_min_ctr(adv_id, nmids):
            nmid = nmids[0]
            if nmid not in nmid_cabitet_category_refs:
                return overall_avg_ctr
            if adv_id in adv_id_min_ctr:
                return adv_id_min_ctr[adv_id]
            cabinet = nmid_cabitet_category_refs[nmid]['cabinet']
            wb_category_name =  nmid_cabitet_category_refs[nmid]['wb_category_name']
            if cabinet in shop_category_min_ctr and wb_category_name in shop_category_min_ctr[cabinet]:
                return shop_category_min_ctr[cabinet][wb_category_name]
            if cabinet in shop_avg_min_ctr:
                return shop_avg_min_ctr[cabinet]
            return overall_avg_ctr

        def calculate_ctr(row):
            adv_id = row['adv_id']
            clicks = row['clicks']
            views = row['views']
            nmids = row['nmids']
            min_ctr = get_min_ctr(adv_id, nmids)  # default_min_ctr - значение CTR по умолчанию
            enough_views = self._get_enough_views(min_ctr, 1.1)
            clicks = clicks + 1
            views = views + enough_views
            ctr = clicks / views
            return ctr

        # Предположим, что adv_id_to_min_ctr - это ваш словарь с минимальными CTR для каждого adv_id
        df['ctr'] = df.apply(calculate_ctr, axis=1)

        return df

    async def _get_df_for_fit(self)-> (pd.DataFrame, str):
        async with sm() as sess:
            adv_settings = await sess.execute(
                select(AdvSetting).options(joinedload(AdvSetting.adv_keywords))
            )
            adv_settings = adv_settings.scalars().unique().all()

            data_rows = []

            time_stamp = None

            for adv in adv_settings:
                item_features_list = []
                for nmid in adv.nmids:
                    item_feature = await sess.execute(
                        select(ItemFeature).where(ItemFeature.nmid == nmid)
                    )
                    item_features = item_feature.scalars().all()
                    for item_feature in item_features:
                        if time_stamp is None:
                            time_stamp = item_feature.timestamp
                        else:
                            assert time_stamp == item_feature.timestamp
                        item_features_list.append(item_feature.vector)

                # Вычисляем средние значения фичей товаров, если они есть

                avg_item_features = pd.DataFrame(item_features_list).mean().to_dict()
                avg_item_features = {f'item_feature_{i}': avg_item_features[i] for i in avg_item_features.keys()}


                for keyword in adv.adv_keywords:
                    assert time_stamp == keyword.timestamp
                    keyword_feature = await sess.execute(
                        select(KeywordFeature).where(KeywordFeature.keyword == keyword.text)
                    )
                    keyword_feature = keyword_feature.scalars().first()
                    keyword_features = keyword_feature.vector

                    row = {
                        'adv_id': adv.adv_id,
                        'keyword': keyword.text,
                        'views': keyword.views,
                        'clicks': keyword.clicks,
                        'spend': keyword.spend,
                        'real_ctr': keyword.real_ctr,
                        'nmids': adv.nmids,
                        **avg_item_features,
                        **{f'keyword_feature_{i}': keyword_features[i] for i in  range(len(keyword_features))},
                    }
                    data_rows.append(row)

        df = pd.DataFrame(data_rows)
        df = df[df.views > 0]
        df['ctr'] = df['clicks'] / df['views']
        return df, time_stamp



    async def _fit_modelGradientBoosting(self):
        fit_logger.debug('Поток обучения запущен, получение данных')
        df, timestamp_str = await self._get_df_for_fit()
        fit_logger.debug('Данные получены')
        df:pd.DataFrame = await self._bayesian_apply(df)
        await asyncio.to_thread(df.to_csv,'work_folder/df_for_fit.csv', index=False)
        y = df['ctr']
        X = df.drop(['nmids', 'keyword', 'views', 'ctr', 'clicks', 'spend', 'adv_id'], axis=1)
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
        global_model = model
        await asyncio.to_thread(save_model, model, timestamp_str, self.model_path)




class Predictor:
    def predict(self, df: pd.DataFrame):
        X = df.drop(['keyword', 'adv_id'], axis=1)
        y = global_model.predict(X)
        df['predicted_ctr'] = y
        return df







