import asyncio
import logging
import os.path
import typing
from ast import literal_eval
from datetime import datetime
import joblib
import xgboost
from ..common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from ..common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from ... import settings
from app.modules.wb_adv_updater.ABC_manager import AbcManager
from app.utils.db.session_maker import get_async_session_maker
import numpy as np
import pandas as pd
from sklearn.model_selection import  cross_validate, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import selectinload
from xgboost import XGBRegressor
from sqlalchemy import select, and_, or_
from app.modules.common_slaves.wildberries.models import AdvSetting,  KeywordSetting, WBCabinet
from . import data_manager
from .data_manager import DataGetter
from ...exc import CardNotFoundInDB
from ...utils import redis_manager
from multiprocessing import Lock
import logging


logger = logging.getLogger(__name__)


data_getter = DataGetter()


path = 'model'

model_lock = Lock()

def save_model(model: xgboost.XGBModel, time_stamp = None):
    with model_lock:
        model_path = os.path.join(path, 'model.json')
        joblib.dump(model, model_path)

        if time_stamp:
            with open(f'{path}/time_stamp.txt', 'w') as file:
                file.write(time_stamp)


def load_model():
    logger.debug('Загрузка модели')
    with model_lock:
        logger.debug('Прошли lock')
        model = joblib.load(os.path.join(path, 'model.json'))
        logger.debug('Модель загружена')
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