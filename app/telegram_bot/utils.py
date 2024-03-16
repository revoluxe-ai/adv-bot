from app import data_managers
from app.my_types import AdvSetting
from dataclasses import dataclass

from app.wildberries.data_classes.keywordstat_from_db import KeywordStatFromDB
from app.wildberries.models import KeywordSetting, WBCategory


@dataclass
class KeywordForKeyboard:
    text: str
    good: bool
    statistic: KeywordStatFromDB
    keyword_settings: KeywordSetting
    adv_setting: AdvSetting
    turn_on: bool


async def get_keywords_for_keyboard(session, adv_setting: AdvSetting)-> list[KeywordForKeyboard]:
    category: WBCategory = await data_managers.get_wb_category(session, adv_setting)
    category_name_to_min_ctr = await data_managers.get_category_name_min_ctr_final_data()
    min_ctr = category_name_to_min_ctr.get(category.wb_category_name, 0)
    good_phrases, bad_phrases = await  data_managers.get_good_bad_phrases(session, adv_setting, min_ctr)
    keyword_stats:list[KeywordStatFromDB] = await data_managers.get_keyword_statistic(session, adv_setting)
    keyword_text_to_keyword_stat = {keyword_stat.text: keyword_stat for keyword_stat in keyword_stats}
    keyword_settings: list[KeywordSetting] = adv_setting.keyword_settings

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






