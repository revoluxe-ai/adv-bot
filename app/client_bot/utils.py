import datetime
from dataclasses import dataclass
from typing import Union

from sqlalchemy import and_, select

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import KeywordStatFromDB
from app.modules.common_slaves.wildberries.models import KeywordSetting, WBCategory
from app.modules.wb_adv_updater import data_managers
from app.my_types import AdvSetting
from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker()

@dataclass
class KeywordForKeyboard:
    text: str
    good: bool
    statistic: KeywordStatFromDB
    keyword_settings: KeywordSetting
    adv_setting: AdvSetting
    turn_on: bool


async def get_keywords_for_keyboard( adv_setting: AdvSetting)-> list[KeywordForKeyboard]:
    category: Union[WBCategory, None] = await data_managers.get_wb_category(adv_setting)
    if not category:
        return []
    category_name_to_min_ctr = await data_managers.get_category_name_min_ctr_final_data()
    min_ctr = category_name_to_min_ctr.get(category.wb_category_name, 0)
    good_phrases, bad_phrases = await data_managers.get_good_bad_phrases(adv_setting, min_ctr)
    pass_days =  datetime.timedelta(days=adv_setting.pass_days)

    keyword_stats:list[KeywordStatFromDB] = await data_managers.get_keywords_statistic(adv_setting, pass_days)
    keyword_text_to_keyword_stat = {keyword_stat.text: keyword_stat for keyword_stat in keyword_stats}
    async with _sm () as session:
        stmt = (
            select(KeywordSetting)
            .where(KeywordSetting.adv_setting_id == adv_setting.id)
        )
        result = await session.execute(stmt)

    keyword_settings = result.scalars().all()
    keywords = []
    for keyword_setting in keyword_settings:
        text = keyword_setting.text
        if keyword_stat := keyword_text_to_keyword_stat.get(text):
            keyword = KeywordForKeyboard(text=keyword_setting.text,
                                         good = True if text in good_phrases else False,
                                         statistic=keyword_stat,
                                         keyword_settings=keyword_setting,
                                         adv_setting=adv_setting,
                                         turn_on = True if text in good_phrases else False)
            keywords.append(keyword)

    keywords.sort(key=lambda keyword: keyword.statistic.ctr, reverse=True)

    return keywords


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


