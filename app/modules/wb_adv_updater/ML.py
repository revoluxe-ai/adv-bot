import asyncio
import logging
import typing
from ast import literal_eval

import numpy as np
import pandas as pd
import xgboost
from redis.asyncio.client import Pipeline
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.wb_adv_updater.ABC_manager import AbcManager
from app.utils.db.session_maker import get_async_session_maker

from ...core.redis_manager.base_redis_manager import BaseRedis
from ...utils import redis_manager, text_cleaner
from . import fitter
from .data_getter import DataGetter as MlDataGetter
from .ml_common_funcs import load_model

sm = get_async_session_maker


logger = logging.getLogger(__name__)


update_predict_ctr_process_semaphore = asyncio.Semaphore(10)

data_getter = MlDataGetter()


class Fitter(AbcManager):
    @staticmethod
    def __get_average_vector(nmids: str, df_vectors: pd.DataFrame) -> list[float] | None:
        nmids_list = literal_eval(nmids)
        vectors = (
            df_vectors[df_vectors["nmid"].isin(nmids_list)].iloc[:, 1:].values
        )  # Предполагаем, что векторы начинаются с 2-го столбца
        if vectors.size == 0:
            return None
        return list(np.mean(vectors, axis=0))  # Явно преобразуем к list[float]

    def fill_average_vector(self, df_stat: pd.DataFrame, df_vectors: pd.DataFrame) -> pd.DataFrame:
        # Вычисляем средние векторы, исключая None
        averaged_vectors = (
            df_stat["nmids"]
            .apply(lambda nmids_str: self.__get_average_vector(nmids_str, df_vectors))
            .dropna()
        )

        # Находим первый не None вектор для определения длины вектора
        first_valid_vector = next((vec for vec in averaged_vectors if vec is not None), None)
        vector_length = len(first_valid_vector) if first_valid_vector is not None else 0

        # Обрабатываем случаи с None, заменяя их на список None соответствующей длины
        averaged_vectors = averaged_vectors.apply(lambda x: x if x is not None else [None] * vector_length)

        # Создаем DataFrame для новых столбцов, учитывая возможные None значения
        new_columns_data = {}
        for i in range(vector_length):
            new_columns_data[f"item_f_{i}"] = averaged_vectors.apply(lambda x: x[i] if x is not None else None)

        new_columns_df = pd.DataFrame(new_columns_data)

        # Объединяем новые столбцы с df_stat и удаляем строки с None в новых столбцах
        df_items_keywords_stat = pd.concat(
            [df_stat.reset_index(drop=True), new_columns_df.reset_index(drop=True)],
            axis=1,
        ).dropna(subset=[f"item_f_{i}" for i in range(vector_length)])

        return df_items_keywords_stat


