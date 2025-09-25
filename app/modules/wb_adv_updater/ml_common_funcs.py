import logging
import os.path
from multiprocessing import Lock

import joblib
import numpy as np
import xgboost

from .data_getter import DataGetter

logger = logging.getLogger(__name__)


data_getter = DataGetter()


path = "model"

model_lock = Lock()
model_cache: xgboost.XGBModel | None = None  # Добавил кеш для модели


def save_model(model: xgboost.XGBModel, time_stamp: str | None = None) -> None:
    with model_lock:
        model_path = os.path.join(path, "model.json")
        joblib.dump(model, model_path)

        if time_stamp:
            with open(f"{path}/time_stamp.txt", "w") as file:
                file.write(time_stamp)


def load_model() -> xgboost.XGBModel:
    global model_cache
    if model_cache is not None:
        logger.debug("Модель загружена из кеша")
        return model_cache

    logger.debug("Загрузка модели")
    with model_lock:
        logger.debug("Прошли lock")
        model_cache = joblib.load(os.path.join(path, "model.json"))
        logger.debug("Модель загружена")
        return model_cache


async def get_keyword_features(keywords: list[str]) -> dict[str, np.ndarray]:
    result = await data_getter.get_keyword_features_from_redis(keywords)
    keyword_to_features = {}
    for row in result:
        keyword = row[0]
        vector = row[1]
        vector = np.array(vector)
        keyword_to_features[keyword] = vector
    return keyword_to_features
