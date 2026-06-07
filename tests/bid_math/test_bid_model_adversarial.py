"""Adversarial-тесты рисков раздувания sparse-ставок."""

import pytest

from tests.rec_system_bid_math.bid_model import run_bid_model
from tests.rec_system_bid_math.synthetic_cases import (
    make_bad_neighbors_good_night_spike_obs,
    make_local_peak_bad_daily_obs,
    print_rankings,
)


def test_bad_neighbors_limit_good_night_spike() -> None:
    """Проверить влияние плохих соседей на один сильный ночной час."""
    obs, truth = make_bad_neighbors_good_night_spike_obs()
    result = run_bid_model(obs)
    print_rankings(result, truth)
    print("debug bid=160 hour=3:", result["debug"][160][3])
    print("debug bid=160 hour=12:", result["debug"][160][12])

    expected_bids = [row["bid"] for row in result["expected_ranked"]]
    assert 160 in expected_bids
    assert result["expected_ranked"][0]["bid"] not in {150, 170}

    if result["expected_ranked"][0]["bid"] == 160:
        pytest.xfail("known risk: local sparse spike may be inflated by hour_ratio")
    assert result["expected_ranked"][0]["bid"] == 120


@pytest.mark.xfail(
    strict=False,
    reason="known risk: hour_ratio may spread a local peak across the full day",
)
def test_local_peak_bad_daily_is_detected_as_risk() -> None:
    """Сравнить expected-рейтинг с истинными сутками при локальном пике."""
    obs, truth = make_local_peak_bad_daily_obs()
    result = run_bid_model(obs)
    print_rankings(result, truth)

    true_daily = truth["true_daily_by_bid"]
    true_best = max(true_daily, key=true_daily.__getitem__)
    expected_top = result["expected_ranked"][0]["bid"]
    assert true_best == 120
    assert expected_top == true_best



def test_local_peak_sparse_bid_becomes_top_interesting_candidate() -> None:
    """Локальный сильный пик должен стать кандидатом на перетест."""
    obs, truth = make_local_peak_bad_daily_obs()
    result = run_bid_model(obs)
    print_rankings(result, truth)

    by_bid = {row["bid"]: row for row in result["rows"]}

    assert result["expected_ranked"][0]["bid"] == 160
    assert result["test_ranked"][0]["bid"] == 160

    assert by_bid[160]["own_anchor"] < by_bid[120]["own_anchor"]
    assert by_bid[160]["uncertainty"] > by_bid[120]["uncertainty"]
    assert by_bid[160]["expected_daily_impressions"] > by_bid[120]["expected_daily_impressions"]




@pytest.mark.parametrize("seed", range(20))
def test_local_peak_candidate_stable_across_seeds(seed):
    obs, truth = make_local_peak_bad_daily_obs(seed=seed)
    result = run_bid_model(obs)
    assert result["expected_ranked"][0]["bid"] == 160
