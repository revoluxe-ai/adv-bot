"""Telegram router package для A/B Hold UI."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_handlers import (
    card_ab_hold_confirm_router,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.handlers import (
    card_ab_hold_router,
)

__all__ = ["card_ab_hold_router", "card_ab_hold_confirm_router"]
