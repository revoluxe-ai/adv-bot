"""Unit: orchestrator — gaps, ceiling, mutation refuse."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.ceiling import RunCeiling
from scripts.wb_api_readonly_ops.models import (
    FamilyName,
    FamilyResult,
    FamilyStatus,
    Mode,
    OverallStatus,
)
from scripts.wb_api_readonly_ops.mutation_guard import (
    MutationWriteRefused,
    assert_read_only_op,
)
from scripts.wb_api_readonly_ops.orchestrator import run_ops


@pytest.mark.asyncio
async def test_unmapped_family_records_gap() -> None:
    """Нет runner → GAP, без invented URL/call."""

    async def ads_ok(mode: Mode, ctx: dict) -> FamilyResult:
        return FamilyResult(family=FamilyName.ADS, status=FamilyStatus.OK)

    report = await run_ops(
        shop_id="s1",
        mode=Mode.PREFLIGHT,
        runners={FamilyName.ADS: ads_ok},
        ceiling=RunCeiling(max_seconds=30, max_calls=10),
    )
    by_name = {f.family: f for f in report.families}
    assert by_name[FamilyName.ADS].status == FamilyStatus.OK
    assert by_name[FamilyName.CARDS].status == FamilyStatus.GAP
    assert "no runner mapped" in by_name[FamilyName.CARDS].gaps[0]
    assert report.overall_status == OverallStatus.PARTIAL
    assert report.web_pass_claimed is False
    assert report.to_dict()["web_pass_claimed"] is False


@pytest.mark.asyncio
async def test_ceiling_exhausted_stops_without_infinite_retry() -> None:
    """Исчерпание call budget → FAILED/GAP, без бесконечного цикла."""
    calls = {"n": 0}

    async def counting(mode: Mode, ctx: dict) -> FamilyResult:
        calls["n"] += 1
        return FamilyResult(family=FamilyName.ADS, status=FamilyStatus.OK)

    # max_calls=1 → first family consumes; rest skipped after second consume fails
    # Actually: first consume succeeds for ads; if only ads runner and we use
    # max_calls=1, first family OK; second family consume fails.
    report = await run_ops(
        shop_id="s1",
        mode=Mode.COLLECT,
        runners={
            FamilyName.ADS: counting,
            FamilyName.CARDS: counting,
            FamilyName.ANALYTICS: counting,
            FamilyName.NORMS: counting,
        },
        ceiling=RunCeiling(max_seconds=60, max_calls=1),
    )
    assert calls["n"] == 1
    assert report.ceiling_exhausted is True
    assert report.overall_status != OverallStatus.OK
    assert any("ceiling" in g for f in report.families for g in f.gaps)


def test_mutation_write_refused() -> None:
    """Denylist mutation ops → MutationWriteRefused."""
    assert_read_only_op("get_cards_list")  # allowed (not in denylist)
    assert_read_only_op("get_supplier_orders")  # ORDERS read allowed
    with pytest.raises(MutationWriteRefused):
        assert_read_only_op("start_campaign")
    with pytest.raises(MutationWriteRefused):
        assert_read_only_op("top_up_budget")
    with pytest.raises(MutationWriteRefused):
        assert_read_only_op("create_payout")
