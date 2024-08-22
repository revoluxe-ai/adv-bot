import asyncio
import logging
import os.path
import typing

from .data_manager import DataGetter
from .ml_common_funcs import load_model
from ast import literal_eval
import xgboost
from app.modules.wb_adv_updater.ABC_manager import AbcManager
from app.utils.db.session_maker import get_async_session_maker
import numpy as np
import pandas as pd
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.modules.common_slaves.wildberries.models import AdvSetting,  KeywordSetting, WBCabinet
from . import data_manager, fitter
from ...utils import redis_manager


sm = get_async_session_maker


logger = logging.getLogger(__name__)




global_model: typing.Union[xgboost.XGBModel, None] = None



update_predict_ctr_process_semaphore = asyncio.Semaphore(10)

data_getter = DataGetter()

class Fitter(AbcManager):

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
















class Predictor:

    def _predict(self, df: pd.DataFrame)-> typing.Union[pd.DataFrame, None]:
        logger.debug('начинаю _predict')
        model = load_model()
        logger.debug('Модель загружена')
        try:
            X = df.drop(['keyword', 'adv_id'], axis=1)
        except Exception as exc:
            logger.error(f'Ошибка удаления столбцов, длина df: {len(df)}')
            raise exc
        logger.debug('Удаление столбцов прошло')
        y = model.predict(X)
        logger.debug('Предсказание завершено')
        df['predicted_ctr'] = y
        return df



    @staticmethod
    async def __update_predict_ctr(keyword_setting, predict_df, min_ctr):
        async with update_predict_ctr_process_semaphore:
            try:
                adv_id = keyword_setting.adv_setting.adv_id
                keyword = keyword_setting.text
                if not keyword:
                    return
                row = predict_df[(predict_df['adv_id'] == adv_id) & (predict_df['keyword'] == keyword)]
                if row.empty:
                    return
                predict_ctr = float(row['predicted_ctr'].values[0])
                result = await data_manager.get_keyword_statistic_clickhouse(keyword_setting, adv_id)
                clicks, views, _ = result
                if clicks == 0:
                    clicks = 1
                    enough_views = int(1 / min_ctr)
                    views += enough_views
                real_ctr = clicks / views
                predict_ctr = (real_ctr + predict_ctr) / 2
                # Создаем задачи для асинхронного обновления Redis
                await redis_manager.set_predict_ctr(adv_id, keyword, predict_ctr)
            except Exception as exc:
                logger.error(f'Ошибка при обновлении предсказания для ключевого слова {keyword_setting.text}: {exc}')




    async def predict_ctr_for_keywords(self):
        async with sm() as session:
            stmt = select(AdvSetting).options(
                selectinload(AdvSetting.adv_keywords),
                selectinload(AdvSetting.keyword_settings)
            ).where(AdvSetting.bot_active == True,
                    AdvSetting.active_status == 'started')
            result = await session.execute(stmt)
            all_adv_settings = result.scalars().unique().all()
        try:
            df_for_predict = await self._get_df_for_predict(all_adv_settings)
        except Exception as exc:
            logger.error(f'Ошибка при получении данных для предсказания: {exc}', exc_info=True)
            raise exc
        try:
            predict_df: pd.DataFrame = await asyncio.to_thread(self._predict, df_for_predict)
        except Exception as exc:
            logger.error(f'Ошибка при предсказании: {exc}', exc_info=True)
            raise exc

        predict_df['predicted_ctr'] = predict_df['predicted_ctr'].apply(lambda ctr: ctr if ctr >=0 else 0)
        await asyncio.to_thread(predict_df.to_csv, 'work_folder/предсказания.csv')
        # predict_df = pd.read_csv('work_folder/предсказания.csv')
        async with sm() as session:
            stmt = select(KeywordSetting)\
                .join(KeywordSetting.adv_setting)\
                .options(selectinload(KeywordSetting.adv_setting))\
                .where(AdvSetting.bot_active == True,
                       AdvSetting.active_status == 'started')
            result = await session.execute(stmt)
            keyword_settings = result.scalars().all()

        adv_id_to_min_ctr = {}

        tasks = []
        for keyword_setting in keyword_settings:
            adv = keyword_setting.adv_setting
            adv_id = adv.adv_id
            if not adv_id in adv_id_to_min_ctr:
                adv_id_to_min_ctr[adv_id] = await data_manager.get_min_ctr(adv)
            min_ctr = adv_id_to_min_ctr[adv_id]
            # try:
            #     await update_predict_ctr(keyword_setting)
            #     logger.debug(f'Предсказание для ключевого слова {keyword_setting.text} в кампании {keyword_setting.adv_setting.name} обновлено')
            # except Exception as exc:
            #     logger.error(f'Ошибка при обновлении предсказания для ключевого слова {keyword_setting.text}: {exc}')
            #     pass
            task = asyncio.create_task(self.__update_predict_ctr(keyword_setting, predict_df, min_ctr))
            tasks.append(task)
            await asyncio.sleep(0)

        part = 100
        for i in range(0, len(tasks), part):
            excs = await asyncio.gather(*tasks[i:i + part], return_exceptions=True)
            await asyncio.sleep(0)
            for ecv in excs:
                if ecv:
                    logger.error(ecv)


        logger.debug('Предсказания обновлены')



    # async def __write_predict_ctr_to_redis(self, adv, keyword, predict_ctr):
    #     logger.debug(f'Обновление предсказания для ключевого слова {keyword} в кампании {adv.name}')
    #     min_ctr = await data_manager.get_min_ctr(adv)
    #     enough_views = int(1 / min_ctr)
    #     async with sm() as session:
    #         stmt = select(KeywordSetting).where(and_(KeywordSetting.adv_setting_id == adv.id,
    #                                                  KeywordSetting.text == keyword))
    #         keyword_setting = await session.execute(stmt)
    #         keyword_setting = keyword_setting.scalar()
    #     clicks, views, _ = await data_manager.get_keyword_statistic(keyword_setting)
    #     if clicks == 0:
    #         clicks = 1
    #         views += enough_views
    #     real_ctr = clicks / views
    #     predict_ctr = (real_ctr + predict_ctr) / 2
    #     adv_id = adv.adv_id
    #     await redis_manager.set_predict_ctr(adv_id, keyword, predict_ctr)
    #     logger.debug(f'Предсказание для ключевого слова {keyword} в кампании {adv.name} обновлено')



    async def _get_df_for_predict(self, adv_settings: list[AdvSetting])-> pd.DataFrame:
       data_rows = []
       for adv in adv_settings:
           logger.debug(f'Обработка кампании {adv.name}')
           if not adv.nmids:
               logger.debug('Нет nmids: %s', adv.name)
               continue
           nmids = adv.nmids
           item_features = await self.get_nmid_to_item_features(nmids)

           item_features = [row[1] for row in item_features.items()]
           avg_item_features = pd.DataFrame(item_features).mean().to_dict()
           avg_item_features = {f'item_feature_{i}': avg_item_features[i] for i in avg_item_features.keys()}

           if not avg_item_features:
                 logger.debug('Нет item_features: %s', adv.name)
                 continue
           clear_keywords = [keyword.text.replace('_', ' ') for keyword in adv.keyword_settings]
           # Выполняем один запрос, чтобы получить все KeywordFeature объекты для этих ключевых слов
           keyword_features_result = await self.get_keyword_features(clear_keywords)
           keyword_features_result = {row[0]: row[1] for row in keyword_features_result}
           for keyword in adv.keyword_settings:
               text = keyword.text.replace('_', ' ')
               keyword_features = keyword_features_result.get(text, [])
               keyword_features = list(keyword_features)
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

    async def get_nmid_to_item_features(self, nmids):
        result = await fitter.get_nmid_to_item_features(nmids)
        return result

    async def get_keyword_features(self, clear_keywords):
        result = await data_getter.get_keyword_features_from_redis(clear_keywords)
        return result







