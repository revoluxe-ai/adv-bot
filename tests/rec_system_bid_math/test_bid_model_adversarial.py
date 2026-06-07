"""Adversarial-тесты новой архитектуры bid-math."""

import pytest

from app.domain.rec_system_bid_math.bid_model import run_bid_model
from tests.rec_system_bid_math.synthetic_cases import (
    make_bad_neighbors_good_night_spike_obs,
    make_local_peak_bad_daily_obs,
    print_rankings,
)


def test_bad_neighbors_limit_good_night_spike() -> None:
    """Плохие соседи должны ограничивать один сильный ночной час."""
    obs, truth = make_bad_neighbors_good_night_spike_obs()
    result = run_bid_model(obs)
    print_rankings(result, truth)
    print("debug bid=160 hour=3:", result["debug"][160][3])
    print("debug bid=160 hour=12:", result["debug"][160][12])

    expected_bids = [row["bid"] for row in result["expected_ranked"]]
    assert 160 in expected_bids
    assert result["expected_ranked"][0]["bid"] not in {150, 170}
    assert result["expected_ranked"][0]["bid"] == 120


def test_local_peak_sparse_bid_becomes_top_interesting_candidate() -> None:
    """Локальный сильный пик должен стать кандидатом на перетест."""
    obs, truth = make_local_peak_bad_daily_obs()
    result = run_bid_model(obs)
    print_rankings(result, truth)

    assert result["expected_ranked"][0]["bid"] == 160
    assert result["test_ranked"][0]["bid"] == 160
    assert result["debug"][160][3]["own_value"] is not None


@pytest.mark.parametrize("seed", range(20))
def test_local_peak_candidate_stable_across_seeds(seed: int) -> None:
    """Локальный peak-риск должен воспроизводиться на разных seed."""
    obs, _truth = make_local_peak_bad_daily_obs(seed=seed)
    result = run_bid_model(obs)

    assert result["expected_ranked"][0]["bid"] == 160
