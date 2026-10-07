"""Хуки shop-runner unmanaged collect для attribution ingest (Slice B)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from app.modules.attribution_facts.ingest.seam import (
    AttributionIngestActivation,
    activate_attribution_ingest,
    deactivate_attribution_ingest,
)
from app.modules.attribution_facts.ports.campaign_settings_history import (
    CampaignSettingsHistoryAsOfPort,
)
from app.modules.attribution_facts.ports.shop_campaign_inventory import (
    ShopCampaignInventoryNmPort,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)


def adv_setting_id_for_physical_adv(
    loader_complex_advs: Sequence[ComplexAdv],
    physical_adv_id: int,
) -> int | None:
    """
    Найти adv_setting_id для physical WB adv_id (Auto или Search leg).

    Args:
        loader_complex_advs: ComplexAdv из shop-runner loader.
        physical_adv_id: WB advertId из fullstats.
    """
    for complex_adv in loader_complex_advs:
        if complex_adv.adv_id == physical_adv_id:
            return complex_adv.adv_setting_original_id
        if complex_adv.search_adv_id == physical_adv_id:
            return complex_adv.adv_setting_original_id
    return None


@asynccontextmanager  # pyright: ignore[reportDeprecated]
async def attribution_ingest_for_fetch(
    *,
    shop_id: str,
    physical_adv_id: int,
    adv_setting_id: int,
    history_port: CampaignSettingsHistoryAsOfPort | None,
    inventory_port: ShopCampaignInventoryNmPort | None,
) -> AsyncIterator[None]:
    """Activation context на время одного fullstats fetch."""
    token = activate_attribution_ingest(
        AttributionIngestActivation(
            shop_id=shop_id,
            adv_setting_id=adv_setting_id,
            physical_adv_id=physical_adv_id,
            history_port=history_port,
            inventory_port=inventory_port,
        )
    )
    try:
        yield
    finally:
        deactivate_attribution_ingest(token)
