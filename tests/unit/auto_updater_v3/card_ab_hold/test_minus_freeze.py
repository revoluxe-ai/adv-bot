"""Unit-тесты A/B Hold allowed-set freeze + enforcement (spec card-ab-hold-mode §8).

Primary invariant: замораживается разрешённый (allowed/relevant) набор фраз;
минус — производный enforcement. Покрывает: capture allowed-set, normalize,
skip ordinary recalc, ready-only-ACTIVE, hold enforcement (новая не-разрешённая
фраза исключается / снятая разрешённая восстанавливается), WB cap видимая
деградация, wiring setup/hold/EXIT, инструкция.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.enter_status import (
    build_enter_poll_status_lines,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    WB_MINUS_CAP,
    capture_allowed_phrase_set,
    compute_enforced_minus,
    empty_allowed_snapshot,
    enforce_allowed_set,
    is_ab_hold_ready_for_tests,
    normalize_allowed_snapshot,
    should_skip_ordinary_minus_recalculation,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    filter_structural_act_candidates,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)


def _complex_adv(*, nmid: int = 101, auto_adv_id: int = 9) -> SimpleNamespace:
    """РК с одной auto-целью (meta unknown → не shelf-only, search=None)."""
    adv_setting = SimpleNamespace(
        nmids=[nmid],
        wb_bid_type=None,
        wb_placement_search=None,
        wb_placement_recommendations=None,
    )
    return SimpleNamespace(
        auto_adv_id=auto_adv_id,
        adv_setting=adv_setting,
        search_adv=None,
    )


async def _run_enforce(
    *,
    allowed: object,
    observed: list[str],
    current: list[str],
) -> tuple[dict[str, object], list[tuple[int, int, list[str]]]]:
    """Прогнать enforce_allowed_set для одной (9,101) цели с заданными данными."""
    calls: list[tuple[int, int, list[str]]] = []

    async def get_minus(adv_id: int, nmid: int) -> list[str]:
        _ = (adv_id, nmid)
        return list(current)

    async def get_observed(adv_id: int, nmid: int) -> list[str]:
        _ = (adv_id, nmid)
        return list(observed)

    async def set_minus(adv_id: int, nmid: int, phrases: list[str]) -> None:
        calls.append((adv_id, nmid, phrases))

    res = await enforce_allowed_set(
        _complex_adv(),
        allowed=allowed,
        get_minus=get_minus,
        set_minus=set_minus,
        get_observed=get_observed,
    )
    return dict(res), calls


@pytest.mark.unit
def test_capture_allowed_phrase_set_keeps_non_bad_texts() -> None:
    """8.1/8.5: allowed-set = тексты ключей status != BAD (BAD исключается)."""
    keywords = [
        SimpleNamespace(status=KeywordStatus.GOOD, text="good b"),
        SimpleNamespace(status=KeywordStatus.GOOD, text="good a"),
        SimpleNamespace(status=KeywordStatus.BAD, text="bad kw"),
        SimpleNamespace(status=KeywordStatus.VIEWS_IS_NOT_ENOUGH, text="warmup"),
        SimpleNamespace(status=KeywordStatus.GOOD, text=""),
    ]
    assert capture_allowed_phrase_set(keywords) == ["good a", "good b", "warmup"]


@pytest.mark.unit
def test_normalize_and_empty_allowed_snapshot() -> None:
    """8.1: normalize → sorted unique strings; empty → []."""
    assert normalize_allowed_snapshot(["b", "a", "a", "", None]) == ["a", "b"]
    assert normalize_allowed_snapshot("not-a-list") == []
    assert normalize_allowed_snapshot(None) == []
    assert empty_allowed_snapshot() == []


@pytest.mark.unit
def test_compute_enforced_minus_cap_and_diff() -> None:
    """8.6/8.7: минус = наблюдаемые вне allowed; cap отсекает + флаг."""
    minus, exceeded = compute_enforced_minus(["a", "b", "c"], ["a"])
    assert minus == ["b", "c"]
    assert exceeded is False

    observed = [f"kw{i}" for i in range(WB_MINUS_CAP + 5)]
    capped, exceeded2 = compute_enforced_minus(observed, [])
    assert len(capped) == WB_MINUS_CAP
    assert exceeded2 is True


@pytest.mark.unit
def test_ordinary_minus_recalc_skipped_on_freeze_modes() -> None:
    """8.2: PENDING/ACTIVE → ordinary allowed-set recalc skip; OFF → allowed."""
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
async def test_enforce_excludes_new_non_allowed_phrase() -> None:
    """8.2/8.6/8.10: новая не-разрешённая фраза во время hold → исключается."""
    res, calls = await _run_enforce(
        allowed=["good1", "good2"],
        observed=["good1", "new_non_allowed"],
        current=[],
    )
    assert calls == [(9, 101, ["new_non_allowed"])]
    assert res["written"] == 1
    assert res["cap_exceeded"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enforce_restores_manually_removed_allowed_phrase() -> None:
    """8.2/8.6: разрешённая фраза, заминусованная вручную → восстанавливается."""
    res, calls = await _run_enforce(
        allowed=["good1"],
        observed=["good1"],
        current=["good1"],
    )
    # good1 разрешена → её нет в целевом минусе → set_minus снимает её.
    assert calls == [(9, 101, [])]
    assert res["written"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enforce_no_write_when_surface_already_clean() -> None:
    """8.6: если минус уже равен «всё вне allowed» — без write."""
    res, calls = await _run_enforce(
        allowed=["good1"],
        observed=["good1", "bad1"],
        current=["bad1"],
    )
    assert calls == []
    assert res["written"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enforce_cap_exceeded_degrades_visibly() -> None:
    """8.7/8.10: > WB cap не-разрешённых → cap_exceeded (видимая деградация)."""
    observed = [f"kw{i}" for i in range(WB_MINUS_CAP + 10)]
    res, calls = await _run_enforce(allowed=[], observed=observed, current=[])
    assert res["cap_exceeded"] == [(9, 101)]
    assert len(calls) == 1
    _, _, phrases = calls[0]
    assert len(phrases) == WB_MINUS_CAP


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
    assert "не запускайте A/B" in pending
    assert "набор фраз ещё не зафиксирован" in pending

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
def test_setup_pipeline_orders_capture_enforce_before_active() -> None:
    """8.1/8.5 wiring: process_ab_setup capture→enforce→mutations со snapshot."""
    import inspect

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
        pipelines,
    )

    src = inspect.getsource(pipelines.process_ab_setup)
    assert "capture_allowed_phrase_set" in src
    assert "enforce_frozen_allowed_set" in src
    assert "allowed_phrases_snapshot" in src
    assert src.index("capture_allowed_phrase_set") < src.index("enforce_frozen_allowed_set")
    assert src.index("enforce_frozen_allowed_set") < src.index("apply_ab_hold_setup_mutations")


@pytest.mark.unit
def test_hold_pipeline_enforces_allowed_set() -> None:
    """8.2/8.6 wiring: process_ab_hold вызывает enforce_frozen_allowed_set."""
    import inspect

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
        pipelines,
    )

    src = inspect.getsource(pipelines.process_ab_hold)
    assert "enforce_frozen_allowed_set" in src
    assert "cap_exceeded" in src


@pytest.mark.unit
def test_disable_clears_allowed_snapshot() -> None:
    """8.3/8.8 wiring: EXIT очищает card_ab_hold_allowed_phrases_snapshot."""
    import inspect

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )

    src = inspect.getsource(handlers.disable_card_ab_hold)
    assert "empty_allowed_snapshot" in src
    assert "card_ab_hold_allowed_phrases_snapshot" in src


@pytest.mark.unit
def test_instruction_mentions_allowed_set_and_scope() -> None:
    """8.9: инструкция про фиксацию набора фраз + scoped/best-effort wording."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )

    text = handlers._INSTRUCTION
    assert "набор" in text and "фраз" in text
    assert "отключите A/B Hold" in text
    assert "не гарантируется" in text
