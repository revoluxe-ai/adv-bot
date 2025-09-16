import os.path
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


def save_model(model: xgboost.XGBModel, time_stamp=None):
    with model_lock:
        model_path = os.path.join(path, "model.json")
        joblib.dump(model, model_path)

        if time_stamp:
            with open(f"{path}/time_stamp.txt", "w") as file:
                file.write(time_stamp)


def load_model():
    logger.debug("Загрузка модели")
    with model_lock:
        logger.debug("Прошли lock")
        model = joblib.load(os.path.join(path, "model.json"))
        logger.debug("Модель загружена")
        # with open(f'{path}/time_stamp.txt', 'r') as file:
        #     time_stamp = file.read()
        return model


async def get_keyword_features(keywords):
    result = await data_getter.get_keyword_features_from_redis(keywords)
    keyword_to_features = {}
    for row in result:
        keyword = row[0]
        vector = row[1]
        vector = np.array(vector)
        keyword_to_features[keyword] = vector
    return keyword_to_features