class Predictor:
    def _predict(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.debug("начинаю _predict")
        model: xgboost.XGBModel = load_model()
        logger.debug("Модель загружена")
        try:
            X = df.drop(["keyword", "adv_id"], axis=1)
        except Exception as exc:
            logger.error(f"Ошибка удаления столбцов, длина df: {len(df)}")
            raise exc
        logger.debug("Удаление столбцов прошло")
        y = model.predict(X)
        logger.debug("Предсказание завершено")
        df["predicted_ctr"] = y
        return df

    async def predict_ctr_for_keywords(self) -> None:
        logger.debug("Начинаю получать кампании для формирования DF для предсказаний")
        async with sm() as session:
            stmt = (
                select(AdvSetting)
                .options(
                    selectinload(AdvSetting.adv_keywords),
                    selectinload(AdvSetting.keyword_settings),
                )
                .where(AdvSetting.bot_active.is_(True))
            )
            result = await session.execute(stmt)
            all_adv_settings_list: list[AdvSetting] = list(result.scalars().unique().all())
        try:
            logger.debug("Начинаю получать DF  для предсказаний")
            df_for_predict: pd.DataFrame = await self._get_df_for_predict(all_adv_settings_list)
            logger.debug("Получили DF для предсказаний")
        except Exception as exc:
            logger.error(f"Ошибка при получении данных для предсказания: {exc}", exc_info=True)
            raise exc
        try:
            logger.debug("Начинаю предсказание")
            predict_df: pd.DataFrame = await asyncio.to_thread(self._predict, df_for_predict)  # Убеждаемся, что _predict всегда возвращает DataFrame
            logger.debug("Предсказания получены")
        except Exception as exc:
            logger.error(f"Ошибка при предсказании: {exc}", exc_info=True)
            raise exc

        predict_df["predicted_ctr"] = predict_df["predicted_ctr"].apply(lambda ctr: ctr if ctr >= 0 else 0)
        await asyncio.to_thread(predict_df.to_csv, "work_folder/предсказания.csv")
        # predict_df = pd.read_csv('work_folder/предсказания.csv')
        async with sm() as session:
            keyword_stmt = select(KeywordSetting).options(selectinload(KeywordSetting.adv_setting)).where(
                KeywordSetting.adv_setting.has(AdvSetting.bot_active.is_(True))
            )
            result = await session.execute(keyword_stmt)
            keyword_settings: list[KeywordSetting] = list(result.scalars().unique().all()) # Явно приводим к list[KeywordSetting]

        redis_manager = BaseRedis()
        async with redis_manager.client.pipeline() as redis_pipeline:
            for keyword_setting in keyword_settings:
                await self.__update_predict_ctr(
                    redis_pipeline,
                    keyword_setting,
                    predict_df,
                )

            await redis_pipeline.execute()

    async def _get_df_for_predict(self, adv_settings: list[AdvSetting]) -> pd.DataFrame:
        data_rows = []
        for adv in adv_settings:
            try:
                logger.debug(f"Обработка кампании {adv.name}")
                if not adv.nmids:
                    logger.debug("Нет nmids: %s", adv.name)
                    continue
                nmids_set: set[int] = set(adv.nmids)  # Преобразуем список в set[int]
                item_features: dict[int, list[float]] = await self.get_nmid_to_item_features(nmids_set)

                item_features_list = [row[1] for row in item_features.items()]
                avg_item_features = pd.DataFrame(item_features_list).mean().to_dict()
                avg_item_features = {f"item_feature_{i}": avg_item_features[i] for i in avg_item_features}

                if not avg_item_features:
                    logger.debug("Нет item_features: %s", adv.name)
                    continue
                clear_keywords: list[str] = [
                    text_cleaner.clear(keyword.text) for keyword in adv.keyword_settings if keyword.text is not None
                ]
                # Выполняем один запрос, чтобы получить все KeywordFeature объекты для этих ключевых слов
                keyword_features_result: dict[str, list[float]] = await self.get_keyword_features(clear_keywords)
                for keyword in adv.keyword_settings:
                    if keyword.text is None:
                        continue
                    text: str = keyword.text.replace("_", " ")
                    keyword_features: list[float] = keyword_features_result.get(text, [])
                    keyword_features = list(keyword_features)
                    if not keyword_features:
                        continue

                    # Собираем данные для строки
                    row: dict[str, typing.Any] = {
                        "adv_id": adv.adv_id,
                        "adv_type": adv.type if adv.type else 0,
                        "keyword": keyword.text,
                        **avg_item_features,  # Убедитесь, что avg_item_features определен и актуален
                        **{f"keyword_feature_{i}": keyword_features[i] for i in range(len(keyword_features))},
                    }
                    data_rows.append(row)
            except Exception:
                logger.error("Ошибка обработки РК", exc_info=True)
        logger.debug("Формирование df")
        df = pd.DataFrame(data_rows)
        logger.debug("Df готов")
        return df

    async def get_nmid_to_item_features(self, nmids: set[int]) -> dict[int, list[float]]:
        result = await fitter.get_nmid_to_item_features(nmids)
        return result

    async def get_keyword_features(self, clear_keywords: list[str]) -> dict[str, list[float]]:
        result = await data_getter.get_keyword_features_from_redis(clear_keywords)
        return result

    @staticmethod
    async def __update_predict_ctr(
        redis_pipeline: Pipeline,
        keyword_setting: KeywordSetting,
        predict_df: pd.DataFrame,
    ) -> None:
        adv_id = keyword_setting.adv_setting.adv_id
        keyword = keyword_setting.text
        if not keyword:
            return

        # Получаем строку с прогнозом для текущего ключевого слова
        row = predict_df[(predict_df["adv_id"] == adv_id) & (predict_df["keyword"] == keyword)]
        if row.empty:
            return

        # Извлекаем предсказанный CTR
        predicted_ctr = float(row["predicted_ctr"].values[0])
        await redis_manager.set_predict_ctr_with_pipeline(redis_pipeline, adv_id, keyword, predicted_ctr)
