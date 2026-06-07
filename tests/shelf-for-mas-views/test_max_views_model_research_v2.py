"""Исследовательский тест модели ранжирования ставок по суточным показам.

Проверяет, что уверенность модели в восстановленном суточном профиле отделена
от покрытия ставки собственными наблюдениями. Это не позволяет ставкам с
редкими, смещёнными к пиковым часам данными стать боевой рекомендацией.
"""

import math
import random
from dataclasses import dataclass
from typing import TypeAlias

HOURS = range(24)

COUNT_CONF_N0 = 10.0
FILL_CONF_PENALTY = 0.35
OWN_SMOOTH_CONF_FACTOR = 0.5
MIN_OWN_ANCHOR_FOR_RECOMMENDATION = 0.20

HourlyValues: TypeAlias = dict[int, dict[int, float | None]]
HourlyConfidence: TypeAlias = dict[int, dict[int, float]]
HourlyCounts: TypeAlias = dict[int, dict[int, int]]
HourlyPresence: TypeAlias = dict[int, dict[int, bool]]
HourRatios: TypeAlias = dict[int, dict[int, float | None]]
RankingRow: TypeAlias = dict[str, int | float | bool]


@dataclass(frozen=True)
class Obs:
    """Агрегированное наблюдение показов для ставки и часа."""

    bid: int
    hour: int
    impressions_sum: float
    valid_hours_count: int


def conf_from_count(n: int, n0: float = COUNT_CONF_N0) -> float:
    """Рассчитать насыщаемую уверенность по числу наблюдений."""
    if n <= 0:
        return 0.0
    return n / (n + n0)


def clamp01(value: float) -> float:
    """Ограничить значение закрытым интервалом от нуля до единицы."""
    return max(0.0, min(1.0, value))


def bid_closeness(
    target_bid: int,
    source_bid: int,
    min_bid: int,
    max_bid: int,
) -> float:
    """Оценить близость исходной ставки к целевой в общем диапазоне ставок."""
    if max_bid == min_bid:
        return 1.0

    distance = abs(target_bid - source_bid)
    full_distance = max_bid - min_bid
    return clamp01(1.0 - distance / full_distance)


def product_conf(weights: list[float]) -> float:
    """Объединить независимые веса уверенности через вероятность дополнения."""
    probability_of_no_support = 1.0
    for weight in weights:
        probability_of_no_support *= 1.0 - clamp01(weight)
    return 1.0 - probability_of_no_support


def weighted_avg(values: list[float], weights: list[float]) -> float:
    """Рассчитать взвешенное среднее для положительной суммы весов."""
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("total_weight must be positive")
    return sum(value * weight for value, weight in zip(values, weights)) / total_weight


def build_observed(
    obs: list[Obs],
) -> tuple[list[int], HourlyValues, HourlyConfidence, HourlyCounts]:
    """Собрать средние показы и уверенность по наблюдаемым ставкам и часам."""
    bids = sorted({item.bid for item in obs})
    y_obs: HourlyValues = {bid: {hour: None for hour in HOURS} for bid in bids}
    c_obs: HourlyConfidence = {
        bid: {hour: 0.0 for hour in HOURS} for bid in bids
    }
    n_obs: HourlyCounts = {bid: {hour: 0 for hour in HOURS} for bid in bids}

    accumulated: dict[tuple[int, int], tuple[float, int]] = {}
    for item in obs:
        if item.valid_hours_count <= 0:
            continue

        key = (item.bid, item.hour)
        previous_impressions, previous_hours = accumulated.get(key, (0.0, 0))
        accumulated[key] = (
            previous_impressions + item.impressions_sum,
            previous_hours + item.valid_hours_count,
        )

    for (bid, hour), (impressions_sum, valid_hours_count) in accumulated.items():
        y_obs[bid][hour] = impressions_sum / valid_hours_count
        c_obs[bid][hour] = conf_from_count(valid_hours_count)
        n_obs[bid][hour] = valid_hours_count

    return bids, y_obs, c_obs, n_obs


