"""Shop-wide common-sales coordinator helpers (assortment, coverage, TaskGroup seams)."""

from .legacy_assigned_nmids import LegacyAssignedSnapshot, resolve_legacy_assigned_nmids
from .shop_assortment_reader import AssortmentPaginationResult, ShopAssortmentReader
from .taskgroup_no_ad_supervisor import (
    SUPERVISOR_COROUTINE_NAMES,
    taskgroup_no_ad_supervisor,
)

__all__ = [
    "AssortmentPaginationResult",
    "LegacyAssignedSnapshot",
    "ShopAssortmentReader",
    "SUPERVISOR_COROUTINE_NAMES",
    "resolve_legacy_assigned_nmids",
    "taskgroup_no_ad_supervisor",
]
