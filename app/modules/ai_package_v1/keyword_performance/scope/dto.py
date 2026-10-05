"""Internal DTO keyword scope (не публичный ExportScopeAdv)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeywordScopeRow:
    """Logical resource anchor + rebound membership для keyword export."""

    shop_id: str
    adv_setting_id: int
    auto_adv_id: int
    search_adv_id: int | None
    main_nmid: int | None
    rebound_auto_adv_ids: frozenset[int]
    rebound_search_adv_ids: frozenset[int]

    @property
    def all_adv_ids(self) -> frozenset[int]:
        """Deduped superset adv_ids для CH filter."""
        ids: set[int] = {self.auto_adv_id}
        if self.search_adv_id is not None:
            ids.add(self.search_adv_id)
        ids.update(self.rebound_auto_adv_ids)
        ids.update(self.rebound_search_adv_ids)
        return frozenset(ids)

    @property
    def proven_nmids(self) -> frozenset[int]:
        """Inventory nmids when main_nmid proven."""
        if self.main_nmid is None:
            return frozenset()
        return frozenset({self.main_nmid})


@dataclass(frozen=True, slots=True)
class AdvIdAssignment:
    """Mapping physical adv_id → logical resource + leg role."""

    adv_id: int
    shop_id: str
    adv_setting_id: int
    leg_role: str
    ambiguous_leg: bool = False
    ambiguous_ownership: bool = False
    foreign_shop: bool = False


@dataclass(frozen=True, slots=True)
class KeywordExportScope:
    """Resolved scope после expansion + ownership validation."""

    rows: tuple[KeywordScopeRow, ...]
    assignments: tuple[AdvIdAssignment, ...]
    all_adv_ids: frozenset[int]
    all_nmids: frozenset[int]
    reason_codes: frozenset[str]
    rebound_unavailable: bool = False
