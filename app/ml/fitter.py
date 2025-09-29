import os
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import selectinload  # оставлен, но уберём использование, чтобы не требовать отношения
from xgboost import XGBRegressor

from shared_lib.models.advsetting import AdvSetting
from shared_lib.utils.sql_session_maker import get_async_session_maker
from shared_lib.utils import data_manager
from shared_lib.utils.data_getter import DataGetter

logger = logging.getLogger(__name__)
logger.debug("fitter module imported (simplified real-only mode)")


@dataclass
class DummyModel:
    value: float = 0.05

    def predict(self, X):  # pragma: no cover
        try:
            n = len(X)
        except Exception:
            n = 1
        return [self.value] * n


sm = get_async_session_maker
_data_getter = DataGetter()

############################################################
# Legacy logic restored (adapted — без wb_cabinet prefetch)
############################################################


async def fit_and_get_new_model() -> Any | None:
    """Возвращает обученную модель XGBRegressor по логике, максимально близкой к legacy."""
    logger.info("[legacy-fit] Старт обучения модели")
    try:
        base_df: pd.DataFrame = await _get_df_for_fit()
    except Exception as exc:
        logger.error("[legacy-fit] Ошибка получения данных: %s", exc, exc_info=True)
        return None

    if base_df.empty:
        logger.warning("[legacy-fit] Нет данных для обучения (base_df.empty)")
        return None

    df: pd.DataFrame = await _bayesian_apply(base_df)

    try:
        await asyncio.to_thread(df.to_csv, "work_folder/df_for_fit.csv", index=False)
    except Exception:
        logger.warning("[legacy-fit] Не удалось сохранить df_for_fit.csv", exc_info=True)

    try:
        y = df["ctr"]
        X = df.drop(
            [
                "keyword",
                "views",
                "ctr",
                "clicks",
                "adv_id",
                "spend",
                "nmids",
                "adv_type",
            ],
            axis=1,
            errors="ignore",
        )
        logger.info(
            "[legacy-fit] Подготовка данных завершена: X.shape=%s item_features=%s keyword_features=%s",
            X.shape,
            len([c for c in X.columns if c.startswith("item_feature_")]),
            len([c for c in X.columns if c.startswith("keyword_feature_")]),
        )
        model = XGBRegressor(n_jobs=-1)
        await asyncio.to_thread(model.fit, X, y)
        setattr(model, "_training_source", "legacy")
        logger.info("[legacy-fit] Модель обучена")
        return model
    except Exception as exc:
        logger.error("[legacy-fit] Ошибка при обучении модели: %s", exc, exc_info=True)
        return None


