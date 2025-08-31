from typing import Sequence

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.utils.db.session_maker import get_async_session_maker as sm
from .not_relevante_template import NotRelevantTemplate
from .redis_manager import RedisManager


class RelevantPhraseManager:
    def __init__(self, adv: AdvSetting):
        self._adv = adv
        self._redis_manager = RedisManager(adv)

    async def update_black_phrases(self, keywords: list[str]) -> None:
        adv_setting_id = self._adv.id
        await self._redis_manager.set_black_phrases(keywords)
        async with sm(read_only=False) as session:
            stmt = (
                select(KeywordSetting)
                .join(KeywordSetting.adv_setting)
                .where(
                    AdvSetting.id == int(adv_setting_id),
                    KeywordSetting.hard_status != 0,
                )
            )
            result = await session.execute(stmt)
            json_template_data = keywords
            keyword_settings: Sequence[KeywordSetting] = result.scalars().all()
            templator = NotRelevantTemplate(json_template_data)

            for keyword_setting in keyword_settings:
                text = str(keyword_setting.text)
                if not templator.is_relevant(text):
                    keyword_setting.hard_status = 0

            await session.commit()

    async def get_relevant_template_data(self):
        data = await self._redis_manager.get_black_phrases()
        return data
