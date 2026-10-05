"""PG read-only AdvSetting policy projection for keyword current state.

``max_cpm`` — policy CAP (``configured_max_cpm``), не текущая применённая ставка.
``current_bid_evidence`` экспортируется только при доказанном persisted bid source;
иначе явный ``UNAVAILABLE`` (cap ≠ applied bid).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.ai_package_v1.keyword_performance.readers.pg_session_adapter import (
    default_pg_session_factory,
)
from app.modules.ai_package_v1.scope.pg_adv_setting_inventory_reader import (
    PgAdvSettingInventoryReader,
    SessionMakerProtocol,
)


@dataclass(frozen=True, slots=True)
class CampaignPolicySnapshot:
    """Campaign-level PG policy keyed by adv_setting_id (не per-keyword)."""

    adv_setting_id: int
    configured_max_cpm: float | None
    bidder_active: bool | None
    campaign_active_status: str | None
    strategy_status: str | None
    min_target_position: int | None
    target_position_mode: str | None


def _enum_text(value: object) -> str | None:
    if value is None:
        return None
    inner = getattr(value, "value", value)
    return str(inner) if inner is not None else None


def _configured_max_cpm(row: object) -> float | None:
    """Policy cap from AdvSetting.max_cpm when bidder is active."""
    bidder_active = getattr(row, "bidder_active", None)
    max_cpm = getattr(row, "max_cpm", None)
    if bidder_active is not True or max_cpm is None:
        return None
    if isinstance(max_cpm, (int, float)):
        return float(max_cpm)
    return None


def _campaign_policy(row: object) -> CampaignPolicySnapshot:
    row_id = getattr(row, "id", None)
    if not isinstance(row_id, int):
        raise TypeError("AdvSetting row must have int id")
    return CampaignPolicySnapshot(
        adv_setting_id=row_id,
        configured_max_cpm=_configured_max_cpm(row),
        bidder_active=getattr(row, "bidder_active", None),
        campaign_active_status=getattr(row, "active_status", None),
        strategy_status=_enum_text(getattr(row, "strategy", None)),
        min_target_position=getattr(row, "min_target_position", None),
        target_position_mode=_enum_text(getattr(row, "target_position_mode", None)),
    )


class PgKeywordPolicyReader:
    """Load campaign-level policy from AdvSetting for ACTIVE current-state rows."""

    def __init__(
        self,
        inventory_reader: PgAdvSettingInventoryReader | None = None,
        *,
        session_maker: SessionMakerProtocol | None = None,
    ) -> None:
        if inventory_reader is not None:
            self._inventory = inventory_reader
        else:
            maker = session_maker or default_pg_session_factory
            self._inventory = PgAdvSettingInventoryReader(maker)

    async def load_policies(
        self, shop_id: str, adv_setting_ids: frozenset[int]
    ) -> dict[int, CampaignPolicySnapshot]:
        """Return campaign policy snapshots for requested adv_setting PKs in shop."""
        if not adv_setting_ids:
            return {}
        inventory = await self._inventory.load_inventory(shop_id)
        result: dict[int, CampaignPolicySnapshot] = {}
        for row in inventory:
            row_id = row.id
            if row_id not in adv_setting_ids:
                continue
            cabinet = getattr(row, "wb_cabinet", None)
            if getattr(cabinet, "shop_id", None) != shop_id:
                continue
            result[row_id] = _campaign_policy(row)
        return result
