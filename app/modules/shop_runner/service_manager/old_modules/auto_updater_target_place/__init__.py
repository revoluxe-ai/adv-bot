"""Target-place auto-updater subpackage.

Keep this module free of eager imports from ``setting_auto_updater`` / white_list
telegram — importing :mod:`last_target_place_update_redis_manager` must not
trigger those graphs (e.g. when :mod:`plan_fact.provider` or
:mod:`common_advs_stat` is still loading).
"""

from __future__ import annotations

__all__ = [
    "LastTargetPlaceUpdateRedisManager",
    "auto_updater_target_place_setting_router",
    "RelevantKeywordStatusSetting",
]


def __getattr__(name: str):
    if name == "LastTargetPlaceUpdateRedisManager":
        from .last_target_place_update_redis_manager import (
            LastTargetPlaceUpdateRedisManager,
        )

        return LastTargetPlaceUpdateRedisManager
    if name == "auto_updater_target_place_setting_router":
        from .telegram import auto_updater_target_place_setting_router

        return auto_updater_target_place_setting_router
    if name == "RelevantKeywordStatusSetting":
        from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater.telegram.callbacks import (
            RelevantKeywordStatusSetting,
        )

        return RelevantKeywordStatusSetting
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
