import logging
import numpy as np
import pandas as pd

# from xgboost import XGBModel  # Теперь используем pipeline

logger = logging.getLogger(__name__)

from app.modules.grpcs.predict_ctr_service.excs import (
    NotFoundItemFeaturesError,
    NotLoadModelError,
)
from app.modules.wb_adv_updater.data_getter import DataGetter
from app.utils import text_cleaner


class Predictor:
    def __init__(self, model):
        """model - это обученная XGBRegressor модель"""
        self._model = model
        self._data_getter = DataGetter()

    async def _get_nmid_to_item_features(
        self, nmids: set[int]
    ) -> dict[int, np.ndarray]:
        result = await self._data_getter.get_item_features_from_redis(nmids)
        result_list = []
        for row in result:
            nmid = row[0]
            vector = row[1]
            result_list.append((nmid, vector))
        return dict(result_list)

    async def _get_keyword_features(
        self, texts: list[str]
    ) -> list[tuple[str, list[float]]]:
        result = await self._data_getter.get_keyword_features_from_redis(texts)
        return result

    async def _get_df_for_predict(
        self, nmids: set[int], texts: list[str]
    ) -> pd.DataFrame:
        # Получаем item features
        item_features = await self._get_nmid_to_item_features(nmids)

        if not item_features:
            raise NotFoundItemFeaturesError("Нет item_features")

        # Оптимизированное вычисление среднего значения без создания DataFrame
        item_features_list = [row[1] for row in item_features.items()]
        if not item_features_list:
            raise NotFoundItemFeaturesError("Пустой список item_features")

        # Используем numpy для более эффективного вычисления среднего
        features_array = np.array(item_features_list)
        avg_features = np.mean(features_array, axis=0)

        # Создаем словарь с усредненными признаками
        avg_item_features = {
            f"item_feature_{i}": float(avg_features[i])
            for i in range(len(avg_features))
        }

        # Получаем и очищаем ключевые слова
        clear_keywords = [text_cleaner.clear(text) for text in texts]

        # Получаем keyword features одним запросом
        keyword_features_result = await self._get_keyword_features(clear_keywords)
        keyword_features_dict = {row[0]: row[1] for row in keyword_features_result}

        # Формируем данные для DataFrame
        data_rows = []
        for text in texts:
            text_cleaned = text.replace("_", " ")
            keyword_features = keyword_features_dict.get(text_cleaned, [])

            if not keyword_features:
                continue

            # Создаем строку данных
            row = {
                "keyword": text,
                **avg_item_features,
                **{
                    f"keyword_feature_{i}": keyword_features[i]
                    for i in range(len(keyword_features))
                },
            }
            data_rows.append(row)

        # Создаем DataFrame только один раз в конце
        df = pd.DataFrame(data_rows)
        return df

    async def predict(self, nmids: list[int], texts: list[str]) -> dict[str, float]:
        model = self._model
        if model is None:
            raise NotLoadModelError("Модель не загружена")
        df = await self._get_df_for_predict(set(nmids), texts)
        if df.empty:
            return {}
        try:
            X = df.drop(["keyword"], axis=1)
            logger.debug(f"Predictor X shape: {X.shape}")
            logger.debug(f"Predictor X columns: {list(X.columns)}")
            logger.debug(
                f"Predictor Item features count: {len([c for c in X.columns if c.startswith('item_feature_')])}"
            )
            logger.debug(
                f"Predictor Keyword features count: {len([c for c in X.columns if c.startswith('keyword_feature_')])}"
            )
        except Exception as exc:
            raise exc
        y = model.predict(X)

        df["predicted_ctr"] = y

        df = df[["keyword", "predicted_ctr"]]
        result_dict = dict(zip(df["keyword"], df["predicted_ctr"]))

        return result_dict

    async def predict_batch(
        self, nmids: list[int], texts: list[str], batch_size: int = 1000
    ) -> dict[str, float]:
        """
        Оптимизированный метод для предсказания с батчевой обработкой больших объемов данных
        """
        if len(texts) <= batch_size:
            return await self.predict(nmids, texts)

        # Разбиваем на батчи для обработки больших объемов данных
        results = {}
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_results = await self.predict(nmids, batch_texts)
            results.update(batch_results)

        return results

    def _compute_avg_features_numpy(self, item_features_list: list) -> dict:
        """
        Оптимизированное вычисление средних признаков с использованием numpy
        """
        if not item_features_list:
            return {}

        # Преобразуем в numpy array для векторных операций
        features_array = np.array(item_features_list)

        # Вычисляем среднее по всем признакам одновременно
        avg_features = np.mean(features_array, axis=0)

        # Создаем словарь с результатами
        return {
            f"item_feature_{i}": float(avg_features[i])
            for i in range(len(avg_features))
        }

    async def predict_batch(
        self, nmids: list[int], texts: list[str], batch_size: int = 1000
    ) -> dict[str, float]:
        """
        Оптимизированный метод для предсказания с батчевой обработкой больших объемов данных
        """
        if len(texts) <= batch_size:
            return await self.predict(nmids, texts)

        # Разбиваем на батчи для обработки больших объемов данных
        results = {}
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_results = await self.predict(nmids, batch_texts)
            results.update(batch_results)

        return results

    def _compute_avg_features_numpy(self, item_features_list: list) -> dict:
        """
        Оптимизированное вычисление средних признаков с использованием numpy
        """
        if not item_features_list:
            return {}

        # Преобразуем в numpy array для векторных операций
        features_array = np.array(item_features_list)

        # Вычисляем среднее по всем признакам одновременно
        avg_features = np.mean(features_array, axis=0)

        # Создаем словарь с результатами
        return {
            f"item_feature_{i}": float(avg_features[i])
            for i in range(len(avg_features))
        }
