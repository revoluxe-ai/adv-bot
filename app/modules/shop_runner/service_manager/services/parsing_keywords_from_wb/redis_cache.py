<<<<<<< HEAD
from app.core.redis_manager.base_redis_manager import KeywordBaseRedis


class LastViewsKeywordsForParser(KeywordBaseRedis):
    @property
    def _key(self) -> str:
        return f"LastViewsKeywordsForParser:{self._adv.adv_id}"
=======
# from app.core.redis_manager.base_redis_manager import KeywordBaseRedis
#
#
# class LastViewsKeywordsForParser(KeywordBaseRedis):
#
#     @property
#     def _key(self) -> str:
#         return f"LastViewsKeywordsForParser:{self._adv.adv_id}"
>>>>>>> 2f5df8c9 (Tempory commit)
