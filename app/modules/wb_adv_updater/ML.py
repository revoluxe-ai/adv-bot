import asyncio
import logging
import os.path
import typing
from ast import literal_eval
import joblib
import xgboost

from ..common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from ... import settings
from app.admin_bot.sender import sender_manager
from app.modules.wb_adv_updater.ABC_manager import AbcManager
from app.utils.db.session_maker import get_async_session_maker
import numpy as np
import pandas as pd
from sklearn.model_selection import  cross_validate, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import selectinload
from xgboost import XGBRegressor
from sqlalchemy import select, and_
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCard, KeywordSetting
from app.modules.wb_adv_updater.models import KeywordFeature, ItemFeature
from . import data_manager
from .data_manager import DataGetter
from ...exc import CardNotFoundInDB
from ...utils import redis_manager
from ...utils.redis_manager import RedisEvent

sm = get_async_session_maker

logger = logging.getLogger(__name__)

global_model: typing.Union[xgboost.XGBModel, None] = None

path = 'model'

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




    async def getGradientBoostingFullFitModel(self, update_model_on_new_features):
        await self._fit_modelGradientBoosting(update_model_on_new_features)
        logger.debug('Модель обучена')


    def _get_enough_views(self, ctr):
         return int(1/ctr)

    async def _bayesian_apply(self, df: pd.DataFrame):

        adv_ids = df['adv_id'].unique()

        adv_id_keyword_text_to_status: dict[(int, 'str'), int] = await data_manager.get_adv_id_keyword_text_to_status(adv_ids)

        adv_id_to_min_ctr: dict[int, float] = await data_manager.get_adv_id_to_min_ctr(adv_ids)
        def calculate_ctr(row):
            clicks = row['clicks']
            views = row['views']
            adv_id = row['adv_id']
            status = adv_id_keyword_text_to_status[(adv_id, row['keyword'])]
            if status == 0:
                return 0
            elif status in [2, 3]:
                return 1
            else:
                if clicks == 0:
                    min_ctr = adv_id_to_min_ctr[adv_id]
                    if min_ctr > 0:
                         enough_views = self._get_enough_views(min_ctr)
                    else:
                         return clicks / views

                    clicks = clicks + 1
                    views = views + enough_views
                    ctr = clicks / views
                    return ctr
                else:
                    return clicks / views
        # Предположим, что adv_id_to_min_ctr - это ваш словарь с минимальными CTR для каждого adv_id
        df['ctr'] = df.apply(calculate_ctr, axis=1)
        return df

    @staticmethod
    async def __fetch_keyword_features(session, keywords):
        keyword_to_features = {}
        # Определение размера батча (например, 100 элементов)
        batch_size = 100
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i + batch_size]
            result = await session.execute(
                select(KeywordFeature).where(KeywordFeature.keyword.in_(batch))
            )
            for kf in result.scalars().all():
                keyword_to_features[kf.keyword] = kf.vector
        return keyword_to_features

    async def _get_df_for_fit(self) -> pd.DataFrame:
        data_rows = []
        async with sm() as session:
            stmt = select(AdvSetting) \
                .options(selectinload(AdvSetting.keyword_settings))\
            .where(AdvSetting.bot_active == True,
                   AdvSetting.active_status == 'started')
            result = await session.execute(stmt)
            adv_settings = result.scalars().all()

        logger.debug(f'Всего кампаний: {len(adv_settings)}')

        # Собираем уникальные nmids и keywords для запросов
        nmids_batch = set()
        keywords_batch = set()
        for adv in adv_settings:
            if adv.nmids:
                nmids_batch.update(adv.nmids)
                if adv.keyword_settings:
                    keywords_batch.update([ks.text for ks in adv.keyword_settings])
                    await asyncio.sleep(0)

        # Получаем все необходимые ItemFeature и KeywordFeature в одном запросе
        nmid_to_item_features = {}
        keyword_to_features = {}
        if nmids_batch:
            async with sm() as session:
                item_features_result = await session.execute(
                    select(ItemFeature).where(ItemFeature.nmid.in_(nmids_batch))
                )
                nmid_to_item_features = {item_feature.nmid: item_feature.vector for item_feature in
                                         item_features_result.scalars().all()}

        if keywords_batch:
            async with sm() as session:
                keyword_to_features = await self.__fetch_keyword_features(session, list(keywords_batch))

        for adv in adv_settings:
            try:
                wb_category = await data_manager.get_wb_category(adv)
            except (CardNotFoundInDB, NotItemsInAdvSetting) as exc:
                logger.debug(f"Не удалось получить категорию РК {exc}")
                await asyncio.sleep(0)
                continue
            keyword_stats = await data_manager.get_keywords_statistic(adv, None)
            keyword_stat_dict = {stat.text: stat for stat in keyword_stats}

            if not adv.nmids:
                await asyncio.sleep(0)
                continue
            item_features_list = [nmid_to_item_features.get(nmid) for nmid in adv.nmids if
                                  nmid in nmid_to_item_features]
            if not item_features_list:
                await asyncio.sleep(0)
                continue

            avg_item_features = pd.DataFrame(item_features_list).mean().to_dict()
            avg_item_features = {f'item_feature_{i}': avg_item_features[i] for i in avg_item_features.keys()}

            for keyword_setting in adv.keyword_settings:
                text = keyword_setting.text
                text = text.replace('_', ' ')
                keyword_features = keyword_to_features.get(text)
                if not keyword_features:
                    logger.debug(f'Нет фичи для ключевого слова {keyword_setting.text}')
                    await asyncio.sleep(0)
                    continue

                keyword_stat = keyword_stat_dict.get(keyword_setting.text)
                if not keyword_stat:
                    await asyncio.sleep(0)
                    continue

                row = {
                    'adv_id': adv.adv_id,
                    'adv_type': adv.type,
                    'keyword': keyword_setting.text,
                    'views': keyword_stat.views,
                    'clicks': keyword_stat.clicks,
                    'spend': keyword_stat.spend,
                    'nmids': adv.nmids,
                    'wb_category_name': wb_category.wb_category_name,
                    **avg_item_features,
                    **{f'keyword_feature_{i}': keyword_features[i] for i in range(len(keyword_features))}
                }
                data_rows.append(row)
                await asyncio.sleep(0)

        df = pd.DataFrame(data_rows)
        if df.empty:
            return df

        df = df[df.views > 0]
        df['ctr'] = df['clicks'] / df['views']
        return df





    async def _fit_modelGradientBoosting(self, update_model_on_new_features):
        logger.debug('Поток обучения запущен, получение данных')
        df = await self._get_df_for_fit()
        logger.debug('Данные получены')
        if len(df) == 0:
            logger.info('Нет данных для обучения')
            return
        df:pd.DataFrame = await self._bayesian_apply(df)
        await asyncio.to_thread(df.to_csv, 'work_folder/df_for_fit.csv', index=False)
        y = df['ctr']
        X = df.drop(['keyword', 'views', 'ctr', 'clicks', 'adv_id', 'spend', 'nmids', 'wb_category_name'],
                    axis=1)
        logger.debug('Данные подготовлены')
        # Создание модели градиентного бустинга
        model = make_pipeline(StandardScaler(), XGBRegressor(n_jobs=-1))
        if settings.cv:
            logger.debug('Начало кросс-валидации')
            cv = KFold(n_splits=5, random_state=42, shuffle=True)
            scores = cross_validate(model, X, y, scoring='neg_mean_squared_error', cv=cv)
            logger.debug('Кросс-валидация завершена')
            mse_scores = -scores['test_score']
            # Вычисление и вывод метрик
            mean_mse = mse_scores.mean()
            std_dev_mse = mse_scores.std()
            max_difference = mse_scores.max() - mse_scores.min()

            logger.info(f"CV MSE scores: {mse_scores}\n"
            f"Mean CV MSE: {mean_mse}\n"
            f"Standard Deviation of CV MSE: {std_dev_mse}\n"
            f"Max difference between CV MSE scores: {max_difference}\n"
            )
        logger.debug('Обучение модели на полных данных')
        model.fit(X, y)
        logger.debug('Модель обучена')
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

    async def predict_ctr_for_keywords(self,  predicted: RedisEvent):
        async with sm() as session:
            stmt = select(AdvSetting).options(
                selectinload(AdvSetting.adv_keywords),
                selectinload(AdvSetting.keyword_settings)
            ).where(AdvSetting.bot_active == True,
                    AdvSetting.active_status == 'started')
            result = await session.execute(stmt)
            all_adv_settings = result.scalars().unique().all()
        adv_id_to_adv_setting = {adv.adv_id: adv for adv in all_adv_settings}
        await predicted.clear()

        df_for_predict = await self._get_df_for_predict(all_adv_settings)
        predict_df = await asyncio.to_thread(self._predict, df_for_predict)
        predict_df['predicted_ctr'] = predict_df['predicted_ctr'].apply(lambda ctr: ctr if ctr >=0 else 0)
        await asyncio.to_thread(predict_df.to_csv, 'work_folder/предсказания.csv')
        for n, row in predict_df.iterrows():
            adv_id = row['adv_id']
            keyword = row['keyword']
            predict_ctr = row['predicted_ctr']
            adv = adv_id_to_adv_setting[adv_id]
            min_ctr = await data_manager.get_min_ctr(adv)
            enough_views = int(1/min_ctr)
            async with sm() as session:
                stmt = select(KeywordSetting).where(and_(KeywordSetting.adv_setting_id == adv.id,
                                                            KeywordSetting.text == keyword))
                keyword_setting = await session.execute(stmt)
                keyword_setting = keyword_setting.scalar()
            clicks, views, _ = await data_manager.get_keyword_statistic(keyword_setting)
            if clicks > 0:
                real_ctr = clicks / views

            else:
                clicks = 1
                views += enough_views
            real_ctr = clicks / views
            predict_ctr = (real_ctr + predict_ctr) / 2

            await redis_manager.set_predict_ctr(adv_id, keyword, predict_ctr)
        await  asyncio.sleep(0)
        logger.debug('Предсказания обновлены')






    async def _get_df_for_predict(self, adv_settings: list[AdvSetting])-> pd.DataFrame:
       data_rows = []
       async with sm() as session:
           for adv in adv_settings:
               logger.debug(f'Обработка кампании {adv.name}')
               if not adv.nmids:
                   logger.debug('Нет nmids: %s', adv.name)
                   continue
               nmids = adv.nmids
               item_features = await session.execute(
                   select(ItemFeature).where(ItemFeature.nmid.in_(nmids))
               )
               item_features = item_features.scalars().all()

               item_features = [item_feature.vector for item_feature in item_features]

               avg_item_features = pd.DataFrame(item_features).mean().to_dict()
               avg_item_features = {f'item_feature_{i}': avg_item_features[i] for i in avg_item_features.keys()}

               if not avg_item_features:
                     logger.error('Нет item_features: %s', adv.name)
                     continue
               clear_keywords = [keyword.text.replace('_', ' ') for keyword in adv.keyword_settings]

               # Выполняем один запрос, чтобы получить все KeywordFeature объекты для этих ключевых слов
               keyword_features_result = await session.execute(
                   select(KeywordFeature).where(KeywordFeature.keyword.in_(clear_keywords))
               )
               keyword_features_list = keyword_features_result.scalars().all()

               # Преобразуем список объектов KeywordFeature в словарь для быстрого доступа
               keyword_features_dict = {kf.keyword: kf.vector for kf in keyword_features_list}

               for keyword in adv.keyword_settings:
                   text = keyword.text.replace('_', ' ')
                   keyword_features = keyword_features_dict.get(text)
                   if not keyword_features:
                       continue

                   # Собираем данные для строки
                   row = {
                       'adv_id': adv.adv_id,
                       'adv_type': adv.type if adv.type else 0,
                       'keyword': keyword.text,
                       **avg_item_features,  # Убедитесь, что avg_item_features определен и актуален
                       **{f'keyword_feature_{i}': keyword_features[i] for i in range(len(keyword_features))},
                   }
                   data_rows.append(row)
       logger.debug('Формирование df')
       df = pd.DataFrame(data_rows)
       logger.debug('Df готов')
       return df







