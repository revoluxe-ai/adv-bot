import typing

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatusReason
from app.utils.db.session_maker import get_async_session_maker as sm

if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv

from app.modules.shop_runner.required_data_miss import is_required_data_miss

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
            if is_required_data_miss(exc):
                raise
            raise FirstKeyUpdaterError from exc

    async def _top_key_auto_update(
        self,
        complex_adv: "ComplexAdv",
    ) -> None:
        keywords = await complex_adv.get_keywords()
        # Пул 1/2/4 (без НРФ 0 и откл. 3) и без причины «МС». По рейтингу лидер
        # может быть белым списком (2) или always-on (4) — тогда не трогаем БД.
        clear_keywords = [
            kw
            for kw in keywords
            if kw.hard_status not in (0, 3)
            and kw.reason != KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
        ]
        if not clear_keywords:
            return None
        clear_keywords.sort(key=lambda kw: kw.rating or 0, reverse=True)

        # Respect user setting: when enabled, auto-promote only relevant phrases.
        candidates = (
            [kw for kw in clear_keywords if kw.relevant]
            if self._adv.auto_add_only_relevant_phrase
            else clear_keywords
        )
        if not candidates:
            return None

        top = candidates[0]
        if top.hard_status != 1:
            return None
        async with sm(read_only=False) as session:
            stmt = (
                update(KeywordSetting)
                .where(KeywordSetting.id == top.keyword_setting_original_id)
                .values(hard_status=2)
            )
            _ = await session.execute(stmt)
            await session.commit()
            from .timestamp_update_redis_cache import LastUpdateFirstPhrase

            timestamp_manager = LastUpdateFirstPhrase(self._adv)
            await timestamp_manager.set_timestamp()

        return None
