"""Dedupe adv_ids, leg_role assignment, ownership overlap validation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    KeywordLegRole,
    KeywordReasonCode,
)
from app.modules.ai_package_v1.keyword_performance.scope.dto import (
    AdvIdAssignment,
    KeywordExportScope,
    KeywordScopeRow,
)


def assign_leg_roles(row: KeywordScopeRow) -> dict[int, KeywordLegRole]:
    """Map adv_id → leg role; AMBIGUOUS when adv_id in multiple slots."""
    slots: dict[int, list[KeywordLegRole]] = defaultdict(list)
    slots[row.auto_adv_id].append(KeywordLegRole.AUTO)
    if row.search_adv_id is not None:
        slots[row.search_adv_id].append(KeywordLegRole.SEARCH)
    for adv_id in row.rebound_auto_adv_ids:
        slots[adv_id].append(KeywordLegRole.REBOUND_AUTO)
    for adv_id in row.rebound_search_adv_ids:
        slots[adv_id].append(KeywordLegRole.REBOUND_SEARCH)
    result: dict[int, KeywordLegRole] = {}
    for adv_id, roles in slots.items():
        unique = set(roles)
        if len(unique) == 1:
            result[adv_id] = unique.pop()
        else:
            result[adv_id] = KeywordLegRole.AMBIGUOUS
    return result


def build_assignments(
    rows: Sequence[KeywordScopeRow],
    global_overlap: Mapping[int, list[tuple[str, int]]],
) -> tuple[tuple[AdvIdAssignment, ...], frozenset[str]]:
    """Build adv_id assignments with requested-shop + global overlap probes."""
    assignments: list[AdvIdAssignment] = []
    reason_codes: set[str] = set()
    requested_shop = rows[0].shop_id if rows else ""

    for row in rows:
        leg_map = assign_leg_roles(row)
        for adv_id, leg_role in leg_map.items():
            ambiguous_leg = leg_role == KeywordLegRole.AMBIGUOUS
            if ambiguous_leg:
                reason_codes.add(KeywordReasonCode.AMBIGUOUS_LEG.value)

            owners = global_overlap.get(adv_id, [])
            shops = {shop for shop, _ in owners}
            ambiguous_ownership = False
            foreign_shop = False

            if len(owners) > 1:
                ambiguous_ownership = True
                reason_codes.add(KeywordReasonCode.AMBIGUOUS_OWNERSHIP.value)
            if shops and requested_shop not in shops:
                foreign_shop = True
                reason_codes.add(KeywordReasonCode.FOREIGN_SHOP_ADV_ID.value)
            elif len(shops) > 1:
                foreign_shop = True
                reason_codes.add(KeywordReasonCode.FOREIGN_SHOP_ADV_ID.value)

            assignments.append(
                AdvIdAssignment(
                    adv_id=adv_id,
                    shop_id=row.shop_id,
                    adv_setting_id=row.adv_setting_id,
                    leg_role=leg_role.value,
                    ambiguous_leg=ambiguous_leg,
                    ambiguous_ownership=ambiguous_ownership or foreign_shop,
                    foreign_shop=foreign_shop,
                )
            )

    return tuple(assignments), frozenset(reason_codes)


def collect_keyword_export_scope(
    rows: Sequence[KeywordScopeRow],
    global_overlap: Mapping[int, list[tuple[str, int]]],
    *,
    rebound_unavailable: bool = False,
) -> KeywordExportScope:
    """Assemble export scope with deduped adv_ids and ownership flags."""
    assignments, reason_codes = build_assignments(rows, global_overlap)
    rc = set(reason_codes)
    if rebound_unavailable:
        rc.add(KeywordReasonCode.REBOUND_IDS_UNAVAILABLE.value)

    all_adv: set[int] = set()
    all_nmids: set[int] = set()
    for row in rows:
        all_adv.update(row.all_adv_ids)
        all_nmids.update(row.proven_nmids)

    return KeywordExportScope(
        rows=tuple(rows),
        assignments=assignments,
        all_adv_ids=frozenset(all_adv),
        all_nmids=frozenset(all_nmids),
        reason_codes=frozenset(rc),
        rebound_unavailable=rebound_unavailable,
    )


def assignment_for_adv_id(
    scope: KeywordExportScope,
    adv_id: int,
) -> AdvIdAssignment | None:
    """First assignment for adv_id (fail-closed if ambiguous ownership)."""
    for item in scope.assignments:
        if item.adv_id == adv_id:
            return item
    return None
