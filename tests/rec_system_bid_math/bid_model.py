"""Чистое математическое ядро стендовой модели прогнозирования ставок.

Модуль работает только с переданными наблюдениями и не зависит от приложения,
базы данных или ClickHouse.
"""

import math
from dataclasses import dataclass
from typing import Any, TypeAlias

HOURS = range(24)
COUNT_CONF_N0 = 10.0
LAMBDA_OWN = 1.0
LAMBDA_SAME_HOUR = 0.85
LAMBDA_HOUR_RATIO = 0.85
MAIN_GAMMA = 0.5
TEST_BETA = 0.75

HourlyValues: TypeAlias = dict[int, dict[int, float | None]]
HourlyConfidence: TypeAlias = dict[int, dict[int, float]]
HourlyCounts: TypeAlias = dict[int, dict[int, int]]
ModelResult: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class Obs:
    """Агрегированное наблюдение показов для одной ставки и часа."""

    bid: int
    hour: int
    impressions_sum: float
    valid_hours_count: int


def conf_from_count(n: int, n0: float = COUNT_CONF_N0) -> float:
    """Рассчитать насыщаемую уверенность по числу валидных наблюдений."""
    if n <= 0:
        return 0.0
    return n / (n + n0)


def _clamp01(value: float) -> float:
    """Ограничить значение интервалом от нуля до единицы."""
    return max(0.0, min(1.0, value))


def bid_closeness(
    target_bid: int,
    source_bid: int,
    min_bid: int,
    max_bid: int,
) -> float:
    """Оценить линейную близость ставок внутри наблюдаемого диапазона."""
    if max_bid == min_bid:
        return 1.0
    return _clamp01(1.0 - abs(target_bid - source_bid) / (max_bid - min_bid))


def product_conf(weights: list[float]) -> float:
    """Объединить независимые веса уверенности."""
    probability_of_no_support = 1.0
    for weight in weights:
        probability_of_no_support *= 1.0 - _clamp01(weight)
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
    """Собрать средние observed-значения и уверенность по bid-hour."""
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


def estimate_same_hour_from_bids(
    *,
    bids: list[int],
    y_obs: HourlyValues,
    c_obs: HourlyConfidence,
    target_bid: int,
    target_hour: int,
) -> tuple[float | None, float]:
    """Оценить ячейку по observed-данным других ставок в том же часу."""
    min_bid = min(bids)
    max_bid = max(bids)
    values: list[float] = []
    weights: list[float] = []

    for source_bid in bids:
        if source_bid == target_bid:
            continue
        source_value = y_obs[source_bid][target_hour]
        if source_value is None or source_value <= 0:
            continue
        weight = c_obs[source_bid][target_hour] * bid_closeness(
            target_bid, source_bid, min_bid, max_bid
        )
        if weight <= 0:
            continue
        values.append(source_value)
        weights.append(weight)

    if not weights:
        return None, 0.0
    return weighted_avg(values, weights), product_conf(weights)


def build_hour_ratios_from_observed(
    *,
    bids: list[int],
    y_obs: HourlyValues,
    c_obs: HourlyConfidence,
) -> tuple[HourlyValues, HourlyConfidence]:
    """Построить пропорции часов исключительно по observed-данным."""
    min_bid = min(bids)
    max_bid = max(bids)
    hour_ratio: HourlyValues = {
        first: {second: None for second in HOURS} for first in HOURS
    }
    hour_conf: HourlyConfidence = {
        first: {second: 0.0 for second in HOURS} for first in HOURS
    }

    for hour in HOURS:
        hour_ratio[hour][hour] = 1.0
        hour_conf[hour][hour] = 1.0

    for first_hour in HOURS:
        for second_hour in HOURS:
            if first_hour == second_hour:
                continue
            log_ratios: list[float] = []
            weights: list[float] = []

            for first_bid in bids:
                first_value = y_obs[first_bid][first_hour]
                if first_value is None or first_value <= 0:
                    continue
                for second_bid in bids:
                    second_value = y_obs[second_bid][second_hour]
                    if second_value is None or second_value <= 0:
                        continue
                    closeness = bid_closeness(
                        first_bid, second_bid, min_bid, max_bid
                    )
                    if closeness <= 0:
                        continue
                    weight = (
                        math.sqrt(
                            c_obs[first_bid][first_hour]
                            * c_obs[second_bid][second_hour]
                        )
                        * closeness
                    )
                    if weight <= 0:
                        continue
                    log_ratios.append(math.log(first_value / second_value))
                    weights.append(weight)

            if weights:
                hour_ratio[first_hour][second_hour] = math.exp(
                    weighted_avg(log_ratios, weights)
                )
                hour_conf[first_hour][second_hour] = product_conf(weights)

    return hour_ratio, hour_conf


def estimate_by_hour_ratios(
    *,
    bids: list[int],
    y_obs: HourlyValues,
    c_obs: HourlyConfidence,
    hour_ratio: HourlyValues,
    hour_conf: HourlyConfidence,
    target_bid: int,
    target_hour: int,
) -> tuple[float | None, float]:
    """Оценить ячейку по observed-часам и общей матрице часовых пропорций."""
    min_bid = min(bids)
    max_bid = max(bids)
    values: list[float] = []
    weights: list[float] = []

    for source_bid in bids:
        closeness = bid_closeness(target_bid, source_bid, min_bid, max_bid)
        if closeness <= 0:
            continue
        for source_hour in HOURS:
            if source_hour == target_hour:
                continue
            source_value = y_obs[source_bid][source_hour]
            ratio = hour_ratio[target_hour][source_hour]
            if source_value is None or source_value <= 0 or ratio is None:
                continue
            weight = (
                c_obs[source_bid][source_hour]
                * closeness
                * hour_conf[target_hour][source_hour]
            )
            if weight <= 0:
                continue
            values.append(source_value * ratio)
            weights.append(weight)

    if not weights:
        return None, 0.0
    return weighted_avg(values, weights), product_conf(weights)


