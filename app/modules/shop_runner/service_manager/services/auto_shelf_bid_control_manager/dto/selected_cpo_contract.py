"""Read-only contract for the selected/current/applied Auto Shelf CPO.

The contract is intentionally narrow: it only exposes the bid that is actually
considered selected/current/applied by the control flow, the corresponding CPO,
and enough metadata to decide whether the value can be safely consumed by a
caller such as the Auto watchdog.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Mapping, Sequence
from typing import cast

from .control_view_dto import AutoShelfBidControlViewDTO


@dataclass(frozen=True, slots=True)
class AutoShelfBidSelectedCpoContract:
    """Selected CPO value together with freshness and provenance metadata."""

    selected_bid_minor: int | None
    selected_cpo_rub: float | None
    updated_at: datetime | None
    source: str
    unavailable_reason: str | None = None

    @property
    def is_available(self) -> bool:
        """Return ``True`` only when the contract is safe to consume."""
        return (
            self.selected_bid_minor is not None
            and self.selected_cpo_rub is not None
            and self.updated_at is not None
            and self.unavailable_reason is None
        )


def as_object_sequence(value: object) -> Sequence[object] | None:
    if isinstance(value, (str, bytes, bytearray)):
        return None
    if isinstance(value, Sequence):
        return cast(Sequence[object], value)
    return None


def as_object_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    object_mapping = cast(Mapping[object, object], value)
    return {str(key): item for key, item in object_mapping.items()}


def coerce_finite_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result):
        return None
    return result


def _unavailable_contract(
    *,
    selected_bid_minor: int | None,
    updated_at: datetime | None,
    reason: str,
) -> AutoShelfBidSelectedCpoContract:
    return AutoShelfBidSelectedCpoContract(
        selected_bid_minor=selected_bid_minor,
        selected_cpo_rub=None,
        updated_at=updated_at,
        source="auto_shelf_bid_control_view_provider.selected_cpo_contract",
        unavailable_reason=reason,
    )


def resolve_selected_cpo_contract_from_view(
    view: AutoShelfBidControlViewDTO,
) -> AutoShelfBidSelectedCpoContract:
    """Resolve the selected CPO from a fresh read-only view DTO.

    The resolver is strict by design:
    - it only accepts the enforced bid for the active mode;
    - it requires the current bid to be synced;
    - it searches the recommendation rows for the exact selected bid;
    - it refuses to fall back to ``plan_ranked[0]`` when the selected bid row is
      missing or stale.
    """
    selected_bid_minor = view.expected_enforced_bid_minor
    updated_at = getattr(view, "state_updated_at", None)

    if not bool(view.enabled):
        return _unavailable_contract(
            selected_bid_minor=selected_bid_minor,
            updated_at=updated_at,
            reason="control_disabled",
        )
    if updated_at is None:
        return _unavailable_contract(
            selected_bid_minor=selected_bid_minor,
            updated_at=updated_at,
            reason="state_updated_at_missing",
        )
    if selected_bid_minor is None:
        return _unavailable_contract(
            selected_bid_minor=None,
            updated_at=updated_at,
            reason="selected_bid_missing",
        )
    if view.actual_bid_minor is None:
        return _unavailable_contract(
            selected_bid_minor=selected_bid_minor,
            updated_at=updated_at,
            reason="actual_bid_missing",
        )
    if int(view.actual_bid_minor) != int(selected_bid_minor):
        return _unavailable_contract(
            selected_bid_minor=selected_bid_minor,
            updated_at=updated_at,
            reason="selected_bid_not_applied",
        )
    if view.bid_sync_detail != "synced":
        return _unavailable_contract(
            selected_bid_minor=selected_bid_minor,
            updated_at=updated_at,
            reason="selected_bid_not_synced",
        )

    recommendation = as_object_dict(view.rec_bid_recommendation)
    if recommendation is None:
        return _unavailable_contract(
            selected_bid_minor=selected_bid_minor,
            updated_at=updated_at,
            reason="recommendation_missing",
        )
    plan_ranked_rows = as_object_sequence(recommendation.get("plan_ranked"))
    if plan_ranked_rows is None:
        return _unavailable_contract(
            selected_bid_minor=selected_bid_minor,
            updated_at=updated_at,
            reason="plan_ranked_missing",
        )

    for raw_row in plan_ranked_rows:
        row = as_object_dict(raw_row)
        if row is None:
            continue
        bid_raw = row.get("bid")
        if isinstance(bid_raw, bool) or not isinstance(bid_raw, int):
            continue
        if int(bid_raw) != int(selected_bid_minor):
            continue
        cpo_raw = row.get("cpo_rub")
        if cpo_raw is None:
            cpo_raw = row.get("expected_order_cost_rub")
        cpo_rub = coerce_finite_float(cpo_raw)
        if cpo_rub is None or cpo_rub < 0:
            return _unavailable_contract(
                selected_bid_minor=selected_bid_minor,
                updated_at=updated_at,
                reason="selected_cpo_missing",
            )
        return AutoShelfBidSelectedCpoContract(
            selected_bid_minor=selected_bid_minor,
            selected_cpo_rub=cpo_rub,
            updated_at=updated_at,
            source=(
                "rec_bid_recommendation.plan_ranked[selected_bid_minor="
                f"{int(selected_bid_minor)}]"
            ),
        )

    return _unavailable_contract(
        selected_bid_minor=selected_bid_minor,
        updated_at=updated_at,
        reason="selected_bid_not_found_in_plan_ranked",
    )


def extract_selected_cpo_details_from_view(
    view: AutoShelfBidControlViewDTO,
) -> tuple[float | None, str | None]:
    """Extract selected bid CPO value and an optional unavailable reason.

    Unlike the strict contract resolver, this helper only searches the
    recommendation rows for the selected/expected bid and returns the CPO
    value when present. It does NOT enforce sync/applied invariants —
    those remain the responsibility of resolve_selected_cpo_contract_from_view.
    The returned reason explains why a CPO value could not be extracted.
    """
    selected_bid_minor = view.expected_enforced_bid_minor
    if selected_bid_minor is None:
        return None, "selected_bid_missing"
    recommendation = as_object_dict(view.rec_bid_recommendation)
    if recommendation is None:
        return None, "recommendation_missing"
    plan_ranked_rows = as_object_sequence(recommendation.get("plan_ranked"))
    if plan_ranked_rows is None:
        return None, "plan_ranked_missing"
    for raw_row in plan_ranked_rows:
        row = as_object_dict(raw_row)
        if row is None:
            continue
        bid_raw = row.get("bid")
        if isinstance(bid_raw, bool) or not isinstance(bid_raw, int):
            continue
        if int(bid_raw) != int(selected_bid_minor):
            continue
        cpo_raw = row.get("cpo_rub")
        if cpo_raw is None:
            cpo_raw = row.get("expected_order_cost_rub")
        cpo_rub = coerce_finite_float(cpo_raw)
        if cpo_rub is None or cpo_rub < 0:
            return None, "selected_cpo_missing"
        return cpo_rub, None
    return None, "selected_bid_not_found_in_plan_ranked"
