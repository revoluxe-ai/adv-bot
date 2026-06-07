"""Регрессионные тесты исходных синтетических bid-math сценариев."""

from tests.rec_system_bid_math.bid_model import run_bid_model
from tests.bid_math.synthetic_cases import (
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

    by_bid = {row["bid"]: row for row in result["rows"]}
    assert by_bid[130]["main_score"] > by_bid[128]["main_score"]
    assert by_bid[130]["main_score"] > by_bid[132]["main_score"]
    assert by_bid[130]["main_score"] > by_bid[145]["main_score"]
    assert by_bid[130]["own_anchor"] < by_bid[100]["own_anchor"]
    assert (
        by_bid[130]["expected_daily_impressions"]
        > by_bid[100]["expected_daily_impressions"]
    )


def test_one_strong_night_hour_can_become_top_expected_and_test_candidate() -> None:
    """Сохранить исходное поведение кандидата с одним ночным часом."""
    obs, _strength = make_one_night_hour_candidate_obs()
    result = run_bid_model(obs)
    print_rankings(result)
    assert result["expected_ranked"][0]["bid"] == 160
    assert result["test_ranked"][0]["bid"] == 160

    by_bid = {row["bid"]: row for row in result["rows"]}
    assert by_bid[160]["own_anchor"] < by_bid[100]["own_anchor"]
    assert (
        by_bid[160]["expected_daily_impressions"]
        > by_bid[120]["expected_daily_impressions"]
    )
    assert by_bid[160]["uncertainty"] > by_bid[120]["uncertainty"]
