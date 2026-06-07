"""Синтетические наборы и форматирование результатов bid-math модели."""

import math
import random
from typing import Any, TypedDict

from tests.rec_system_bid_math.bid_model import HOURS, ModelResult, Obs


class SyntheticTruth(TypedDict):
    """Истинные суточные суммы и назначение синтетического сценария."""

    true_daily_by_bid: dict[int, float]
    description: str


def synthetic_hour_profile(hour: int) -> float:
    """Сформировать базовый профиль со слабой ночью и сильным вечером."""
    night_floor = 0.35
    morning = 0.20 * math.exp(-((hour - 9) ** 2) / (2 * 3.5**2))
    midday = 0.55 * math.exp(-((hour - 14) ** 2) / (2 * 4.5**2))
    evening = 0.85 * math.exp(-((hour - 20) ** 2) / (2 * 3.2**2))
    return night_floor + morning + midday + evening


def make_sparse_confirmed_best_obs(
    *,
    days: int = 30,
    seed: int = 20260607,
) -> tuple[list[Obs], dict[int, float]]:
    """Создать sparse-сценарий с подтверждённо лучшей ставкой 130."""
    rng = random.Random(seed)
    bid_strength = {
        100: 1.00,
        115: 1.18,
        128: 1.55,
        130: 2.25,
        132: 1.58,
        145: 1.05,
        150: 1.00,
    }
    observed_hours_by_bid = {
        100: list(HOURS),
        115: [0, 1, 2, 6, 7, 8, 10, 11, 12, 13, 14, 15, 18, 19, 20, 21, 22],
        128: [0, 1, 7, 8, 10, 11, 12, 13, 19, 20, 21, 22],
        130: [1, 8, 11, 14, 20, 22],
        132: [0, 2, 7, 9, 12, 14, 18, 20, 21, 23],
        145: [18, 19, 20, 21, 22, 23],
        150: [20, 21, 22],
    }
    probabilities = {
        100: 0.90,
        115: 0.90,
        128: 0.75,
        130: 0.85,
        132: 0.75,
        145: 0.55,
        150: 0.45,
    }
    obs: list[Obs] = []

    for day in range(days):
        day_factor = (
            1.0
            + 0.05 * math.sin(day / 7 * 2 * math.pi)
            + rng.uniform(-0.02, 0.02)
        )
        for bid, strength in bid_strength.items():
            for hour in observed_hours_by_bid[bid]:
                if rng.random() > probabilities[bid]:
                    continue
                noise = 1.0 + rng.uniform(-0.035, 0.035)
                if bid in {145, 150} and hour in {20, 21, 22}:
                    noise *= 1.03
                obs.append(
                    Obs(
                        bid=bid,
                        hour=hour,
                        impressions_sum=(
                            1000.0
                            * strength
                            * synthetic_hour_profile(hour)
                            * day_factor
                            * noise
                        ),
                        valid_hours_count=1,
                    )
                )

    return obs, bid_strength


def make_one_night_hour_candidate_obs(
    *,
    days: int = 30,
    seed: int = 20260608,
) -> tuple[list[Obs], dict[int, float]]:
    """Создать сценарий, где ставка 160 наблюдается только в 03:00."""
    rng = random.Random(seed)
    bid_strength = {100: 1.00, 120: 1.25, 160: 4.00}
    obs: list[Obs] = []

    for _day in range(days):
        day_factor = 1.0 + rng.uniform(-0.01, 0.01)
        for bid in [100, 120]:
            for hour in HOURS:
                if rng.random() > 0.90:
                    continue
                obs.append(
                    Obs(
                        bid=bid,
                        hour=hour,
                        impressions_sum=(
                            1000.0
                            * bid_strength[bid]
                            * synthetic_hour_profile(hour)
                            * day_factor
                            * (1.0 + rng.uniform(-0.02, 0.02))
                        ),
                        valid_hours_count=1,
                    )
                )

        if rng.random() < 0.35:
            obs.append(
                Obs(
                    bid=160,
                    hour=3,
                    impressions_sum=(
                        1000.0
                        * bid_strength[160]
                        * synthetic_hour_profile(3)
                        * day_factor
                        * (1.0 + rng.uniform(-0.02, 0.02))
                    ),
                    valid_hours_count=1,
                )
            )

    return obs, bid_strength


