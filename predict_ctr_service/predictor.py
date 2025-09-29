import logging
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Tuple, Set
from numpy.typing import NDArray

# from xgboost import XGBModel  # Теперь используем pipeline

logger = logging.getLogger(__name__)

from .excs import (
    NotFoundItemFeaturesError,
    NotLoadModelError,
)
from .utils.data_getter import DataGetter
from .utils import text_cleaner


class Predictor:
    def __init__(self, model: Any) -> None:
        """model - это обученная XGBRegressor модель или совместимый объект"""
        self._model: Any = model
        self._data_getter = DataGetter()

    async def _get_nmid_to_item_features(
        self, nmids: Set[int]
    ) -> Dict[int, NDArray[float]]:
        result = await self._data_getter.get_item_features_from_redis(nmids)
        # Ожидаем dict[int, list[float]]
        if not isinstance(result, dict):
            return {}
        result_list: List[Tuple[int, NDArray[float]]] = []
        for nmid, vector in result.items():
            arr: NDArray[float] = np.array(vector, dtype=float)
            result_list.append((nmid, arr))
        return dict(result_list)

    async def _get_keyword_features(
        self, texts: List[str]
    ) -> List[Tuple[str, List[float]]]:
        result = await self._data_getter.get_keyword_features_from_redis(texts)
        if not isinstance(result, list):
            return []
        return result

    async def _get_df_for_predict(
        self, nmids: Set[int], texts: List[str]
    ) -> pd.DataFrame:
        # Получаем item features
        item_features = await self._get_nmid_to_item_features(nmids)

        if not item_features:
            raise NotFoundItemFeaturesError("Нет item_features")

        item_features_list = list(item_features.values())
        if not item_features_list:
            raise NotFoundItemFeaturesError("Пустой список item_features")

        features_array = np.array(item_features_list)
        avg_features = np.mean(features_array, axis=0)

        avg_item_features: Dict[str, float] = {
            f"item_feature_{i}": float(avg_features[i])
            for i in range(len(avg_features))
        }

        # Получаем и очищаем ключевые слова
        clear_keywords = [text_cleaner.clear(text) for text in texts]

        keyword_features_result = await self._get_keyword_features(clear_keywords)
        keyword_features_dict: Dict[str, List[float]] = {row[0]: row[1] for row in keyword_features_result}

        data_rows: List[Dict[str, Any]] = []
        for text in texts:
            text_cleaned = text.replace("_", " ")
            keyword_features = keyword_features_dict.get(text_cleaned, [])

            if not keyword_features:
                continue

            row: Dict[str, Any] = {
                "keyword": text,
                **avg_item_features,
                **{
                    f"keyword_feature_{i}": float(keyword_features[i])
                    for i in range(len(keyword_features))
                },
            }
            data_rows.append(row)

        df = pd.DataFrame(data_rows)
        return df

    async def predict(self, nmids: List[int], texts: List[str]) -> Dict[str, float]:
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
        result_dict: Dict[str, float] = dict(zip(df["keyword"], df["predicted_ctr"]))

        return result_dict

    async def predict_batch(
        self, nmids: List[int], texts: List[str], batch_size: int = 1000
    ) -> Dict[str, float]:
        """
        Оптимизированный метод для предсказания с батчевой обработкой больших объемов данных
        """
        if len(texts) <= batch_size:
            return await self.predict(nmids, texts)

        results: Dict[str, float] = {}
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_results = await self.predict(nmids, batch_texts)
            results.update(batch_results)

        return results

    def _compute_avg_features_numpy(self, item_features_list: List[List[float]]) -> Dict[str, float]:
        """
        Оптимизированное вычисление средних признаков с использованием numpy
        """
        if not item_features_list:
            return {}

        features_array = np.array(item_features_list)

        avg_features = np.mean(features_array, axis=0)

        return {
            f"item_feature_{i}": float(avg_features[i])
            for i in range(len(avg_features))
        }
