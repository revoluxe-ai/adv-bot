"""Регрессионные тесты новой архитектуры bid-math."""

from app.domain.rec_system_bid_math.bid_model import run_bid_model
from tests.rec_system_bid_math.synthetic_cases import (
    make_one_night_hour_candidate_obs,
    make_sparse_confirmed_best_obs,
    print_rankings,
)


def test_sparse_confirmed_bid_becomes_best_main_candidate() -> None:
    """Подтверждённая соседями sparse-ставка должна победить в main."""
    obs, _strength = make_sparse_confirmed_best_obs()
    result = run_bid_model(obs)
    print_rankings(result)

    assert result["main_ranked"][0]["bid"] == 130


def test_one_strong_night_hour_can_become_top_expected_and_test_candidate() -> None:
    """Сильный sparse-сигнал должен быть виден в expected и test."""
    obs, _strength = make_one_night_hour_candidate_obs()
    result = run_bid_model(obs)
    print_rankings(result)

    assert result["expected_ranked"][0]["bid"] == 160
    assert result["test_ranked"][0]["bid"] == 160