def make_bad_neighbors_good_night_spike_obs(
    *,
    days: int = 30,
    seed: int = 20260609,
) -> tuple[list[Obs], SyntheticTruth]:
    """Создать spike-сценарий с очень плохими соседями 150 и 170."""
    rng = random.Random(seed)
    stable_strength = {120: 1.45, 150: 0.20, 170: 0.16}
    true_daily = {
        bid: 1000.0
        * strength
        * sum(synthetic_hour_profile(hour) for hour in HOURS)
        for bid, strength in stable_strength.items()
    }
    true_daily[160] = 7200.0
    obs: list[Obs] = []

    for _day in range(days):
        day_factor = 1.0 + rng.uniform(-0.015, 0.015)
        for bid, strength in stable_strength.items():
            for hour in HOURS:
                obs.append(
                    Obs(
                        bid=bid,
                        hour=hour,
                        impressions_sum=(
                            1000.0
                            * strength
                            * synthetic_hour_profile(hour)
                            * day_factor
                            * (1.0 + rng.uniform(-0.02, 0.02))
                        ),
                        valid_hours_count=1,
                    )
                )
        obs.append(
            Obs(
                bid=160,
                hour=3,
                impressions_sum=3300.0
                * day_factor
                * (1.0 + rng.uniform(-0.02, 0.02)),
                valid_hours_count=1,
            )
        )

    return obs, {
        "true_daily_by_bid": true_daily,
        "description": (
            "Bid 160 has one strong night observation, weak adjacent bids, "
            "and a true daily total below stable bid 120."
        ),
    }


def make_local_peak_bad_daily_obs(
    *,
    days: int = 30,
    seed: int = 20260610,
) -> tuple[list[Obs], SyntheticTruth]:
    """Создать локальный пик 160 при худшей истинной суточной сумме."""
    rng = random.Random(seed)
    stable_120 = {hour: 1400.0 * synthetic_hour_profile(hour) for hour in HOURS}
    weak_160 = {hour: 650.0 * synthetic_hour_profile(hour) for hour in HOURS}
    weak_160[3] = 3600.0
    true_daily = {120: sum(stable_120.values()), 160: sum(weak_160.values())}
    obs: list[Obs] = []

    for _day in range(days):
        day_factor = 1.0 + rng.uniform(-0.015, 0.015)
        for hour in HOURS:
            obs.append(
                Obs(
                    bid=120,
                    hour=hour,
                    impressions_sum=stable_120[hour]
                    * day_factor
                    * (1.0 + rng.uniform(-0.015, 0.015)),
                    valid_hours_count=1,
                )
            )
        obs.append(
            Obs(
                bid=160,
                hour=3,
                impressions_sum=weak_160[3]
                * day_factor
                * (1.0 + rng.uniform(-0.015, 0.015)),
                valid_hours_count=1,
            )
        )

    return obs, {
        "true_daily_by_bid": true_daily,
        "description": (
            "Bid 160 is exceptional only at 03:00 and weaker than bid 120 "
            "over the true full day; only its peak is observed."
        ),
    }


def format_rankings(
    result: ModelResult,
    truth: SyntheticTruth | dict[str, Any] | None = None,
) -> str:
    """Отформатировать все rows и добавить истинные суммы при наличии."""
    true_daily_by_bid = truth.get("true_daily_by_bid", {}) if truth else {}
    lines = ["rankings:"]

    for row in result["expected_ranked"]:
        bid = int(row["bid"])
        fields = [
            f"bid={bid}",
            f"expected_daily_impressions={row['expected_daily_impressions']:.2f}",
            f"confidence={row['confidence']:.4f}",
            f"uncertainty={row['uncertainty']:.2f}",
            f"own_anchor={row['own_anchor']:.4f}",
            f"main_score={row['main_score']:.2f}",
            f"test_score={row['test_score']:.2f}",
        ]
        if bid in true_daily_by_bid:
            fields.append(f"true_daily={true_daily_by_bid[bid]:.2f}")
        lines.append(" ".join(fields))

    return "\n".join(lines)


def print_rankings(
    result: ModelResult,
    truth: SyntheticTruth | dict[str, Any] | None = None,
) -> None:
    """Распечатать полный рейтинг в едином стендовом формате."""
    print(format_rankings(result, truth))
