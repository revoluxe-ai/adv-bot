import datetime
from dataclasses import dataclass
from typing import Union

from sqlalchemy import and_, select

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import KeywordSetting, WBCategory
from app.modules.wb_adv_updater import data_manager
from app.my_types import AdvSetting
from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker

@dataclass
class KeywordForKeyboard:
    text: str
    good: bool
    statistic: CalculatedKeyword
    keyword_settings: KeywordSetting
    adv_setting: AdvSetting
    turn_on: bool
    bad_reason: Union[str, None] = None


async def get_keywords_for_keyboard( adv_setting: AdvSetting)-> list[CalculatedKeyword]:
    all_phrases: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv_setting)

    all_phrases.sort(key=lambda keyword: keyword.ctr, reverse=True)

    return all_phrases



async def create_ref_link(ref_link_name, user_telegram_id):
    stmt = select(RefLink).where(and_(RefLink.name == ref_link_name, RefLink.referrer_id == user_telegram_id))
    async with _sm() as session:
        result = await session.execute(stmt)
        ref_link = result.scalar_one_or_none()
        if ref_link:
            return False
        stmt = select(User.id).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user_id = result.scalar_one()
        ref_link = RefLink(name=ref_link_name, referrer_id=user_id)
        session.add(ref_link)
        await session.commit()
        return ref_link