def bid_smoothing(
    bids: list[int],
    y_obs: HourlyValues,
    c_obs: HourlyConfidence,
) -> tuple[HourlyValues, HourlyConfidence, HourlyPresence]:
    """Восстановить каждый час по данным близких ставок.

    Близкие ставки влияют сильнее, дальние слабее, а собственные наблюдения
    остаются главным якорем значения и его уверенности.
    """
    min_bid = min(bids)
    max_bid = max(bids)
    y0: HourlyValues = {bid: {} for bid in bids}
    c0: HourlyConfidence = {bid: {} for bid in bids}
    has_own: HourlyPresence = {bid: {} for bid in bids}

    for target_bid in bids:
        for hour in HOURS:
            values: list[float] = []
            weights: list[float] = []

            for source_bid in bids:
                source_value = y_obs[source_bid][hour]
                if source_value is None:
                    continue

                weight = c_obs[source_bid][hour] * bid_closeness(
                    target_bid=target_bid,
                    source_bid=source_bid,
                    min_bid=min_bid,
                    max_bid=max_bid,
                )
                if weight <= 0:
                    continue

                values.append(source_value)
                weights.append(weight)

            if not weights:
                y0[target_bid][hour] = None
                c0[target_bid][hour] = 0.0
                has_own[target_bid][hour] = False
                continue

            raw_value = weighted_avg(values, weights)
            raw_fill_conf = product_conf(weights)
            own_conf = c_obs[target_bid][hour]

            y0[target_bid][hour] = raw_value
            has_own[target_bid][hour] = own_conf > 0
            if own_conf > 0:
                c0[target_bid][hour] = max(
                    own_conf,
                    OWN_SMOOTH_CONF_FACTOR * raw_fill_conf,
                )
            else:
                c0[target_bid][hour] = FILL_CONF_PENALTY * raw_fill_conf

    return y0, c0, has_own


def build_hour_ratios(
    bids: list[int],
    y0: HourlyValues,
    c0: HourlyConfidence,
    c_obs: HourlyConfidence,
) -> tuple[HourRatios, HourlyConfidence]:
    """Построить матрицу отношений показов между часами суток.

    Ставки с малым собственным покрытием суток получают слабый вес и поэтому
    не могут существенно исказить общие часовые пропорции.
    """
    hour_ratio: HourRatios = {
        first_hour: {second_hour: None for second_hour in HOURS}
        for first_hour in HOURS
    }
    hour_conf: HourlyConfidence = {
        first_hour: {second_hour: 0.0 for second_hour in HOURS}
        for first_hour in HOURS
    }

    for hour in HOURS:
        hour_ratio[hour][hour] = 1.0
        hour_conf[hour][hour] = 1.0

    bid_anchor = {
        bid: sum(c_obs[bid][hour] for hour in HOURS) / 24.0 for bid in bids
    }

    for first_hour in HOURS:
        for second_hour in HOURS:
            if first_hour == second_hour:
                continue

            log_ratios: list[float] = []
            weights: list[float] = []
            for bid in bids:
                first_value = y0[bid][first_hour]
                second_value = y0[bid][second_hour]
                if first_value is None or second_value is None:
                    continue
                if first_value <= 0 or second_value <= 0:
                    continue

                pair_conf = math.sqrt(
                    c0[bid][first_hour] * c0[bid][second_hour]
                )
                weight = pair_conf * bid_anchor[bid]
                if weight <= 0:
                    continue

                log_ratios.append(math.log(first_value / second_value))
                weights.append(weight)

            if not weights:
                continue

            avg_log_ratio = weighted_avg(log_ratios, weights)
            hour_ratio[first_hour][second_hour] = math.exp(avg_log_ratio)
            hour_conf[first_hour][second_hour] = 1.0 - math.exp(-sum(weights))

    return hour_ratio, hour_conf


def final_recalc(
    bids: list[int],
    y0: HourlyValues,
    c0: HourlyConfidence,
    hour_ratio: HourRatios,
    hour_conf: HourlyConfidence,
) -> tuple[HourlyValues, HourlyConfidence]:
    """Пересчитать каждый час ставки по всем доступным часам этой ставки.

    Прогноз исходного часа масштабируется отношением целевого и исходного
    часов. Его вес учитывает уверенность исходного значения и пропорции часов.
    """
    y_final: HourlyValues = {bid: {} for bid in bids}
    c_final: HourlyConfidence = {bid: {} for bid in bids}

    for bid in bids:
        for target_hour in HOURS:
            values: list[float] = []
            weights: list[float] = []

            for source_hour in HOURS:
                source_value = y0[bid][source_hour]
                ratio = hour_ratio[target_hour][source_hour]
                if source_value is None or ratio is None:
                    continue

                weight = c0[bid][source_hour] * hour_conf[target_hour][source_hour]
                if weight <= 0:
                    continue

                values.append(source_value * ratio)
                weights.append(weight)

            if not weights:
                y_final[bid][target_hour] = None
                c_final[bid][target_hour] = 0.0
                continue

            y_final[bid][target_hour] = weighted_avg(values, weights)
            c_final[bid][target_hour] = 1.0 - math.exp(-sum(weights))

    return y_final, c_final


