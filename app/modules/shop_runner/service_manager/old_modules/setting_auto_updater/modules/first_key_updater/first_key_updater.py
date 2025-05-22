from typing import Awaitable

from sqlalchemy import update

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import KeywordSetting, AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm
from .exc import FirstKeyUpdaterError


class FirstKeyUpdater:

    def __init__(self, adv: AdvSetting):
        self._adv = adv

    async def top_key_auto_update(
        self,
        keywords_coroutine: Awaitable[list[CalculatedKeyword]],
    ) -> None:

        keywords = await keywords_coroutine

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

        keywords = list(
            filter(lambda kw: kw.relevant and kw.hard_status == 1, keywords)
        )
        if not keywords:
            return None
        keywords = sorted(
            keywords, key=lambda kw: kw.rating_by_predict_ctr, reverse=True
        )
        top_keyword: CalculatedKeyword = keywords[0]
        if top_keyword.hard_status == 2:
            return None
        async with sm(read_only=False) as session:
            stmt = (
                update(KeywordSetting)
                .where(KeywordSetting.id == top_keyword.keyword_setting_original_id)
                .values(hard_status=2)
            )
            await session.execute(stmt)
            await session.commit()
            from .timestamp_update_redis_cache import LastUpdateFirstPhrase

            timestamp_manager = LastUpdateFirstPhrase(self._adv)
            await timestamp_manager.set_timestamp()

        return None
