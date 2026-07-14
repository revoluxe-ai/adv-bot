"""Unit-тесты A/B Hold minus freeze (spec card-ab-hold-mode §8 / decision §8).

Покрывает: snapshot normalize/drift, skip ordinary recalc, ready-only-ACTIVE,
restore-on-drift, wiring manager + setup pipeline ordering.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.enter_status import (
    build_enter_poll_status_lines,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    capture_minus_snapshot,
    empty_minus_snapshot,
    is_ab_hold_ready_for_tests,
    minus_phrases_drift,
    normalize_minus_snapshot,
    restore_minus_snapshot_if_drift,
    should_skip_ordinary_minus_recalculation,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    filter_structural_act_candidates,
)


@pytest.mark.unit
def test_minus_snapshot_normalize_and_drift() -> None:
    """8.1: snapshot normalize + drift detect (failing before equals)."""
    raw = [
        {"adv_id": 1, "nmid": 10, "phrases": ["b", "a", "a"]},
        {"bad": True},
    ]
    snap = normalize_minus_snapshot(raw)
    assert snap == [{"adv_id": 1, "nmid": 10, "phrases": ["a", "b"]}]
    assert empty_minus_snapshot() == []
    assert minus_phrases_drift(["a", "b"], ["b", "a"]) is False
    assert minus_phrases_drift(["a"], ["a", "x"]) is True


@pytest.mark.unit
def test_ordinary_minus_recalc_skipped_on_freeze_modes() -> None:
    """8.2: PENDING/ACTIVE → ordinary recalc skip; OFF → allowed."""
    assert should_skip_ordinary_minus_recalculation(CardAbHoldMode.PENDING_SETUP)
    assert should_skip_ordinary_minus_recalculation(CardAbHoldMode.ACTIVE)
    assert not should_skip_ordinary_minus_recalculation(CardAbHoldMode.OFF)
    pool = [
        SimpleNamespace(adv_id=1, card_ab_hold_mode="active"),
        SimpleNamespace(adv_id=2, card_ab_hold_mode="off"),
        SimpleNamespace(adv_id=3, card_ab_hold_mode="pending_setup"),
    ]
    assert [a.adv_id for a in filter_structural_act_candidates(pool)] == [2]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_minus_snapshot_on_drift_writes_expected() -> None:
    """8.2: drift → set_minus со snapshot; без drift — без write."""
    calls: list[tuple[int, int, list[str]]] = []

    async def get_minus(adv_id: int, nmid: int) -> list[str]:
        _ = adv_id
        assert nmid == 77
        return ["dirty"]

    async def set_minus(adv_id: int, nmid: int, phrases: list[str]) -> None:
        calls.append((adv_id, nmid, phrases))

    snap = [{"adv_id": 5, "nmid": 77, "phrases": ["clean", "set"]}]
    n = await restore_minus_snapshot_if_drift(
        SimpleNamespace(),
        snapshot=snap,
        get_minus=get_minus,
        set_minus=set_minus,
    )
    assert n == 1
    assert calls == [(5, 77, ["clean", "set"])]

    calls.clear()
    n2 = await restore_minus_snapshot_if_drift(
        SimpleNamespace(),
        snapshot=[{"adv_id": 5, "nmid": 77, "phrases": ["dirty"]}],
        get_minus=get_minus,
        set_minus=set_minus,
    )
    assert n2 == 0
    assert calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_capture_minus_snapshot_reads_wb_targets() -> None:
    """8.1: capture собирает phrases per (adv_id, nmid) с WB get."""
    adv_setting = SimpleNamespace(
        nmids=[101],
        wb_bid_type=None,
        wb_placement_search=None,
        wb_placement_recommendations=None,
    )
    complex_adv = SimpleNamespace(
        auto_adv_id=9,
        adv_setting=adv_setting,
        search_adv=None,
    )

    async def get_minus(adv_id: int, nmid: int) -> list[str]:
        assert (adv_id, nmid) == (9, 101)
        return ["z", "a"]

    # Force not shelf-only: leave meta unknown → not wb_is_manual_shelf_only
    snap = await capture_minus_snapshot(complex_adv, get_minus=get_minus)
    assert snap == [{"adv_id": 9, "nmid": 101, "phrases": ["a", "z"]}]


@pytest.mark.unit
def test_ui_ready_for_ab_tests_only_when_active() -> None:
    """8.3: ready-to-test только ACTIVE; PENDING не ready."""
    assert is_ab_hold_ready_for_tests(CardAbHoldMode.ACTIVE) is True
    assert is_ab_hold_ready_for_tests(CardAbHoldMode.PENDING_SETUP) is False
    assert is_ab_hold_ready_for_tests(CardAbHoldMode.OFF) is False

    pending = build_enter_poll_status_lines(
        mode="pending_setup",
        abort_safe=True,
        abort_can_continue=True,
    )
    assert "можно запускать A/B" not in pending.lower()
    assert "ACTIVE" not in pending or "не ACTIVE" in pending
    assert "не запускайте A/B" in pending

    active = build_enter_poll_status_lines(
        mode="active",
        abort_safe=None,
        abort_can_continue=None,
    )
    assert "Можно запускать A/B-тесты" in active
    assert "зафиксированы" in active


@pytest.mark.unit
def test_manager_wires_minus_structural_filter() -> None:
    """8.2/8.6 wiring: update_minus_phrases_in_advs фильтрует freeze modes."""
    import inspect

    from app.modules.shop_runner.service_manager.manager import CoroutinesManager

    src = inspect.getsource(CoroutinesManager.update_minus_phrases_in_advs)
    assert "filter_structural_act_candidates" in src


@pytest.mark.unit
def test_setup_pipeline_orders_minus_sync_before_active() -> None:
    """8.1/8.5 wiring: process_ab_setup sync→capture→mutations со snapshot."""
    import inspect

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
        pipelines,
    )

    src = inspect.getsource(pipelines.process_ab_setup)
    assert "force_ab_hold_setup_sync" in src
    assert "capture_minus_snapshot" in src
    assert "minus_phrases_snapshot" in src
    assert src.index("force_ab_hold_setup_sync") < src.index("capture_minus_snapshot")
    assert src.index("capture_minus_snapshot") < src.index("apply_ab_hold_setup_mutations")


@pytest.mark.unit
def test_hold_pipeline_restores_minus_on_drift() -> None:
    """8.2/8.6 wiring: process_ab_hold вызывает restore_minus_snapshot_if_drift."""
    import inspect

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
        pipelines,
    )

    src = inspect.getsource(pipelines.process_ab_hold)
    assert "restore_minus_snapshot_if_drift" in src


@pytest.mark.unit
def test_disable_clears_minus_snapshot() -> None:
    """8.3/8.7 wiring: EXIT очищает card_ab_hold_minus_phrases_snapshot."""
    import inspect

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )

    src = inspect.getsource(handlers.disable_card_ab_hold)
    assert "empty_minus_snapshot" in src
    assert "card_ab_hold_minus_phrases_snapshot" in src


@pytest.mark.unit
def test_instruction_mentions_minus_freeze() -> None:
    """8.8: инструкция про фиксацию минус-фраз и отключение Hold."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )

    text = handlers._INSTRUCTION
    assert "минус-фразы фиксируются" in text
    assert "отключите A/B Hold" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_minus_manager_skips_ordinary_recalc_on_active() -> None:
    """8.2: MinusPhraseManager.update_minus_phrases no-op при ACTIVE без force."""
    from app.modules.shop_runner.service_manager.services.minus_phrase_manager.minus_phrase_manager import (
        MinusPhraseManager,
    )

    mgr = MinusPhraseManager(
        wb_api_manager_hub=AsyncMock(),
        click_house_manager=AsyncMock(),
        update_redis_timestamp_manager=AsyncMock(),
    )
    mgr._update_minus_phrases = AsyncMock()  # type: ignore[method-assign]
    adv = SimpleNamespace(
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        shop_id=1,
        adv_id=2,
    )
    skipped = await mgr.update_minus_phrases(adv)  # type: ignore[arg-type]
    assert skipped is False
    mgr._update_minus_phrases.assert_not_called()

    forced = await mgr.update_minus_phrases(
        adv, force_ab_hold_setup_sync=True
    )  # type: ignore[arg-type]
    assert forced is True
    mgr._update_minus_phrases.assert_awaited_once()
