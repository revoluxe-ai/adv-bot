"""MembershipSnapshotResolver: history → inventory fallback → fail-closed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.attribution_facts.domain.enums import AttributionReasonCode
from app.modules.attribution_facts.domain.models import MembershipSnapshot
from app.modules.attribution_facts.membership.as_of import (
    event_date_observed_lower_bound,
    event_date_observed_upper_bound,
    select_as_of_snapshot,
)
from app.modules.attribution_facts.membership.payload import (
    empty_promoted_is_ambiguous,
    promoted_nm_ids_from_payload,
)
from app.modules.attribution_facts.ports.campaign_settings_history import (
    CampaignSettingsHistoryAsOfPort,
)
from app.modules.attribution_facts.ports.shop_campaign_inventory import (
    ShopCampaignInventoryNmPort,
)


@dataclass(frozen=True, slots=True)
class MembershipResolveResult:
    """Результат resolver с provenance и reason codes."""

    snapshot: MembershipSnapshot | None
    partial_fallback: bool
    reason_codes: tuple[AttributionReasonCode, ...] = ()


class MembershipSnapshotResolver:
    """
    As-of membership для physical adv_id и event_date.

    Precedence: history covering date → inventory fallback → UNKNOWN.
    """

    def __init__(
        self,
        *,
        shop_id: str,
        adv_setting_id: int,
        physical_adv_id: int,
        history_port: CampaignSettingsHistoryAsOfPort | None,
        inventory_port: ShopCampaignInventoryNmPort | None,
        collect_time_promoted_nm_ids: frozenset[int] | None = None,
    ) -> None:
        self._shop_id = shop_id
        self._adv_setting_id = adv_setting_id
        self._physical_adv_id = physical_adv_id
        self._history = history_port
        self._inventory = inventory_port
        self._collect_time_promoted = collect_time_promoted_nm_ids

    async def resolve(self, event_date: date) -> MembershipResolveResult:
        """
        Построить MembershipSnapshot для event_date.

        Returns:
            MembershipResolveResult; snapshot None → UNKNOWN classification.
        """
        if self._history is not None:
            range_start = event_date_observed_lower_bound(event_date)
            range_end = event_date_observed_upper_bound(event_date)
            timeline = await self._history.snapshots_covering(
                self._adv_setting_id,
                range_start=range_start,
                range_end=range_end,
            )
            picked = select_as_of_snapshot(timeline, event_date)
            if picked is not None:
                promoted = promoted_nm_ids_from_payload(picked.payload_json)
                if empty_promoted_is_ambiguous(promoted):
                    return MembershipResolveResult(
                        snapshot=None,
                        partial_fallback=False,
                        reason_codes=(
                            AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN,
                        ),
                    )
                return MembershipResolveResult(
                    snapshot=MembershipSnapshot(
                        snapshot_id=picked.snapshot_id,
                        shop_id=self._shop_id,
                        physical_adv_id=self._physical_adv_id,
                        event_date=event_date,
                        promoted_nm_ids=promoted or frozenset(),
                        authoritative=True,
                        partial_fallback=False,
                    ),
                    partial_fallback=False,
                )
        if self._inventory is not None:
            nm_ids = await self._inventory.nm_ids_for_adv(
                self._shop_id,
                self._physical_adv_id,
            )
            if nm_ids:
                return MembershipResolveResult(
                    snapshot=MembershipSnapshot(
                        snapshot_id=f"inventory:{self._physical_adv_id}:{event_date.isoformat()}",
                        shop_id=self._shop_id,
                        physical_adv_id=self._physical_adv_id,
                        event_date=event_date,
                        promoted_nm_ids=frozenset(nm_ids),
                        authoritative=True,
                        partial_fallback=True,
                    ),
                    partial_fallback=True,
                    reason_codes=(
                        AttributionReasonCode.ATTRIBUTION_SOURCE_PARTIAL,
                    ),
                )
        return MembershipResolveResult(
            snapshot=None,
            partial_fallback=False,
            reason_codes=(AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN,),
        )
