"""DATA_MAP semantics (S13,S24,S32,S44)."""

from __future__ import annotations

import pytest

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.data_map_builder import (
    build_data_map,
)
from tests.unit.ai_package_v1.keyword_performance.conftest import GENERATED_AT

pytestmark = pytest.mark.unit


def test_datamap_position_delta_convention() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT)
    dm = build_data_map(
        cutoff=cutoff,
        daily_first=None,
        daily_last=None,
        position_first=None,
        position_last=None,
        export_period_note="test",
    )
    assert dm["position_direction"] == "lower_is_better"
    assert "negative = improvement" in dm["position_delta_convention"]


def test_datamap_grain_keys() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT)
    dm = build_data_map(
        cutoff=cutoff,
        daily_first=None,
        daily_last=None,
        position_first=None,
        position_last=None,
        export_period_note="test",
    )
    daily = dm["datasets"]["keyword_daily"]
    assert "adv_id" in daily["primary_key"]
    assert "leg_role" in daily["primary_key"]
    assert "norm_query" in daily["primary_key"]
    leg_pk = [
        row
        for row in dm["export_field_matrix"]
        if row["dataset"] == "keyword_daily" and row["field"] == "leg_role"
    ]
    assert leg_pk and leg_pk[0].get("primary_key") is True


def test_datamap_comparable_formulas() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT)
    dm = build_data_map(
        cutoff=cutoff,
        daily_first=None,
        daily_last=None,
        position_first=None,
        position_last=None,
        export_period_note="test",
    )
    formulas = dm["comparable_window_formulas"]
    assert "mtd_vs_prev_mtd" in formulas
    assert "calendar_previous_month_quarter_year" in formulas


def test_datamap_source_field_matrix() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT)
    dm = build_data_map(
        cutoff=cutoff,
        daily_first=None,
        daily_last=None,
        position_first=None,
        position_last=None,
        export_period_note="test",
    )
    export_matrix = dm["export_field_matrix"]
    fields = {entry["field"] for entry in export_matrix}
    assert "decision_cpm_curr" in fields
    assert "current_bid_evidence" in fields
    assert "final_bid" in fields
    assert dm["source_field_matrix"]


def test_datamap_export_field_matrix_complete() -> None:
    """Every exported pydantic field has registry metadata with source+formula."""
    from app.modules.ai_package_v1.keyword_performance.domain.export_field_registry import (
        build_export_field_matrix,
        validate_registry_completeness,
    )

    gaps = validate_registry_completeness()
    assert gaps == [], f"registry gaps: {gaps}"
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT)
    dm = build_data_map(
        cutoff=cutoff,
        daily_first=None,
        daily_last=None,
        position_first=None,
        position_last=None,
        export_period_note="test",
    )
    matrix = dm["export_field_matrix"]
    assert len(matrix) == len(build_export_field_matrix())
    datasets = {row["dataset"] for row in matrix}
    assert "keyword_decisions" in datasets
    assert "keyword_position_windows" in datasets
    for row in matrix:
        assert row.get("source"), row["field"]
        assert row.get("formula"), row["field"]
        assert row.get("grain"), row["field"]
        assert "nullable" in row
        assert row.get("coverage_when_absent") is not None


def test_datamap_dual_bounds() -> None:
    cutoff = PackageCutoff.from_generated_at(GENERATED_AT)
    dm = build_data_map(
        cutoff=cutoff,
        daily_first=None,
        daily_last=None,
        position_first=None,
        position_last=None,
        export_period_note="manifest.period separate from keyword_history_bounds",
    )
    assert "keyword_history_bounds" in dm
    assert "export_period_vs_keyword_history" in dm
