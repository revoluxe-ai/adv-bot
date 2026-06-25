"""Загрузка данных тика V3 для ``UpdateContextManager``."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.dto import (
    TickData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager import (
    DataUpdateManager,
)

__all__ = ("DataUpdateManager", "TickData")
