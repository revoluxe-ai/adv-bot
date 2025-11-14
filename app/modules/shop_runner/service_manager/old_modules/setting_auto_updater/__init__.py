"""
Модуль дальше не поддерживается, новый модуль

 - app/modules/shop_runner/service_manager/old_modules/setting_auto_updater_v2

"""

__all__ = [
    "AdvSettingAutoUpdater",
    "SettingAutoUpdaterCriticalError",
    "get_control_spend_sum",
    "last_auto_update_phrases_to_white_list",
]


from .click_house_control_spend_sum import (
    get_sum_spend_for_complex_adv as get_control_spend_sum,
)
from .exc import SettingAutoUpdaterCriticalError
from .modules.white_list_updater.auto_white_list_updater.redis_cache import (
    last_auto_update_phrases_to_white_list,
)
from .setting_auto_updater import AdvSettingAutoUpdater
