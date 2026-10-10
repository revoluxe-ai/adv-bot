"""
Shop headroom state, eligibility и allocator protocol (без production ranking).

Production allocator algorithm — отдельное Owner decision позже.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode


@dataclass(frozen=True, slots=True)
class ShopHeadroomState:
    """Derived signed headroom / pressure (recomputable, не user setting)."""

    configured_target_drr_percent: Decimal
    actual_drr_percent: Decimal | None
    headroom_rub: Decimal | None
    control_pressure: Decimal | None


@dataclass(frozen=True, slots=True)
class CampaignHeadroomEligibility:
    """Eligibility кампании для bounded CPO proposal (без финального rank)."""

    campaign: CampaignRef
    eligible: bool
    reason_codes: tuple[AdControlReasonCode, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BoundedCpoProposal:
    """
    Bounded proposal contract (semantic); не production actuation.

    ``proposed_max_cpo_rub`` для V1 — order-value ``TARGET_CPO_RUB``.
    Catalog-price actuation остаётся заблокированной. Allocator не заполняет
    это поле (``HEADROOM_ALLOCATOR_NOT_ACCEPTED``).
    """

    campaign: CampaignRef
    current_max_cpo_rub: Decimal | None
    proposed_max_cpo_rub: Decimal | None
    decision: str
    reason_codes: tuple[AdControlReasonCode, ...]


class HeadroomAllocator(Protocol):
    """Интерфейс будущего детерминированного allocator (algorithm TBD)."""

    def propose_bounded_adjustments(
        self,
        shop_headroom: ShopHeadroomState,
        eligible_campaigns: tuple[CampaignHeadroomEligibility, ...],
    ) -> tuple[BoundedCpoProposal, ...]:
        """Вернуть bounded proposals; production formula не в foundation slice."""
        ...
