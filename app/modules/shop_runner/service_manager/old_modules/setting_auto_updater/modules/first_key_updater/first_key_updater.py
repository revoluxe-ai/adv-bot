from collections.abc import Awaitable

from sqlalchemy import update


from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.utils.db.session_maker import get_async_session_maker as sm

from .exc import FirstKeyUpdaterError


class FirstKeyUpdater:
    def __init__(self, adv: AdvSetting):
        self._adv = adv

    async def top_key_auto_update(
        self,
        complex_adv: ComplexAdv,
    ) -> None:
        keywords = await complex_adv.get_keywords()

        try:
            await self._top_key_auto_update(keywords)
        except Exception as exc:
            raise FirstKeyUpdaterError from exc

    async def _top_key_auto_update(
        self,
        keywords: list[CalculatedKeyword],
    ) -> None:
        if not keywords:
            return None
        clear_keywords = [kw for kw in keywords if kw.hard_status not in [0, 3]]
        if not clear_keywords:
            return None
        clear_keywords = sorted(
            clear_keywords, key=lambda kw: kw.rating_by_orders, reverse=True
        )
        top_key = clear_keywords[0]
        if top_key.hard_status == 2:
            return None
        # TODO: Сделать кнопку добавления не только релевантных фраз
        if self._adv.auto_add_only_relevant_phrase:
            relevant_phrases = [kw for kw in clear_keywords if kw.relevant]
        else:
            relevant_phrases = clear_keywords
        if not relevant_phrases:
            return None
        top_relevant_phrase = relevant_phrases[0]
        if top_relevant_phrase.hard_status == 2:
            return None

        async with sm(read_only=False) as session:
            stmt = (
                update(KeywordSetting)
                .where(
                    KeywordSetting.id == top_relevant_phrase.keyword_setting_original_id
                )
                .values(hard_status=2)
            )
            await session.execute(stmt)
            await session.commit()
            from .timestamp_update_redis_cache import LastUpdateFirstPhrase

            timestamp_manager = LastUpdateFirstPhrase(self._adv)
            await timestamp_manager.set_timestamp()

        return None
