from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from .old_modules import LastTargetPlaceUpdateRedisManager
from .old_modules.setting_auto_updater.modules.first_key_updater.timestamp_update_redis_cache import (
    LastUpdateFirstPhrase,
)
from .old_modules.setting_auto_updater.modules.target_place_updater.redis_cache import (
    LastSetDownTargetPlace,
    LastSetUpTargetPlace,
)

__all__ = ["CoroutinesManager", "LastSetUpTargetPlace", "LastSetDownTargetPlace"]

if TYPE_CHECKING:
    from .manager import CoroutinesManager


def __getattr__(name: str):
    if name == "CoroutinesManager":
        module = import_module(".manager", __name__)
        attr = module.CoroutinesManager
        globals()["CoroutinesManager"] = attr
        return attr
    raise AttributeError(f"module {__name__} has no attribute {name}")
