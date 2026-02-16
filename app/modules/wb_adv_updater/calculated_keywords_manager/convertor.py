from .keyword_setting_dto import KeywordSettingDTO
from ...common_slaves.wildberries.models import KeywordSetting


def keyword_setting_to_keyword_setting_dto(keyword_setting: KeywordSetting) -> KeywordSettingDTO:

    return KeywordSettingDTO(
        text=keyword_setting.text,
        hard_status=keyword_setting.hard_status,
        id= keyword_setting.id,
        target_place=keyword_setting.target_place,
        relevant=keyword_setting.relevant,
        added_clicks=keyword_setting.added_clicks,
    )
