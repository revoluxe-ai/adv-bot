from predict_ctr_service.utils.redis_manager import get_nmid_vectors, get_keywords_vectors
from typing import Set, Dict, List, Tuple


class DataGetter:
    @staticmethod
    async def get_item_features_from_redis(nmids_batch: Set[int]) -> Dict[int, List[float]]:
        result = await get_nmid_vectors(nmids_batch)
        if not isinstance(result, dict):
            return {}
        # Приведение типов для mypy
        return dict(result)

    @staticmethod
    async def get_keyword_features_from_redis(
        keywords: List[str],
    ) -> List[Tuple[str, List[float]]]:
        result = await get_keywords_vectors(keywords)
        if not isinstance(result, list):
            return []
        return list(result)
