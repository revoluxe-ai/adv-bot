"""Тесты DTO-границы для доменной bid-math модели."""

from app.domain.rec_system_bid_math.bid_model import run_bid_model
from app.domain.rec_system_bid_math.input_models import (
    BidHourObservation,
    to_bid_model_obs,
)


def test_bid_hour_observation_converts_to_obs() -> None:
    """DTO должен конвертироваться во внутренний Obs без потери данных."""
    observations = [
        BidHourObservation(
            bid=160,
            hour=3,
            impressions_sum=1234.5,
            valid_hours_count=2,
        )
    ]

    obs = to_bid_model_obs(observations)

    assert len(obs) == 1
    assert obs[0].bid == 160
    assert obs[0].hour == 3
    assert obs[0].impressions_sum == 1234.5
    assert obs[0].valid_hours_count == 2


def test_run_bid_model_works_with_converted_dto() -> None:
    """run_bid_model должен работать на converted DTO без прямой зависимости."""
    observations = [
        BidHourObservation(
            bid=100,
            hour=0,
            impressions_sum=1000.0,
            valid_hours_count=1,
        ),
        BidHourObservation(
            bid=100,
            hour=1,
            impressions_sum=1100.0,
            valid_hours_count=1,
        ),
        BidHourObservation(
            bid=120,
            hour=0,
            impressions_sum=1300.0,
            valid_hours_count=1,
        ),
    ]

    result = run_bid_model(to_bid_model_obs(observations))

    assert result["expected_ranked"]
    assert result["main_ranked"]
    assert result["test_ranked"]
    assert result["debug"]