def combine_cell(
    *,
    own_value: float | None,
    own_conf: float,
    same_hour_value: float | None,
    same_hour_conf: float,
    hour_ratio_value: float | None,
    hour_ratio_conf: float,
) -> tuple[float | None, float]:
    """Объединить собственную, same-hour и hour-ratio оценки ячейки."""
    values: list[float] = []
    weights: list[float] = []

    if own_value is not None and own_conf > 0:
        values.append(own_value)
        weights.append(LAMBDA_OWN * own_conf)
    if same_hour_value is not None and same_hour_conf > 0:
        values.append(same_hour_value)
        weights.append(LAMBDA_SAME_HOUR * same_hour_conf)
    if hour_ratio_value is not None and hour_ratio_conf > 0:
        values.append(hour_ratio_value)
        weights.append(LAMBDA_HOUR_RATIO * hour_ratio_conf)

    if not weights:
        return None, 0.0
    return weighted_avg(values, weights), product_conf(weights)


def calculate_bid_hour_matrix(obs: list[Obs]) -> ModelResult:
    """Рассчитать итоговую bid-hour матрицу и debug каждой ячейки."""
    bids, y_obs, c_obs, n_obs = build_observed(obs)
    hour_ratio, hour_conf = build_hour_ratios_from_observed(
        bids=bids, y_obs=y_obs, c_obs=c_obs
    )
    y_final: HourlyValues = {bid: {} for bid in bids}
    c_final: HourlyConfidence = {bid: {} for bid in bids}
    debug: dict[int, dict[int, dict[str, float | None]]] = {
        bid: {} for bid in bids
    }

    for bid in bids:
        for hour in HOURS:
            own_value = y_obs[bid][hour]
            own_conf = c_obs[bid][hour]
            same_value, same_conf = estimate_same_hour_from_bids(
                bids=bids,
                y_obs=y_obs,
                c_obs=c_obs,
                target_bid=bid,
                target_hour=hour,
            )
            ratio_value, ratio_conf = estimate_by_hour_ratios(
                bids=bids,
                y_obs=y_obs,
                c_obs=c_obs,
                hour_ratio=hour_ratio,
                hour_conf=hour_conf,
                target_bid=bid,
                target_hour=hour,
            )
            final_value, final_conf = combine_cell(
                own_value=own_value,
                own_conf=own_conf,
                same_hour_value=same_value,
                same_hour_conf=same_conf,
                hour_ratio_value=ratio_value,
                hour_ratio_conf=ratio_conf,
            )
            y_final[bid][hour] = final_value
            c_final[bid][hour] = final_conf
            debug[bid][hour] = {
                "own_value": own_value,
                "own_conf": own_conf,
                "same_hour_value": same_value,
                "same_hour_conf": same_conf,
                "hour_ratio_value": ratio_value,
                "hour_ratio_conf": ratio_conf,
                "final_value": final_value,
                "final_conf": final_conf,
            }

    return {
        "bids": bids,
        "y_final": y_final,
        "c_final": c_final,
        "debug": debug,
        "hour_ratio": hour_ratio,
        "hour_conf": hour_conf,
        "y_obs": y_obs,
        "c_obs": c_obs,
        "n_obs": n_obs,
    }


def rank_bids_by_impressions(
    obs: list[Obs],
    *,
    main_gamma: float = MAIN_GAMMA,
    test_beta: float = TEST_BETA,
) -> ModelResult:
    """Построить полные expected, main и test рейтинги всех ставок."""
    matrix = calculate_bid_hour_matrix(obs)
    bids: list[int] = matrix["bids"]
    y_final: HourlyValues = matrix["y_final"]
    c_final: HourlyConfidence = matrix["c_final"]
    c_obs: HourlyConfidence = matrix["c_obs"]
    rows: list[dict[str, int | float]] = []

    for bid in bids:
        expected = sum(y_final[bid][hour] or 0.0 for hour in HOURS)
        confidence = sum(c_final[bid][hour] for hour in HOURS) / 24.0
        uncertainty = expected * (1.0 - confidence)
        rows.append(
            {
                "bid": bid,
                "expected_daily_impressions": expected,
                "confidence": confidence,
                "uncertainty": uncertainty,
                "main_score": expected - main_gamma * uncertainty,
                "test_score": expected + test_beta * uncertainty,
                "own_anchor": sum(c_obs[bid][hour] for hour in HOURS) / 24.0,
            }
        )

    return {
        "rows": rows,
        "expected_ranked": sorted(
            rows,
            key=lambda row: row["expected_daily_impressions"],
            reverse=True,
        ),
        "main_ranked": sorted(
            rows, key=lambda row: row["main_score"], reverse=True
        ),
        "test_ranked": sorted(
            rows, key=lambda row: row["test_score"], reverse=True
        ),
        **matrix,
    }


def run_bid_model(
    obs: list[Obs],
    *,
    main_gamma: float = MAIN_GAMMA,
    test_beta: float = TEST_BETA,
) -> ModelResult:
    """Запустить полный расчёт и вернуть рейтинги, матрицы и debug."""
    return rank_bids_by_impressions(
        obs, main_gamma=main_gamma, test_beta=test_beta
    )
