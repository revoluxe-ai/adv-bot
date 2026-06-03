"""Re-export ``UpdateContextManager`` из ``keywords_prepared``."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    UpdateContextManager,
)

__all__ = ["UpdateContextManager"]
