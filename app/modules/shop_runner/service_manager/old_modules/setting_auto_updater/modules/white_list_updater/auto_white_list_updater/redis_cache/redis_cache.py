from app.modules.common_slaves.wildberries.models import AdvSetting
from .last_auto_update_phrases_to_white_list import (
    LastAutoDeleteFromWhiteList,
    LastAutoAddPhraseToWhiteList,
)


class AdvSettingRedisCache:
    def __init__(self, adv: AdvSetting):
        self.last_auto_adding_phrase_to_white_list = LastAutoAddPhraseToWhiteList(adv)

        self.last_auto_delete_white_list = LastAutoDeleteFromWhiteList(adv)
