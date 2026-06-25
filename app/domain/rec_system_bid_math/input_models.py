"""Входные DTO для доменной bid-math модели."""

from dataclasses import dataclass

from app.domain.rec_system_bid_math.bid_model import Obs


@dataclass(frozen=True)
class BidHourObservation:
    """Внешнее наблюдение для одной ставки и одного часа."""

    bid: int
    hour: int
    impressions_sum: float
    valid_hours_count: int


def to_bid_model_obs(
    observations: list[BidHourObservation],
) -> list[Obs]:
    """Преобразовать внешний DTO в внутренний Obs для чистой математики."""
    return [
        Obs(
            bid=observation.bid,
            hour=observation.hour,
            impressions_sum=observation.impressions_sum,
            valid_hours_count=observation.valid_hours_count,
        )
        for observation in observations
    ]
