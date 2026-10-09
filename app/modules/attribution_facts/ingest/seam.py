"""Shop-runner seam: ingest raw fullstats chunk до DayStats collapse."""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import cast

from app.modules.attribution_facts.ingest.pipeline import (
    build_ingest_batch_from_raw_items,
)
from app.modules.attribution_facts.membership.resolver import MembershipSnapshotResolver
from app.modules.attribution_facts.ports.campaign_settings_history import (
    CampaignSettingsHistoryAsOfPort,
)
from app.modules.attribution_facts.ports.observation_writer import (
    AttributionObservationWriter,
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
    observation_writer: AttributionObservationWriter | None = None


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


def _physical_adv_id_from_item(item: dict[str, object]) -> int | None:
    for key in ("advertId", "advert_id"):
        raw = item.get(key)
        if raw is None:
            continue
        if not isinstance(raw, (int, str, float)):
            continue
        try:
            adv_id = int(raw)
        except (TypeError, ValueError):
            continue
        if adv_id > 0:
            return adv_id
    return None


def _fullstats_item_to_dict(item: object) -> dict[str, object]:
    if isinstance(item, dict):
        return cast(dict[str, object], item)
    to_dict = getattr(item, "to_dict", None)
    if callable(to_dict):
        raw = to_dict()
        if isinstance(raw, dict):
            return cast(dict[str, object], raw)
    additional = getattr(item, "additional_properties", None)
    if isinstance(additional, dict):
        return cast(dict[str, object], additional)
    return {}


async def maybe_ingest_fullstats_chunk(items: list[object]) -> None:
    """
    Ingest raw apps/nms если activation установлена (Slice B, in-memory).

    Вызывается из fullstats adapter до collapse mapper.
    """
    activation = _active_ingest.get()
    if activation is None or not items:
        return
    raw_dicts = tuple(_fullstats_item_to_dict(item) for item in items)
    raw_items = tuple(
        row
        for row in raw_dicts
        if _physical_adv_id_from_item(row) == activation.physical_adv_id
    )
    if not raw_items:
        logger.warning(
            "attribution ingest skipped: no items for physical_adv_id=%s",
            activation.physical_adv_id,
        )
        return
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
    if activation.observation_writer is not None:
        try:
            await activation.observation_writer.append_batch(batch)
        except Exception:
            logger.exception(
                "attribution persistence failed shop_id=%s adv_id=%s",
                activation.shop_id,
                activation.physical_adv_id,
            )
    logger.debug(
        "attribution ingest batch shop_id=%s adv_id=%s facts=%s coverage=%s",
        activation.shop_id,
        activation.physical_adv_id,
        len(batch.facts),
        batch.coverage.status,
    )
