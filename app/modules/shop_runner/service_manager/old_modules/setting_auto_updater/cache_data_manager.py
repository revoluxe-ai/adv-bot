# from app.core.redis_manager.base_redis_manager import BaseRedis
# from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
#     CalculatedKeyword,
# )
# from app.modules.common_slaves.wildberries.models import AdvSetting
#
#
# class LastSpendByKeywords(BaseRedis):
#     def __init__(self, adv: AdvSetting):
#         self._adv = adv
#
#     @property
#     def _key(self) -> str:
#         key = f"LastSpendByKeywords:{self._adv.adv_id}"
#         return key
#
#     async def set(self, keywords: list[CalculatedKeyword]):
#         value = sum([kw.spend for kw in keywords])
#         value = int(value * 100)
#         key = self._key
#         await self.client.set(key, value)
#
#     async def _get(self) -> int | None:
#         key = self._key
#         value = await self.client.get(key)
#         if not value:
#             return None
#         value = int(int(value.decode()) / 100)
#         return value
#
#     async def check_change_spend(self, keywords: list[CalculatedKeyword]):
#         new_spend = sum(kw.spend for kw in keywords)
#         new_spend = int(new_spend) * 100
#         last_spend: int | None = await self._get()
#         return not new_spend == last_spend
