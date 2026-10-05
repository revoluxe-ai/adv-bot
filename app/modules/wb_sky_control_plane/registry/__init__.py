"""Registry cmp_* resource identity."""

from app.modules.wb_sky_control_plane.registry.anchor import (
    build_anchor_fingerprint,
    generate_resource_id,
)
from app.modules.wb_sky_control_plane.registry.backfill import (
    BackfillStats,
    backfill_campaign_resource_registry,
)
from app.modules.wb_sky_control_plane.registry.model import WbSkyCampaignResourceRegistry

__all__ = [
    "BackfillStats",
    "WbSkyCampaignResourceRegistry",
    "backfill_campaign_resource_registry",
    "build_anchor_fingerprint",
    "generate_resource_id",
]
