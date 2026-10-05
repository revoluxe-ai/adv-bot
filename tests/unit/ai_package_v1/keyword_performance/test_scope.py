"""Scope expansion, rebound, ownership, leg separation (S05,S06,S08,S26,S40,S46)."""

from __future__ import annotations

import pytest

from app.modules.ai_package_v1.keyword_performance.domain.enums import KeywordLegRole
from app.modules.ai_package_v1.keyword_performance.scope.adv_id_collector import (
    assign_leg_roles,
    collect_keyword_export_scope,
)
from tests.unit.ai_package_v1.keyword_performance.conftest import make_scope_row

pytestmark = pytest.mark.unit


def test_rebound_adv_id_in_scope() -> None:
    row = make_scope_row(rebound_auto=frozenset({999}))
    roles = assign_leg_roles(row)
    assert 999 in roles
    assert roles[999] == KeywordLegRole.REBOUND_AUTO


def test_auto_search_legs_separate() -> None:
    row = make_scope_row(auto_adv_id=111, search_adv_id=222)
    roles = assign_leg_roles(row)
    assert roles[111] == KeywordLegRole.AUTO
    assert roles[222] == KeywordLegRole.SEARCH


def test_same_query_two_legs_two_adv_ids() -> None:
    row = make_scope_row()
    assert 111 in row.all_adv_ids
    assert 222 in row.all_adv_ids
    assert row.auto_adv_id != row.search_adv_id


def test_rebound_ownership_ambiguous_foreign_shop() -> None:
    row = make_scope_row(rebound_auto=frozenset({888}))
    overlap = {888: [("1", 101), ("999", 202)]}
    scope = collect_keyword_export_scope([row], overlap)
    assert "AMBIGUOUS_OWNERSHIP" in scope.reason_codes or "FOREIGN_SHOP_ADV_ID" in scope.reason_codes


def test_no_rebind_timeline_fields() -> None:
    row = make_scope_row(rebound_auto=frozenset({999}))
    assert not hasattr(row, "rebind_transition_date")
