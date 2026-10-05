"""Daily facts: grain, spend, snapshot conflict, missing vs zero (S02,S07,S09,S18,S25,S41,S43,S44)."""

from __future__ import annotations

import pytest

from app.modules.ai_package_v1.keyword_performance.domain.enums import (
    QuerySpendStatus,
    RawQueryStatus,
    SnapshotStatus,
)
from app.modules.ai_package_v1.keyword_performance.domain.spend_mapper import map_spend
from app.modules.ai_package_v1.keyword_performance.export.daily_assembler import (
    assemble_daily_rows,
)
from app.modules.ai_package_v1.keyword_performance.scope.adv_id_collector import (
    collect_keyword_export_scope,
)
from tests.unit.ai_package_v1.keyword_performance.conftest import (
    MANIFEST_SHOP_ID,
    make_daily_raw,
    make_scope_row,
)

pytestmark = pytest.mark.unit


def _scope():
    row = make_scope_row()
    overlap = {111: [("1", 101)], 222: [("1", 101)]}
    return collect_keyword_export_scope([row], overlap)


def test_rebound_row_retains_adv_id() -> None:
    raw = make_daily_raw(adv_id=999)
    scope = collect_keyword_export_scope(
        [make_scope_row(rebound_auto=frozenset({999}))],
        {999: [("1", 101)]},
    )
    rows = assemble_daily_rows([raw], manifest_shop_id=MANIFEST_SHOP_ID, scope=scope)
    assert rows[0].adv_id == 999


def test_null_spend_unavailable() -> None:
    spend, status = map_spend(None)
    assert spend is None
    assert status == QuerySpendStatus.UNAVAILABLE


def test_factual_spend_status() -> None:
    spend, status = map_spend(12.5)
    assert spend == 12.5
    assert status == QuerySpendStatus.FACTUAL


def test_missing_day_not_zero() -> None:
    raw = make_daily_raw(views=None, clicks=None, spend=None)
    rows = assemble_daily_rows([raw], manifest_shop_id=MANIFEST_SHOP_ID, scope=_scope())
    assert rows[0].views is None
    assert rows[0].clicks is None


def test_snapshot_conflict_ambiguous() -> None:
    raw = make_daily_raw(variants=2)
    rows = assemble_daily_rows([raw], manifest_shop_id=MANIFEST_SHOP_ID, scope=_scope())
    assert rows[0].snapshot_status == SnapshotStatus.AMBIGUOUS
    assert rows[0].views is None


def test_snapshot_identical_collapse() -> None:
    raw = make_daily_raw(variants=1)
    rows = assemble_daily_rows([raw], manifest_shop_id=MANIFEST_SHOP_ID, scope=_scope())
    assert rows[0].snapshot_status == SnapshotStatus.OK
    assert rows[0].views == 100


def test_raw_query_unavailable() -> None:
    raw = make_daily_raw()
    rows = assemble_daily_rows([raw], manifest_shop_id=MANIFEST_SHOP_ID, scope=_scope())
    assert rows[0].raw_query is None
    assert rows[0].raw_query_status == RawQueryStatus.RAW_QUERY_UNAVAILABLE
    assert rows[0].norm_query == "query"


def test_missing_position_null() -> None:
    raw = make_daily_raw(avr_pos=None)
    rows = assemble_daily_rows([raw], manifest_shop_id=MANIFEST_SHOP_ID, scope=_scope())
    assert rows[0].cluster_avg_pos is None