def rank_bids_by_impressions(
    obs: list[Obs],
    min_own_anchor_for_recommendation: float = (
        MIN_OWN_ANCHOR_FOR_RECOMMENDATION
    ),
) -> list[RankingRow]:
    """Ранжировать ставки по восстановленным показам и уверенности модели.

    ``model_confidence`` описывает качество восстановления суток, тогда как
    ``own_anchor`` отражает фактическое покрытие ставки собственными данными.
    Только достаточный собственный якорь делает ставку доступной для выбора.
    """
    bids, y_obs, c_obs, _n_obs = build_observed(obs)
    y0, c0, _has_own = bid_smoothing(
        bids=bids,
        y_obs=y_obs,
        c_obs=c_obs,
    )
    hour_ratio, hour_conf = build_hour_ratios(
        bids=bids,
        y0=y0,
        c0=c0,
        c_obs=c_obs,
    )
    y_final, c_final = final_recalc(
        bids=bids,
        y0=y0,
        c0=c0,
        hour_ratio=hour_ratio,
        hour_conf=hour_conf,
    )

    result: list[RankingRow] = []
    for bid in bids:
        daily_impressions = sum(y_final[bid][hour] or 0.0 for hour in HOURS)
        model_confidence = sum(c_final[bid][hour] for hour in HOURS) / 24.0
        own_anchor = sum(c_obs[bid][hour] for hour in HOURS) / 24.0
        eligible = own_anchor >= min_own_anchor_for_recommendation
        selection_score = daily_impressions * model_confidence

        result.append(
            {
                "bid": bid,
                "daily_impressions": daily_impressions,
                "model_confidence": model_confidence,
                "own_anchor": own_anchor,
                "eligible": eligible,
                "selection_score": selection_score,
            }
        )

    return sorted(
        result,
        key=lambda row: (row["eligible"], row["selection_score"]),
        reverse=True,
    )


def synthetic_hour_profile(hour: int) -> float:
    """Сформировать суточный профиль со слабой ночью и сильным вечером."""
    night_floor = 0.35
    morning = 0.20 * math.exp(-((hour - 9) ** 2) / (2 * 3.5**2))
    midday = 0.55 * math.exp(-((hour - 14) ** 2) / (2 * 4.5**2))
    evening = 0.85 * math.exp(-((hour - 20) ** 2) / (2 * 3.2**2))
    return night_floor + morning + midday + evening


def should_observe(*, bid: int, hour: int, rng: random.Random) -> bool:
    """Имитировать различное и местами смещённое покрытие ставок данными."""
    if bid == 100:
        return True
    if bid == 110:
        return hour not in {2, 3, 4, 5} and rng.random() < 0.95
    if bid == 120:
        return (
            hour
            in {
                0,
                1,
                2,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                18,
                19,
                20,
                21,
                22,
            }
            and rng.random() < 0.75
        )
    if bid == 130:
        return (
            hour
            in {
                0,
                1,
                2,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                18,
                19,
                20,
                21,
                22,
                23,
            }
            and rng.random() < 0.70
        )
    if bid == 140:
        return hour in {18, 19, 20, 21, 22, 23} and rng.random() < 0.60
    if bid == 150:
        return hour in {11, 12, 13, 20, 21} and rng.random() < 0.45
    return False


