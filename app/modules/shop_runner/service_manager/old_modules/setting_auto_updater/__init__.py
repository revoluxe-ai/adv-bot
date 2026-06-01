"""
Модуль дальше не поддерживается, новый модуль

 - app/modules/shop_runner/service_manager/old_modules/setting_auto_updater_v2

Public names are loaded lazily to avoid import cycles with plan_fact / common_advs_stat.
"""

from __future__ import annotations

__all__ = [
    "AdvSettingAutoUpdater",
    "SettingAutoUpdaterCriticalError",
    "get_control_spend_sum",
    "last_auto_update_phrases_to_white_list",
]


def __getattr__(name: str):
    if name == "AdvSettingAutoUpdater":
        from .setting_auto_updater import AdvSettingAutoUpdater

        return AdvSettingAutoUpdater
    if name == "SettingAutoUpdaterCriticalError":
        from .exc import SettingAutoUpdaterCriticalError

        return SettingAutoUpdaterCriticalError
    if name == "get_control_spend_sum":
        from .click_house_control_spend_sum import (
            get_sum_spend_for_complex_adv as get_control_spend_sum,
        )

        return get_control_spend_sum
    if name == "last_auto_update_phrases_to_white_list":
        from .modules.white_list_updater.auto_white_list_updater.redis_cache import (
            last_auto_update_phrases_to_white_list,
        )

        return last_auto_update_phrases_to_white_list
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
