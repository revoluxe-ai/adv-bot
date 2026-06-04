"""DTO ``UpdatePipeline`` — re-export ``AdvState`` из keyword_dto."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.adv_state import (
    AdvState,
)

__all__ = ["AdvState"]
