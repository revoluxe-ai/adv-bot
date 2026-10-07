"""Shop-runner seam: ingest raw fullstats chunk до DayStats collapse."""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from app.modules.attribution_facts.ingest.pipeline import (
    build_ingest_batch_from_raw_items,
)
from app.modules.attribution_facts.membership.resolver import MembershipSnapshotResolver
from app.modules.attribution_facts.ports.campaign_settings_history import (
    CampaignSettingsHistoryAsOfPort,
)
from app.modules.attribution_facts.ports.shop_campaign_inventory import (
    ShopCampaignInventoryNmPort,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AttributionIngestActivation:
    """Контекст одного unmanaged fullstats fetch."""

    shop_id: str
    adv_setting_id: int
    physical_adv_id: int
    history_port: CampaignSettingsHistoryAsOfPort | None
    inventory_port: ShopCampaignInventoryNmPort | None


_active_ingest: ContextVar[AttributionIngestActivation | None] = ContextVar(
    "attribution_ingest_activation",
    default=None,
)
_last_batch_store: ContextVar[object | None] = ContextVar(
    "attribution_last_ingest_batch",
    default=None,
)


def activate_attribution_ingest(
    activation: AttributionIngestActivation,
) -> Token[AttributionIngestActivation | None]:
    """Включить ingest для следующего fullstats chunk fetch."""
    return _active_ingest.set(activation)


def deactivate_attribution_ingest(
    token: Token[AttributionIngestActivation | None],
) -> None:
    """Сбросить ingest activation."""
    _active_ingest.reset(token)


def get_last_ingest_batch() -> object | None:
    """Последний batch (тесты/diagnostics); не persistence."""
    return _last_batch_store.get()


def _fullstats_item_to_dict(item: object) -> dict[str, object]:
    if isinstance(item, dict):
        return item
    to_dict = getattr(item, "to_dict", None)
    if callable(to_dict):
        raw = to_dict()
        if isinstance(raw, dict):
            return raw
    additional = getattr(item, "additional_properties", None)
    if isinstance(additional, dict):
        return additional
    return {}


async def maybe_ingest_fullstats_chunk(items: list[object]) -> None:
    """
    Ingest raw apps/nms если activation установлена (Slice B, in-memory).

    Вызывается из fullstats adapter до collapse mapper.
    """
    activation = _active_ingest.get()
    if activation is None or not items:
        return
    raw_items = tuple(_fullstats_item_to_dict(item) for item in items)
    resolver = MembershipSnapshotResolver(
        shop_id=activation.shop_id,
        adv_setting_id=activation.adv_setting_id,
        physical_adv_id=activation.physical_adv_id,
        history_port=activation.history_port,
        inventory_port=activation.inventory_port,
    )
    try:
        batch = await build_ingest_batch_from_raw_items(
            shop_id=activation.shop_id,
            raw_items=raw_items,
            resolver=resolver,
        )
    except Exception:
        logger.exception(
            "attribution ingest failed shop_id=%s adv_id=%s",
            activation.shop_id,
            activation.physical_adv_id,
        )
        return
    _ = _last_batch_store.set(batch)
    logger.debug(
        "attribution ingest batch shop_id=%s adv_id=%s facts=%s coverage=%s",
        activation.shop_id,
        activation.physical_adv_id,
        len(batch.facts),
        batch.coverage.status,
    )
