"""Unit tests for the bounded A1 write-set selectors."""

from scripts.a1_controlled_ad_expansion_v1 import (
    Candidate,
    _candidate_rows,
    _next_observation_day,
    classify_bottleneck,
    choose_contour,
    choose_contours,
    rank_mats_candidates,
    validate_allowlist,
    validate_incremental_spend,
)
from datetime import date


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
    """Совместимый single-result helper сохраняет порядок приоритетов."""
    selected = choose_contour(
        [
            Candidate(20, (388166103,), 11, 100, "activate_paused_leg", 388166103),
            Candidate(10, (837395782,), 11, 100, "activate_paused_leg", 837395782),
        ]
    )
    assert selected is not None
    assert selected.nm_id == 837395782


def test_contour_selection_is_not_mutex() -> None:
    """Actionable 837 and 148 legs are both retained in one write-set."""
    selected = choose_contours(
        [
            Candidate(39900256, (837395782,), 11, 100, "activate_paused_leg", 837395782),
            Candidate(39943851, (14824677,), 9, 0, "top_up_budget", 14824677),
        ]
    )
    assert [candidate.nm_id for candidate in selected] == [837395782, 14824677]


def test_mat_candidate_388166103_is_ranked() -> None:
    """MATS candidate 388166103 participates in ranking."""
    selected = choose_contours(
        [Candidate(77, (388166103,), 9, 0, "top_up_budget", 388166103)]
    )
    assert [candidate.nm_id for candidate in selected] == [388166103]
    assert rank_mats_candidates(selected)[0].nm_id == 388166103


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


def test_paused_auto_leg_is_an_allowed_zero_spend_lever() -> None:
    """Подходящий paused Auto leg также разрешён без искусственного top-up."""
    rows = _candidate_rows(
        [{
            "id": 39900256,
            "status": 11,
            "name": "Auto A1",
            "nm_settings": [{"nmID": 837395782}],
        }],
        {39900256: 3000},
        {837395782: (1000.0, 3000.0)},
    )
    assert rows[0].action == "activate_paused_leg"


def test_recommendations_only_leg_is_never_selected() -> None:
    """Recommendations-only placement cannot be activated by the executor."""
    rows = _candidate_rows(
        [{
            "id": 39943926,
            "status": 9,
            "name": "Search overshoot",
            "settings": {
                "placements": {"search": False, "recommendations": True},
            },
            "nm_settings": [{"nmID": 14824677}],
        }],
        {39943926: 1200},
        {14824677: (1000.0, 3000.0)},
    )
    assert rows[0].campaign_kind == "RECOMMENDATIONS_ONLY"
    assert rows[0].action == "no_change"
    assert choose_contours(rows) == []


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


def test_next_observation_day_uses_source_cutoff() -> None:
    """При данных только до вчера следующий закрытый день — сегодня."""
    assert _next_observation_day(
        [{"date": "2026-09-07"}], today=date(2026, 9, 8)
    ) == date(2026, 9, 8)
