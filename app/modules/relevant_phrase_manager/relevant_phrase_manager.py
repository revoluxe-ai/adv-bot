from collections.abc import Sequence

from sqlalchemy import select, update

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from .not_relevante_template import NotRelevantTemplate


class RelevantPhraseManager:
    def __init__(self, adv: AdvSetting):
        self._adv = adv

    async def update_black_phrases(self, keywords: list[str]) -> None:
        adv_setting_id = self._adv.id
        async with sm(read_only=False) as session:
            await session.execute(
                update(AdvSetting)
                .where(AdvSetting.id == adv_setting_id)
                .values(black_phrases=keywords)
            )
            stmt = (
                select(KeywordSetting)
                .join(KeywordSetting.adv_setting)
                .where(
                    AdvSetting.id == int(adv_setting_id),
                    KeywordSetting.hard_status != 0,
                )
            )
            result = await session.execute(stmt)
            keyword_settings: Sequence[KeywordSetting] = result.scalars().all()
            templator = NotRelevantTemplate(keywords)

            for keyword_setting in keyword_settings:
                if keyword_setting.hard_status == 4:  # фикс.фразы — не переводить в чёрный список
                    continue
                text = str(keyword_setting.text)
                if not templator.is_relevant(text):
                    keyword_setting.hard_status = 0
                    keyword_setting.relevant = False

            await session.commit()

    async def get_relevant_template_data(self) -> list[str]:
        result = getattr(self._adv, "black_phrases", None)
        if result is None:
            return []
        if not isinstance(result, list):
            return []
        return result
