import typing

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.keywords_manager.keywords_manager import KeywordsManager
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatusReason
from app.utils.db.session_maker import get_async_session_maker as sm

if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv

from .exc import FirstKeyUpdaterError


class FirstKeyUpdater:
    def __init__(self, adv: AdvSetting):
        self._adv = adv

    async def top_key_auto_update(
        self,
        complex_adv: "ComplexAdv",
    ) -> None:
        try:
            await self._top_key_auto_update(complex_adv)
        except Exception as exc:
            raise FirstKeyUpdaterError from exc

    async def _top_key_auto_update(
        self,
        complex_adv: "ComplexAdv",
    ) -> None:

        keywords = await complex_adv.get_keywords()
        auto_and_white_list_keywords_without_cooldown_by_min_bid = \
        [kw for kw in keywords if kw.hard_status in (1, 2)
         and kw.reason != KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID]

        if not auto_and_white_list_keywords_without_cooldown_by_min_bid:
            return None
        best = auto_and_white_list_keywords_without_cooldown_by_min_bid[0]
        if best.hard_status == 2:
            return None

        async with sm(read_only=False) as session:
            stmt = (
                update(KeywordSetting)
                .where(KeywordSetting.id == best.keyword_setting_original_id)
                .values(hard_status=2)
            )
            await session.execute(stmt)
            await session.commit()
            from .timestamp_update_redis_cache import LastUpdateFirstPhrase

            timestamp_manager = LastUpdateFirstPhrase(self._adv)
            await timestamp_manager.set_timestamp()

        return None
