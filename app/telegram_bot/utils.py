from typing import Union

from sqlalchemy import select

from app import data_managers
from app.my_types import AdvSetting
from dataclasses import dataclass

from app.wildberries.data_classes.keywordstat_from_db import KeywordStatFromDB
from app.wildberries.models import KeywordSetting, WBCategory
from app.session_maker import get_async_session_maker


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
    good_phrases, bad_phrases = await  data_managers.get_good_bad_phrases(adv_setting, min_ctr)
    keyword_stats:list[KeywordStatFromDB] = await data_managers.get_keyword_statistic( adv_setting)
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






