"""Политика membership role для одной физической ноги (PG nmids authority)."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.product_control.domain.bindings import MembershipEvidence
from app.modules.product_control.domain.enums import MembershipRole


def normalize_leg_nmids(nmids: Sequence[int]) -> tuple[int, ...]:
    """Дедуп и детерминированный порядок (сортировка уникальных nmID)."""
    return tuple(sorted(dict.fromkeys(nmids)))


def resolve_leg_membership_role(
    nmids: Sequence[int],
    *,
    provenance_source: str = "PG_NMIDS",
) -> tuple[MembershipRole, MembershipEvidence | None]:
    """
    PRIMARY только при ровно одном уникальном nmID на ноге.

    Пустой список и >1 unique → UNKNOWN без evidence.
    """
    unique = normalize_leg_nmids(nmids)
    if len(unique) == 1:
        return (
            MembershipRole.PRIMARY,
            MembershipEvidence(
                source=provenance_source,
                detail="single_unique_nmid_on_leg",
            ),
        )
    return MembershipRole.UNKNOWN, None
