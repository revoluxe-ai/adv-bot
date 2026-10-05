"""Conservative spend mapping: FACTUAL only from clusters_adv_stats.spend."""

from __future__ import annotations

from app.modules.ai_package_v1.keyword_performance.domain.enums import QuerySpendStatus
from app.modules.ai_package_v1.keyword_performance.domain.derived_metrics import (
    finite_or_none,
)


def map_spend(spend: float | None) -> tuple[float | None, QuerySpendStatus]:
    """Map raw spend column; forbid CPM×views fabrication.

    Args:
        spend: Nullable spend from CH snapshot tuple.

    Returns:
        (spend_rub, query_spend_status) — UNAVAILABLE when null.
    """
    if spend is None:
        return None, QuerySpendStatus.UNAVAILABLE
    value = finite_or_none(spend)
    if value is None:
        return None, QuerySpendStatus.UNAVAILABLE
    return value, QuerySpendStatus.FACTUAL
