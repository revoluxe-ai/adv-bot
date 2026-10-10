"""Stub-contract: leg-CPO CH unit stubs ↔ golden seed/CH boundary ContractCase."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.wb_stat_manager.leg_cpo import (
    build_leg_cpo_snapshot,
    load_leg_cpo_snapshot,
    load_leg_cpo_snapshots,
)
from tests.support.leg_cpo_ch_contract import (
    CONTRACT_ID,
    GET_STATS_REQUIRED_POSITIONAL,
    GOLDEN_PAIR_CASE,
    LEG_CPO_CH_CONTRACT_CASES,
    LOAD_SNAPSHOT_REQUIRED_KWONLY,
    RecordingGetStatsByAdvIds,
    RecordingLegCpoSnapshotLoader,
    RecordingLegCpoSnapshotsLoader,
    assert_get_stats_request_matches_case,
    assert_load_snapshot_kwargs_match_case,
    assert_snapshot_matches_case,
    golden_leg_cpo_snapshot,
    golden_stats_by_adv_id,
)
from tests.support.leg_cpo_ch_seed import (
    LEG_CPO_AUTO_ADV_ID,
    LEG_CPO_FIXED_DAYS,
    LEG_CPO_FIXED_NOW,
    LEG_CPO_SEARCH_ADV_ID,
    resolve_leg_cpo_window,
)

pytestmark = pytest.mark.unit


def test_leg_cpo_ch_contract_registry_matches_seed_constants() -> None:
    """Shared ContractCase ids и seed economics зафиксированы в одном registry."""
    assert CONTRACT_ID == "leg-cpo-ch-boundary-v1"
    case = GOLDEN_PAIR_CASE
    assert case.auto_adv_id == LEG_CPO_AUTO_ADV_ID
    assert case.search_adv_id == LEG_CPO_SEARCH_ADV_ID
    assert case.now == LEG_CPO_FIXED_NOW
    assert case.days == LEG_CPO_FIXED_DAYS
    assert {c.case_id for c in LEG_CPO_CH_CONTRACT_CASES} == {
        "paired_auto_search_seed_window"
    }


def test_golden_stats_build_snapshot_matches_ch_boundary_expectations() -> None:
    """Pure calculator на golden stats == ожидания integration CH boundary tests."""
    case = GOLDEN_PAIR_CASE
    start_date, end_date = resolve_leg_cpo_window(
        now=LEG_CPO_FIXED_NOW, days=LEG_CPO_FIXED_DAYS
    )
    snapshot = build_leg_cpo_snapshot(
        auto_adv_id=case.auto_adv_id,
        search_adv_id=case.search_adv_id,
        stats_by_adv_id=golden_stats_by_adv_id(case),
        start_date=start_date,
        end_date=end_date,
    )
    assert_snapshot_matches_case(snapshot, case)
    assert snapshot.auto_cpo == pytest.approx(600.0 / 2)
    assert snapshot.search_cpo == pytest.approx(300.0 / 3)


@pytest.mark.asyncio
async def test_recording_get_stats_fake_matches_golden_request_return() -> None:
    """Scenario stub ``get_stats_by_adv_ids_last_days`` parity с ContractCase."""
    case = GOLDEN_PAIR_CASE
    fake = RecordingGetStatsByAdvIds(case=case)
    adv_ids, start_date, end_date = case.get_stats_request()
    result = await fake(adv_ids, start_date, end_date)
    fake.assert_matches_case(case)
    assert set(result) == {case.auto_adv_id, case.search_adv_id}
    assert result[case.auto_adv_id].orders == case.auto_orders
    assert result[case.search_adv_id].orders == case.search_orders


@pytest.mark.asyncio
async def test_recording_load_snapshot_fake_matches_golden_kwargs_return() -> None:
    """Scenario stub ``load_leg_cpo_snapshot`` parity с ContractCase."""
    fake = RecordingLegCpoSnapshotLoader()
    snapshot = await fake.load_leg_cpo_snapshot(**GOLDEN_PAIR_CASE.load_snapshot_kwargs())
    fake.assert_matches_case()
    assert_snapshot_matches_case(snapshot)


@pytest.mark.asyncio
async def test_recording_load_snapshots_batch_fake_matches_golden_map() -> None:
    """Scenario stub ``load_leg_cpo_snapshots`` возвращает golden map keyed by auto adv_id."""
    case = GOLDEN_PAIR_CASE
    adv_setting = MagicMock()
    adv_setting.adv_id = case.auto_adv_id
    adv_setting.search_adv_id = case.search_adv_id
    complex_adv = ComplexAdv(adv_setting=adv_setting)
    fake = RecordingLegCpoSnapshotsLoader(case=case)
    snapshots = await fake.load_leg_cpo_snapshots(
        complex_advs=[complex_adv],
        now=case.now,
        days=case.days,
    )
    fake.assert_matches_case(case)
    assert snapshots[case.auto_adv_id].search_cpo == case.expected_search_cpo


def test_production_loader_signatures_match_contract_thin_ends() -> None:
    """Boundary adapter: production CH loader signatures стабильны для stub parity."""
    stats_sig = inspect.signature(
        __import__(
            "app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat",
            fromlist=["get_stats_by_adv_ids_last_days"],
        ).get_stats_by_adv_ids_last_days
    )
    stats_params = [
        p
        for p in stats_sig.parameters
        if p not in ("self",) and stats_sig.parameters[p].kind.name != "VAR_KEYWORD"
    ]
    assert stats_params == list(GET_STATS_REQUIRED_POSITIONAL)

    snapshot_sig = inspect.signature(load_leg_cpo_snapshot)
    snapshot_kwonly = {
        name
        for name, param in snapshot_sig.parameters.items()
        if param.kind.name == "KEYWORD_ONLY"
    }
    assert LOAD_SNAPSHOT_REQUIRED_KWONLY <= snapshot_kwonly

    batch_sig = inspect.signature(load_leg_cpo_snapshots)
    batch_params = [
        name
        for name, param in batch_sig.parameters.items()
        if name != "self"
    ]
    assert batch_params[0] == "complex_advs"


@pytest.mark.asyncio
async def test_async_mock_stub_can_reuse_golden_contract_return() -> None:
    """Unit AsyncMock stub может вернуть тот же golden snapshot без ad-hoc чисел."""
    case = GOLDEN_PAIR_CASE
    stub = AsyncMock(return_value=golden_leg_cpo_snapshot(case))
    snapshot = await stub(**case.load_snapshot_kwargs())
    stub.assert_awaited_once()
    call = stub.await_args
    assert call is not None
    assert_load_snapshot_kwargs_match_case(call.kwargs, case)
    assert_snapshot_matches_case(snapshot, case)
