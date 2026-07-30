"""Telegram router package для A/B Hold UI."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_handlers import (
    card_ab_hold_confirm_router,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.handlers import (
    card_ab_hold_router,
)
# Регистрация Emergency callbacks на том же router (side-effect import).
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    emergency_handlers as _emergency_handlers,  # noqa: F401
)

_ = _emergency_handlers  # keep side-effect registration reachable for pyright

__all__ = ["card_ab_hold_router", "card_ab_hold_confirm_router"]
