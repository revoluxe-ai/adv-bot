import asyncio
import logging
import os
from datetime import date, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from xgboost import XGBRegressor  # type: ignore

from shared_lib.models.advsetting import AdvSetting
from shared_lib.utils.sql_session_maker import get_async_session_maker
from shared_lib.utils.data_getter import DataGetter
from shared_lib.settings_master import settings as shared_settings

logger = logging.getLogger(__name__)

CLICKHOUSE_QUERY_TEMPLATE = """
SELECT
    text,
    sum(clicks)  AS clicks,
    sum(views)   AS views,
    sum(spend)   AS spend
FROM default_db.advkeyword
WHERE adv_id = %(adv_id)s
  AND date >= %(date_from)s
GROUP BY text
HAVING views > 0
LIMIT %(limit)s
"""

try:
    import clickhouse_connect  # type: ignore
except Exception:  # pragma: no cover
    clickhouse_connect = None  # type: ignore


def _get_env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}


def _get_env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


async def _load_active_adv_settings(session: AsyncSession) -> list[AdvSetting]:
    stmt = select(AdvSetting).where(AdvSetting.bot_active == True)  # noqa: E712
    result = await session.execute(stmt)
    advs = list(result.scalars().all())
    return advs


async def _fetch_clickhouse_keyword_stats(adv_id: int, days: int, limit: int) -> pd.DataFrame:
    if clickhouse_connect is None:
        raise RuntimeError("clickhouse-connect не установлен")
    host = shared_settings.clickhouse_host
    user = shared_settings.clickhouse_user
    password = shared_settings.clickhouse_password
    port = shared_settings.CLICKHOUSE_PORT
    client = await clickhouse_connect.get_async_client(  # type: ignore[attr-defined]
        host=host, username=user, password=password, port=port, database="default_db"
    )
    date_from = (date.today() - timedelta(days=days)).isoformat()
    query = CLICKHOUSE_QUERY_TEMPLATE
    params = {"adv_id": adv_id, "date_from": date_from, "limit": limit}
    result = await client.query(query, params)
    rows = result.result_rows  # type: ignore[attr-defined]
    df = pd.DataFrame(rows, columns=["keyword", "clicks", "views", "spend"])
    return df


async def build_training_dataframe(days: int = 7, limit_per_adv: int = 500) -> pd.DataFrame:
    """Собирает датафрейм для обучения на реальных данных.

    1. Берём активные AdvSetting
    2. Для каждого adv_id получаем статистику ключевых слов из ClickHouse
    3. Получаем item и keyword векторы из Redis
    4. Формируем признаки + целевую ctr = clicks / views (со сглаживанием)
    """
    dg = DataGetter()
    rows: list[dict[str, Any]] = []

    async with get_async_session_maker() as session:  # type: ignore
        advs = await _load_active_adv_settings(session)

    if not advs:
        logger.warning("Нет активных AdvSetting для обучения")
        return pd.DataFrame()

    for adv in advs:
        if not adv.adv_id:
            continue
        nmids = adv.nmids or []
        if not nmids:
            continue
        try:
            kw_df = await _fetch_clickhouse_keyword_stats(int(adv.adv_id), days, limit_per_adv)
        except Exception:
            logger.error("Не удалось получить статистику из ClickHouse для adv_id=%s", adv.adv_id, exc_info=True)
            continue
        if kw_df.empty:
            continue

        # item features (усреднение по всем nmid кампании)
        try:
            item_features_list = await dg.get_item_features_from_redis(nmids)
        except Exception:
            logger.error("Ошибка получения item features из Redis", exc_info=True)
            continue
        if not item_features_list:
            continue
        vectors = [vec for _nmid, vec in item_features_list]
        # длина векторов может быть разной, пропускаем кривые
        try:
            import numpy as np
            arr = np.array(vectors, dtype=float)
            avg_item = arr.mean(axis=0)
        except Exception:
            logger.error("Ошибка усреднения item features", exc_info=True)
            continue
        item_feature_map = {f"item_feature_{i}": float(val) for i, val in enumerate(avg_item)}

        # keyword features batch (берём все keywords из статистики)
        keywords = kw_df["keyword"].tolist()
        try:
            kw_vectors = await dg.get_keyword_features_from_redis(keywords)
        except Exception:
            logger.error("Ошибка получения keyword features", exc_info=True)
            continue
        kw_vec_map = {k: v for k, v in kw_vectors}

        for rec in kw_df.itertuples():  # type: ignore
            clicks = int(rec.clicks)
            views = int(rec.views)
            if views == 0:
                continue
            # Сглаживание CTR: (clicks + alpha) / (views + beta)
            alpha = float(os.getenv("PREDICT_CTR_CTR_ALPHA", "1"))
            beta = float(os.getenv("PREDICT_CTR_CTR_BETA", "30"))
            ctr = (clicks + alpha) / (views + beta)
            kw_vec = kw_vec_map.get(rec.keyword)
            if not kw_vec:
                continue
            sample: dict[str, Any] = {
                "adv_id": adv.adv_id,
                "keyword": rec.keyword,
                "ctr": ctr,
                "views": views,
                "clicks": clicks,
                **item_feature_map,
            }
            for i, val in enumerate(kw_vec):
                sample[f"keyword_feature_{i}"] = val
            rows.append(sample)

    df = pd.DataFrame(rows)
    logger.info("Сформирован датафрейм для обучения: %s строк", len(df))
    return df


async def train_real_model() -> tuple[Any | None, dict[str, Any]]:
    """Обучает XGBRegressor на реальных данных. Возвращает (model, stats)."""
    days = _get_env_int("PREDICT_CTR_TRAIN_DAYS", 7)
    limit_per_adv = _get_env_int("PREDICT_CTR_TRAIN_LIMIT_PER_ADV", 500)
    min_rows = _get_env_int("PREDICT_CTR_MIN_ROWS", 200)
    df = await build_training_dataframe(days=days, limit_per_adv=limit_per_adv)
    if df.empty:
        logger.warning("Пустой датафрейм – пропуск обучения")
        return None, {"rows": 0, "reason": "empty"}
    if "ctr" not in df.columns:
        logger.error("Нет столбца ctr – обучение невозможно")
        return None, {"rows": len(df), "reason": "no_ctr_column"}
    if len(df) < min_rows:
        logger.warning("Мало строк (%s < %s) – пропуск обучения", len(df), min_rows)
        return None, {"rows": len(df), "reason": "too_few_rows", "min_rows": min_rows}

    y = df["ctr"]
    X = df.drop(["keyword", "ctr"], axis=1, errors="ignore")
    logger.info("Старт обучения реальной модели: X.shape=%s", X.shape)
    model = XGBRegressor(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        n_jobs=4,
        tree_method="hist",
    )
    await asyncio.to_thread(model.fit, X, y)
    logger.info("Обучение завершено. Модель готова.")
    stats = {
        "rows": int(len(df)),
        "features": int(X.shape[1]),
        "days": days,
        "limit_per_adv": limit_per_adv,
        "min_rows": min_rows,
        "mode": "real",
    }
    return model, stats
