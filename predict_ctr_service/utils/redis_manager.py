from .clickhouse_client import get_clickhouse_client
from shared_lib.models.calculated_keyword import CalculatedKeyword
from typing import List, Dict, Tuple, Any
from datetime import timedelta

from . import text_cleaner
from .redis_client import redis_replica_client
from .key_encoder import encode_key

# set_predict_ctrs
async def set_predict_ctrs(adv_id: int, keywords: List[CalculatedKeyword]) -> List[CalculatedKeyword]:
    # Формируем список ключей для запроса к Redis
    keys = [
        f"predict_ctr:{adv_id}:{text_cleaner.clear(keyword.text)}"
        for keyword in keywords
    ]
    # Получаем данные из Redis за один запрос
    predict_ctr_bytes_list = await redis_replica_client.mget(keys)
    for i, keyword in enumerate(keywords):
        value = predict_ctr_bytes_list[i]
        if value is not None:
            try:
                keyword.predict_ctr = float(value)
            except (TypeError, ValueError):
                keyword.predict_ctr = None
        else:
            keyword.predict_ctr = None
    return keywords  # Заглушка, замените на реальную реализацию

# get_clusters_and_presets
async def get_clusters_and_presets(texts: List[str]) -> Dict[str, Tuple[str | None, int | None]]:
    keys = [f"cluster_and_preset:{encode_key(text)}" for text in texts]
    # values = await redis_replica_client.mget(keys)
    values = [None] * len(keys)  # Заглушка для примера
    clusters_and_presets: dict[str, tuple[str | None, int | None]] = {}
    for text, value in zip(texts, values, strict=False):
        if value is None:
            clusters_and_presets[text] = (None, None)
            continue
        value = value.decode("utf-8") if hasattr(value, 'decode') else value
        try:
            cluster, preset = value.split(":")
            clusters_and_presets[text] = (cluster, int(preset))
        except Exception:
            clusters_and_presets[text] = (None, None)
    return clusters_and_presets

# __calculate_clusters
def __calculate_clusters(preset_to_keywords: Dict[Any,
    List[CalculatedKeyword]],
    preset_to_cluster_name: Dict[Any, str]) -> List[CalculatedKeyword]:
    keyword_stats = []
    for preset in preset_to_keywords:
        keywords = preset_to_keywords[preset]
        keyword_cluster_name = preset_to_cluster_name[preset]
        views: int = 0
        clicks: int = 0
        spend: float = 0.0
        query: float = 0.0
        for keyword in keywords:
            views += keyword.views
            clicks += keyword.clicks
            spend += keyword.spend
            if isinstance(keyword.query, (int, float)):
                query += float(keyword.query)
        cluster_keyword = CalculatedKeyword(
            text=keyword_cluster_name, views=views, clicks=clicks, spend=spend
        )
        cluster_keyword.query = query if query else "<50"
        cluster_keyword.childs_keywords = keywords
        keyword_stats.append(cluster_keyword)
    return keyword_stats

# _build_clickhouse_query

def _build_clickhouse_query(
    adv_ids: set[int],
    pass_time: timedelta | None,
    last_views: int | None = None,
) -> str:
    adv_ids_str = ", ".join(str(aid) for aid in adv_ids)
    # Здесь должен быть ваш SQL-запрос
    query = f"SELECT ... FROM ... WHERE adv_id IN ({adv_ids_str})"  # Заглушка
    return query

__all__ = [
    "get_clickhouse_client",
    "set_predict_ctrs",
    "get_clusters_and_presets",
    "__calculate_clusters",
    "_build_clickhouse_query",
    "get_nmid_vectors",
    "get_keywords_vectors"
]

async def get_nmid_vectors(nmids_batch: set[int]) -> dict[int, list[float]]:
    # Заглушка для примера
    return {nmid: [0.0, 1.0] for nmid in nmids_batch}

async def get_keywords_vectors(keywords: list[str]) -> list[tuple[str, list[float]]]:
    # Заглушка для примера
    return [(kw, [0.0, 1.0]) for kw in keywords]
