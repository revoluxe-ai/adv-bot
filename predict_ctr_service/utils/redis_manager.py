from shared_lib.models.calculated_keyword import CalculatedKeyword
from .clickhouse_client import get_clickhouse_client
from typing import List, Dict, Tuple, Any
import json


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
        for keyword in keywords:
            views += keyword.views
            clicks += keyword.clicks
            spend += keyword.spend
        cluster_keyword = CalculatedKeyword(
            text=keyword_cluster_name, views=views, clicks=clicks, spend=spend
        )
        cluster_keyword.childs_keywords = keywords
        keyword_stats.append(cluster_keyword)
    return keyword_stats


async def get_nmid_vectors(nmids_batch: set[int]) -> dict[int, list[float]]:
    """
    Получить вектора для nmids из Redis.
    Ключ: item_vector:{nmid}, значение: JSON-сериализованный список float.
    """
    if not nmids_batch:
        return {}
    result = {}
    for nmid in nmids_batch:
        key = f"item_vector:{nmid}"
        vector_bytes = await redis_replica_client.get(key)
        if vector_bytes:
            vector_str = vector_bytes.decode("utf-8")
            vector = json.loads(vector_str)
            result[nmid] = vector
    return result

async def get_keywords_vectors(keywords: list[str]) -> list[tuple[str, list[float]]]:
    """
    Получить вектора для ключевых слов из Redis.
    Ключ: keyword_vector:{keyword}, значение: JSON-сериализованный список float.
    """
    if not keywords:
        return []
    result = []
    for keyword in keywords:
        key = f"keyword_vector:{keyword}"
        vector_bytes = await redis_replica_client.get(key)
        if vector_bytes:
            vector_str = vector_bytes.decode("utf-8")
            vector = json.loads(vector_str)
            result.append((keyword, vector))
    return result



__all__ = [
    "get_clickhouse_client",
    "set_predict_ctrs",
    "get_clusters_and_presets",
    "__calculate_clusters",
    "get_nmid_vectors",
    "get_keywords_vectors"
]