async def _get_df_for_fit() -> pd.DataFrame:
    data_rows = []
    start_time = time.time()
    logger.info("[legacy-fit] Получение исходных данных")

    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.bot_active == True)  # noqa: E712
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()
        nmids_in_active_adv = {nmid for adv in adv_settings for nmid in (adv.nmids or [])}

        # Вторая выборка (как в legacy, но без selectinload wb_cabinet, т.к. модель урезана)
        stmt = select(AdvSetting).where(AdvSetting.bot_active == True)  # noqa: E712
        result = await session.execute(stmt)
        adv_settings_iter = result.scalars()

    for adv in adv_settings_iter:
        nmids = adv.nmids or []
        if len(nmids) != 1:  # в legacy пропускали кампании не с одним артикулом для обучения
            continue
        nmid_in_adv = nmids[0]
        if nmid_in_adv not in nmids_in_active_adv:
            continue
        try:
            nmid_to_item_features = await _get_nmid_to_item_features(set(nmids))
        except Exception:
            logger.warning("[legacy-fit] Ошибка получения item features", exc_info=True)
            continue
        if not nmid_to_item_features:
            continue
        item_features_list = list(nmid_to_item_features.values())
        try:
            avg_item_features = pd.DataFrame(item_features_list).mean().to_dict()
            avg_item_features = {
                f"item_feature_{i}": avg_item_features[i] for i in avg_item_features.keys()
            }
        except Exception:
            logger.warning("[legacy-fit] Ошибка усреднения item features", exc_info=True)
            continue

        # Получаем статистику ключевых слов (ClickHouse) через data_manager legacy-функцию
        try:
            keyword_stats: list[Any] = await data_manager.get_keywords_statistic_clickhouse(
                adv, last_views=500
            )
        except Exception:
            logger.warning("[legacy-fit] Ошибка получения keyword stats", exc_info=True)
            continue

        if not keyword_stats:
            continue

        # Кластеризация (legacy сбор)
        try:
            keywords_stats_by_clusters = await data_manager.convert_keyword_stats_in_clusters(
                keyword_stats
            )
        except Exception:
            logger.warning("[legacy-fit] Ошибка конвертации статистики в кластеры", exc_info=True)
            keywords_stats_by_clusters = []

        in_clusters = {kw.text for kw in keyword_stats}
        clear_keyword_stat = [kw for kw in keyword_stats if kw.text not in in_clusters]
        keyword_stats_combined = keywords_stats_by_clusters + clear_keyword_stat

        processed = 0
        for kw_stat in keyword_stats_combined:
            try:
                kw_vectors = await _data_getter.get_keyword_features_from_redis([kw_stat.text])
            except Exception:
                logger.debug("[legacy-fit] Ошибка получения keyword vector", exc_info=True)
                continue
            if not kw_vectors:
                continue
            keyword_feature = kw_vectors[0][1]
            row = {
                "adv_id": adv.adv_id,
                "adv_type": getattr(adv, "type", None),
                "keyword": kw_stat.text,
                "views": kw_stat.views,
                "clicks": kw_stat.clicks,
                "spend": kw_stat.spend,
                "nmids": adv.nmids,
                **avg_item_features,
                **{f"keyword_feature_{i}": keyword_feature[i] for i in range(len(keyword_feature))},
            }
            data_rows.append(row)
            processed += 1
            if processed % 200 == 0:
                logger.debug("[legacy-fit] processed %s keywords for adv %s", processed, adv.adv_id)

    df = pd.DataFrame(data_rows)
    logger.info(
        "[legacy-fit] Сбор данных завершён: %s строк за %.2f сек", len(df), time.time() - start_time
    )
    return df


async def _bayesian_apply(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy расчёт CTR c байесовским сглаживанием через data_manager."""
    if df.empty:
        return df
    adv_ids = df["adv_id"].unique().tolist()
    try:
        adv_id_keyword_text_to_status: dict[tuple[int, str], int] = (
            await data_manager.get_adv_id_keyword_text_to_status(adv_ids)
        )
    except Exception:
        logger.warning("[legacy-fit] Ошибка получения статусов ключевых слов", exc_info=True)
        adv_id_keyword_text_to_status = {}
    try:
        adv_id_to_min_ctr: dict[int, float] = await data_manager.get_adv_id_to_min_ctr(
            adv_ids
        )
    except Exception:
        logger.warning("[legacy-fit] Ошибка получения min ctr", exc_info=True)
        adv_id_to_min_ctr = {aid: 0.0 for aid in adv_ids}

    def calculate_ctr(row):
        clicks = row["clicks"]
        views = row["views"]
        adv_id = row["adv_id"]
        try:
            status = adv_id_keyword_text_to_status[(adv_id, row["keyword"])]
        except KeyError:
            status = 1
        if status == 0:
            return 0
        if views == 0:
            return 0
        if clicks == 0:
            min_ctr = adv_id_to_min_ctr.get(adv_id, 0)
            if min_ctr > 0:
                enough_views = _get_enough_views(min_ctr)
                # Bayesian update: добавляем 1 к кликам и enough_views к показам
                return (clicks + 1) / (views + enough_views)
            return 0
        return clicks / views

    df["ctr"] = df.apply(calculate_ctr, axis=1)
    return df


def _get_enough_views(ctr: float) -> int:
    if ctr <= 0:
        return 1
    return int(1 / ctr) if ctr > 0 else 1


async def _get_nmid_to_item_features(nmids_batch: set[int]) -> dict[int, np.ndarray]:
    result = await _data_getter.get_item_features_from_redis(nmids_batch)
    items = []
    for row in result:
        nmid = row[0]
        vector = row[1]
        items.append((nmid, vector))
    return dict(items)
