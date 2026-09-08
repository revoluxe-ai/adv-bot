"""Unit tests for the bounded A1 write-set selectors."""

from scripts.a1_controlled_ad_expansion_v1 import (
    Candidate,
    _candidate_rows,
    classify_bottleneck,
    choose_contour,
    validate_allowlist,
    validate_incremental_spend,
)


def test_allowlist_rejects_forbidden_nmid() -> None:
    """Запрещённый nmID не должен попасть в mutation envelope."""
    try:
        validate_allowlist([7974113])
    except ValueError as exc:
        assert "FORBIDDEN_NMIDS" in str(exc)
    else:
        raise AssertionError("forbidden nmID was accepted")


def test_incremental_spend_is_bounded() -> None:
    """Суммарный top-up не превышает hard max 2000 RUB/day."""
    assert validate_incremental_spend([1000, 1000]) == 2000
    try:
        validate_incremental_spend([1500, 501])
    except ValueError as exc:
        assert "OVER_MAX" in str(exc)
    else:
        raise AssertionError("over-limit spend was accepted")


def test_contour_pick_prefers_priority_paused_leg() -> None:
    """Приоритетный paused leg выбирается раньше secondary candidate."""
    selected = choose_contour(
        [
            Candidate(20, (388166103,), 11, 100, "activate_paused_leg", 388166103),
            Candidate(10, (14824677,), 11, 100, "activate_paused_leg", 14824677),
        ]
    )
    assert selected is not None
    assert selected.nm_id == 14824677


def test_preflight_classifies_paused_search_before_budget() -> None:
    """Свежий paused Search leg выбирается минимальным рычагом."""
    rows = _candidate_rows(
        [{
            "id": 39943926,
            "status": 11,
            "name": "Search A1",
            "nm_settings": [{"nmID": 14824677}],
        }],
        {39943926: 1200},
        {14824677: (1000.0, 3000.0)},
    )
    assert rows[0].classification == "PAUSED_LEG_AVAILABLE"
    assert rows[0].action == "activate_paused_leg"


def test_budget_topup_is_not_selected_for_forbidden_nmids() -> None:
    """Наблюдаемые forbidden nmID не проходят в mutation candidate set."""
    rows = _candidate_rows(
        [{
            "id": 99,
            "status": 9,
            "name": "Auto",
            "nm_settings": [{"nmID": 7974113}],
        }],
        {99: 0},
        {7974113: (100.0, 500.0)},
    )
    assert rows == []
    assert classify_bottleneck(
        status=9, budget=700, daily_limit=500, has_paused_leg=False,
        max_cpo=1200, sales_7d=1000,
    ) == "BUDGET_LIMITED"
