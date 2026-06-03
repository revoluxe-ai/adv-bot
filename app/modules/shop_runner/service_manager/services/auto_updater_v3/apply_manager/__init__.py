"""Персист итогового состояния V3-тика в БД/Redis."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.dto import (
    V3ApplyInput,
    V3ApplyResult,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager import (
    ApplyManager,
)

__all__ = ("ApplyManager", "V3ApplyInput", "V3ApplyResult")