def make_large_synthetic_obs(
    *,
    days: int = 30,
    seed: int = 20260607,
) -> tuple[list[Obs], dict[int, float]]:
    """Создать воспроизводимую выборку с полными и разреженными ставками."""
    rng = random.Random(seed)
    bid_strength = {
        100: 1.00,
        110: 1.18,
        120: 1.34,
        130: 1.55,
        140: 1.52,
        150: 1.50,
    }
    obs: list[Obs] = []

    for day in range(days):
        day_factor = (
            1.0
            + 0.06 * math.sin(day / 7 * 2 * math.pi)
            + rng.uniform(-0.025, 0.025)
        )
        for bid, strength in bid_strength.items():
            for hour in HOURS:
                if not should_observe(bid=bid, hour=hour, rng=rng):
                    continue

                noise = 1.0 + rng.uniform(-0.04, 0.04)
                if bid in {140, 150} and hour in {20, 21}:
                    noise *= 1.06

                avg_impressions = (
                    1000.0
                    * strength
                    * synthetic_hour_profile(hour)
                    * day_factor
                    * noise
                )
                obs.append(
                    Obs(
                        bid=bid,
                        hour=hour,
                        impressions_sum=avg_impressions,
                        valid_hours_count=1,
                    )
                )

    return obs, bid_strength


def test_large_synthetic_rank_bids_by_impressions(capsys: object) -> None:
    """Не допустить выбора разреженной ставки по восстановленным пиковым часам."""
    obs, bid_strength = make_large_synthetic_obs()
    ranked = rank_bids_by_impressions(obs)

    print("\nranked bids:")
    for row in ranked:
        bid = int(row["bid"])
        print(
            "bid=",
            bid,
            "true_strength=",
            bid_strength[bid],
            "daily=",
            round(float(row["daily_impressions"]), 2),
            "model_conf=",
            round(float(row["model_confidence"]), 4),
            "own_anchor=",
            round(float(row["own_anchor"]), 4),
            "eligible=",
            row["eligible"],
            "score=",
            round(float(row["selection_score"]), 2),
        )

    # Печать показывается только при отключённом перехвате вывода pytest.
    assert hasattr(capsys, "readouterr")
    capsys.readouterr()  # type: ignore[attr-defined]

    assert ranked[0]["bid"] == 130
    assert ranked[0]["eligible"] is True
    assert ranked[0]["selection_score"] > ranked[1]["selection_score"]

    by_bid = {row["bid"]: row for row in ranked}
    assert by_bid[140]["eligible"] is False
    assert by_bid[150]["eligible"] is False
    assert all(float(row["model_confidence"]) > 0 for row in ranked)
    assert all(float(row["daily_impressions"]) > 0 for row in ranked)


def make_sparse_but_confirmed_best_obs(
    *,
    days: int = 30,
    seed: int = 20260607,
) -> tuple[list[Obs], dict[int, float]]:
    rng = random.Random(seed)

    bid_strength = {
        100: 1.00,
        115: 1.18,
        128: 1.47,  # близкий подтверждающий донор
        130: 1.62,  # истинно лучшая ставка, но данных меньше
        132: 1.50,  # близкий подтверждающий донор
        145: 1.45,  # вечерний peak-bias
        150: 1.42,  # sparse/noisy peak-bias
    }

    # 130 имеет мало часов, но они репрезентативны: ночь, утро, день, вечер.
    observed_hours_by_bid = {
        100: list(range(24)),                         # широкий слабый baseline
        115: [0, 1, 2, 6, 7, 8, 10, 11, 12, 13, 14, 15, 18, 19, 20, 21, 22],
        128: [0, 1, 7, 8, 10, 11, 12, 13, 19, 20, 21, 22],  # близко к 130
        130: [1, 8, 11, 14, 20, 22],                  # мало, но хорошие точки суток
        132: [0, 2, 7, 9, 12, 14, 18, 20, 21, 23],    # близко к 130
        145: [18, 19, 20, 21, 22, 23],                # только жирный вечер
        150: [20, 21, 22],                            # совсем sparse peak
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
                # 130 мало часов в сутках, но каждый выбранный час подтверждён чаще.
                if bid == 130:
                    observe_probability = 0.85
                elif bid in {128, 132}:
                    observe_probability = 0.75
                elif bid in {145, 150}:
                    observe_probability = 0.55
                else:
                    observe_probability = 0.9

                if rng.random() > observe_probability:
                    continue

                noise = 1.0 + rng.uniform(-0.035, 0.035)

                # Ловушка: дальние ставки кажутся хорошими только в вечерний пик.
                if bid in {145, 150} and hour in {20, 21, 22}:
                    noise *= 1.08

                avg_impressions = (
                    1000.0
                    * strength
                    * synthetic_hour_profile(hour)
                    * day_factor
                    * noise
                )

                obs.append(
                    Obs(
                        bid=bid,
                        hour=hour,
                        impressions_sum=avg_impressions,
                        valid_hours_count=1,
                    )
                )

    return obs, bid_strength
