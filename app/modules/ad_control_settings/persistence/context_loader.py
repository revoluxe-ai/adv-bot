"""
Adapter: persistence rows → ``ResolverContext`` slot maps.

Campaign row absence => INHERIT at resolver (default slot), never copy shop payload.
"""

from __future__ import annotations

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.enums import AdControlFeatureId
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ShopFeatureSlot,
)
from app.modules.ad_control_settings.persistence.repository import AdControlSettingsRepository


async def load_resolver_shop_features(
    repository: AdControlSettingsRepository,
    shop_id: str,
) -> dict[AdControlFeatureId, ShopFeatureSlot]:
    """Load shop configured slots for resolver input."""
    return await repository.load_shop_slots(shop_id)


async def load_resolver_campaign_features(
    repository: AdControlSettingsRepository,
    campaign: CampaignRef,
) -> dict[AdControlFeatureId, CampaignFeatureSlot]:
    """
    Load only persisted campaign authority.

    Features without rows are omitted; resolver defaults them to INHERIT.
    """
    return await repository.load_campaign_slots(campaign)
