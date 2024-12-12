import asyncio
import logging
import os.path
import time
from collections import defaultdict

from .ml_common_funcs import save_model
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
from sqlalchemy import select, and_, or_, func
from app.modules.common_slaves.wildberries.models import AdvSetting,  KeywordSetting, WBCabinet
from . import data_manager
from .data_manager import DataGetter
from ...exc import CardNotFoundInDB
from ...utils import redis_manager
from multiprocessing import Lock

sm = get_async_session_maker


logger = logging.getLogger(__name__)

data_getter = DataGetter()

async def getGradientBoostingFullFitModel():
    await _fit_modelGradientBoosting()
    logger.debug('Модель обучена')




async def _fit_modelGradientBoosting():
    logger.debug('Поток обучения запущен, получение данных')
    try:
         df = await _get_df_for_fit()
    except Exception as exc:
        logger.error(f'Ошибка при получении данных для обучения: {exc}', exc_info=True)
        raise exc
    logger.debug('Данные получены')
    if len(df) == 0:
        logger.info('Нет данных для обучения')
        return
    df:pd.DataFrame = await _bayesian_apply(df)
    await asyncio.to_thread(df.to_csv, 'work_folder/df_for_fit.csv', index=False)
    y = df['ctr']
    X = df.drop(['keyword', 'views', 'ctr', 'clicks', 'adv_id', 'spend', 'nmids'],
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


async def _get_df_for_fit() -> pd.DataFrame:
    data_rows = []
    start_time = time.time()
    logger.info('Начало получения данных для обучения')

    async with sm() as session:
        try:
            logger.debug('Формирование подзапроса для WBCabinet')
            subquery = select(WBCabinet.id).where(
                or_(
                    WBCabinet.expiration_time > datetime.now(),
                    WBCabinet.bonus > 0,
                    WBCabinet.balance > 0,
                )
            ).exists()

            # Подсчет общего количества записей
            logger.debug('Подсчет общего количества кампаний')
            count_stmt = select(func.count()).select_from(AdvSetting).where(subquery, AdvSetting.type == 8)
            total_count = await session.scalar(count_stmt)
            logger.info(f'Всего найдено кампаний: {total_count}')

            # Основной запрос
            logger.debug('Выполнение основного запроса для получения AdvSetting')
            stmt = select(AdvSetting).options(
                selectinload(AdvSetting.wb_cabinet)
            ).where(subquery, AdvSetting.type == 8)
            result = await session.execute(stmt)
            adv_settings = result.scalars().yield_per(100)

            for n, adv in enumerate(adv_settings):
                logger.info(f'Обработка кампании {n + 1} из {total_count} (ID: {adv.adv_id})')
                nmids = adv.nmids

                if len(nmids) >= 1:
                    logger.debug(f'Получение features для {len(nmids)} nmids кампании {adv.adv_id}')
                    nmid_to_item_features = await get_nmid_to_item_features(nmids)

                    if nmid_to_item_features:
                        logger.debug(f'Расчет средних features для кампании {adv.adv_id}')
                        item_features_list = list(nmid_to_item_features.values())
                        avg_item_features = pd.DataFrame(item_features_list).mean().to_dict()
                        avg_item_features = {f'item_feature_{i}': avg_item_features[i] for i in
                                             avg_item_features.keys()}

                        logger.debug(f'Получение статистики ключевых слов из ClickHouse для кампании {adv.adv_id}')
                        keyword_stats: list[CalculatedKeyword] \
                            = await data_manager.get_keywords_statistic_clickhouse(adv,
                                                                                   last_views=500)
                        logger.debug(f'Получено {len(keyword_stats)} ключевых слов для кампании {adv.adv_id}')

                        logger.debug('Конвертация статистики ключевых слов в кластеры')
                        keywords_stats_by_clusters = await data_manager.convert_keyword_stats_in_clusters(keyword_stats)
                        logger.debug(f'Получено {len(keywords_stats_by_clusters)} кластеров')

                        in_clusters = {kw.text for kw in keyword_stats}

                        clear_keyword_stat = []
                        for keyword_stat in keyword_stats:
                            if keyword_stat.text not in in_clusters:
                                clear_keyword_stat.append(keyword_stat)

                        logger.debug(f'Найдено {len(clear_keyword_stat)} ключевых слов вне кластеров')

                        keyword_stats = keywords_stats_by_clusters + clear_keyword_stat

                        logger.debug(f'Получение features для {len(keyword_stats)} ключевых слов из Redis')
                        processed_keywords = 0
                        for keyword_stat in keyword_stats:
                            keyword_features = await data_getter.get_keyword_features_from_redis([keyword_stat.text])
                            if keyword_features:
                                keyword_feature = keyword_features[0][1]
                                row = {
                                    'adv_id': adv.adv_id,
                                    'adv_type': adv.type,
                                    'keyword': keyword_stat.text,
                                    'views': keyword_stat.views,
                                    'clicks': keyword_stat.clicks,
                                    'spend': keyword_stat.spend,
                                    'nmids': adv.nmids,
                                    **avg_item_features,
                                    **{f'keyword_feature_{i}': keyword_feature[i] for i in range(len(keyword_feature))}
                                }
                                data_rows.append(row)
                                processed_keywords += 1

                                if processed_keywords % 100 == 0:
                                    logger.debug(
                                        f'Обработано {processed_keywords} ключевых слов из {len(keyword_stats)}')

                            await asyncio.sleep(0)

        except Exception as e:
            logger.error(f'Ошибка при получении данных: {str(e)}', exc_info=True)
            raise

    # Преобразуем данные в DataFrame
    df = pd.DataFrame(data_rows)
    execution_time = time.time() - start_time
    logger.info(f'Завершено получение данных. Собрано {len(data_rows)} строк за {execution_time:.2f} секунд')
    return df


async def __fetch_keyword_features(keywords: list[str])->list[tuple[str, list[float]]]:
    result: list[tuple[str, list[float]]] = await data_getter.get_keyword_features_from_redis(keywords)
    return result


async def _bayesian_apply(df: pd.DataFrame):
    adv_ids = df['adv_id'].unique()

    adv_id_keyword_text_to_status: dict[(int, 'str'), int] = await data_manager.get_adv_id_keyword_text_to_status(adv_ids)

    adv_id_to_min_ctr: dict[int, float] = await data_manager.get_adv_id_to_min_ctr(adv_ids)
    def calculate_ctr(row):
        clicks = row['clicks']
        views = row['views']
        adv_id = row['adv_id']
        try:
            status = adv_id_keyword_text_to_status[(adv_id, row['keyword'])]
        except KeyError:
            status = 1
        if status == 0:
            return 0
        elif status in [2, 3]:
            return 1
        else:
            if clicks == 0:
                min_ctr = adv_id_to_min_ctr[adv_id]
                if min_ctr > 0:
                     enough_views = _get_enough_views(min_ctr)
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


def _get_enough_views(ctr):
     return int(1/ctr)


async def get_nmid_to_item_features(nmids_batch: set[int]) -> dict[int, np.ndarray]:
    result = await data_getter.get_item_features_from_redis(nmids_batch)
    result_list = []
    for row in result:
        nmid = row[0]
        vector = row[1]
        result_list.append((nmid, vector))
    return dict(result_list)

