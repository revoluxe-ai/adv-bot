import math
from dataclasses import dataclass


HOURS = range(24)

COUNT_CONF_N0 = 10.0
FILL_CONF_PENALTY = 0.35
OWN_SMOOTH_CONF_FACTOR = 0.5


@dataclass(frozen=True)
class Obs:
    bid: int
    hour: int
    impressions_sum: float
    valid_hours_count: int


def conf_from_count(n: int, n0: float = COUNT_CONF_N0) -> float:
    if n <= 0:
        return 0.0
    return n / (n + n0)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def bid_closeness(
    target_bid: int,
    source_bid: int,
    min_bid: int,
    max_bid: int,
) -> float:
    if max_bid == min_bid:
        return 1.0

    distance = abs(target_bid - source_bid)
    full_distance = max_bid - min_bid

    return clamp01(1.0 - distance / full_distance)


def product_conf(weights: list[float]) -> float:
    """
    Вероятностное объединение доверий:
    один сильный источник даёт доверие,
    много сильных источников повышают доверие,
    результат всегда 0..1.
    """
    p = 1.0
    for w in weights:
        p *= 1.0 - clamp01(w)
    return 1.0 - p


def weighted_avg(values: list[float], weights: list[float]) -> float:
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("total_weight must be positive")

    return sum(v * w for v, w in zip(values, weights)) / total_weight


def build_observed(obs: list[Obs]):
    bids = sorted({o.bid for o in obs})

    y_obs = {b: {h: None for h in HOURS} for b in bids}
    c_obs = {b: {h: 0.0 for h in HOURS} for b in bids}
    n_obs = {b: {h: 0 for h in HOURS} for b in bids}

    for o in obs:
        if o.valid_hours_count <= 0:
            continue

        y_obs[o.bid][o.hour] = o.impressions_sum / o.valid_hours_count
        c_obs[o.bid][o.hour] = conf_from_count(o.valid_hours_count)
        n_obs[o.bid][o.hour] = o.valid_hours_count

    return bids, y_obs, c_obs, n_obs


def bid_smoothing(bids, y_obs, c_obs):
    """
    Первый слой.

    Для каждой ячейки bid+hour считаем значение через все ставки,
    у которых есть данные в этом же hour.

    Близкие ставки влияют сильно.
    Далёкие ставки влияют слабо.
    Собственные данные остаются самым сильным источником.
    """
    min_bid = min(bids)
    max_bid = max(bids)

    y0 = {b: {} for b in bids}
    c0 = {b: {} for b in bids}
    has_own = {b: {} for b in bids}

    for target_bid in bids:
        for hour in HOURS:
            values = []
            weights = []

            for source_bid in bids:
                source_value = y_obs[source_bid][hour]
                if source_value is None:
                    continue

                closeness = bid_closeness(
                    target_bid=target_bid,
                    source_bid=source_bid,
                    min_bid=min_bid,
                    max_bid=max_bid,
                )

                weight = c_obs[source_bid][hour] * closeness
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


def build_hour_ratios(bids, y0, c0, c_obs):
    """
    Второй слой.

    Строим матрицу пропорций часов:
    hour_ratio[h1][h2] = во сколько раз h1 отличается от h2.

    Пропорции считаются по всем ставкам.
    Но ставка с малым собственным покрытием суток плохо учит пропорциям.
    """
    hour_ratio = {h1: {h2: None for h2 in HOURS} for h1 in HOURS}
    hour_conf = {h1: {h2: 0.0 for h2 in HOURS} for h1 in HOURS}

    for h in HOURS:
        hour_ratio[h][h] = 1.0
        hour_conf[h][h] = 1.0

    bid_anchor = {
        b: sum(c_obs[b][h] for h in HOURS) / 24.0
        for b in bids
    }

    for h1 in HOURS:
        for h2 in HOURS:
            if h1 == h2:
                continue

            log_ratios = []
            weights = []

            for bid in bids:
                y1 = y0[bid][h1]
                y2 = y0[bid][h2]

                if y1 is None or y2 is None:
                    continue
                if y1 <= 0 or y2 <= 0:
                    continue

                pair_conf = math.sqrt(c0[bid][h1] * c0[bid][h2])
                weight = pair_conf * bid_anchor[bid]

                if weight <= 0:
                    continue

                log_ratios.append(math.log(y1 / y2))
                weights.append(weight)

            if not weights:
                continue

            avg_log_ratio = weighted_avg(log_ratios, weights)

            hour_ratio[h1][h2] = math.exp(avg_log_ratio)
            hour_conf[h1][h2] = 1.0 - math.exp(-sum(weights))

    return hour_ratio, hour_conf


def final_recalc(bids, y0, c0, hour_ratio, hour_conf):
    """
    Третий слой.

    Для каждой ячейки bid+hour пересчитываем значение через все часы этой же ставки.

    Каждый другой час source_hour даёт прогноз:
    y0[bid][source_hour] * hour_ratio[target_hour][source_hour]

    Вес прогноза:
    достоверность source_hour * достоверность пропорции часов.
    """
    y_final = {b: {} for b in bids}
    c_final = {b: {} for b in bids}

    for bid in bids:
        for target_hour in HOURS:
            values = []
            weights = []

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


def rank_bids_by_impressions(obs: list[Obs]):
    bids, y_obs, c_obs, _n_obs = build_observed(obs)

    y0, c0, _has_own = bid_smoothing(bids, y_obs, c_obs)

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

    result = []

    for bid in bids:
        daily_impressions = sum(y_final[bid][h] or 0.0 for h in HOURS)
        confidence = sum(c_final[bid][h] for h in HOURS) / 24.0

        selection_score = daily_impressions * confidence

        result.append(
            {
                "bid": bid,
                "daily_impressions": daily_impressions,
                "confidence": confidence,
                "selection_score": selection_score,
            }
        )

    return sorted(result, key=lambda x: x["selection_score"], reverse=True)


def test_rank_bids_by_impressions_on_synthetic_data():
    """
    Синтетика:

    Истинная сила ставок:
    120 — лучшая.
    130 — имеет хорошие дневные часы, но мало покрытия и меньше доверия.

    Проверяем, что побеждает не просто ставка с жирными дневными наблюдениями,
    а ставка с лучшим показовым score с учётом confidence.
    """
    bid_strength = {
        100: 1.00,
        110: 1.15,
        120: 1.70,
        130: 1.25,
    }

    hour_strength = {
        h: 0.5 + 0.8 * math.sin((h - 6) / 24 * 2 * math.pi) ** 2
        for h in HOURS
    }

    observed_hours = {
        100: list(range(0, 24, 2)),          # 12 часов
        110: list(range(6, 18)),             # 12 дневных часов
        120: [0, 1, 2, 10, 11, 12, 20, 21],  # дыряво, но сильная ставка
        130: [8, 9, 10, 11, 12, 13],         # мало часов, опасный peak-bias
    }

    obs = []

    for bid, hours in observed_hours.items():
        for hour in hours:
            if bid in (100, 110, 120):
                valid_hours_count = 20
            else:
                valid_hours_count = 10

            avg_impressions_per_hour = (
                1000
                * bid_strength[bid]
                * hour_strength[hour]
            )

            obs.append(
                Obs(
                    bid=bid,
                    hour=hour,
                    impressions_sum=avg_impressions_per_hour * valid_hours_count,
                    valid_hours_count=valid_hours_count,
                )
            )

    ranked = rank_bids_by_impressions(obs)

    assert ranked[0]["bid"] == 120
    assert ranked[0]["selection_score"] > ranked[1]["selection_score"]
    assert ranked[0]["daily_impressions"] > 0
    assert ranked[0]["confidence"] > 0
    assert all(row["confidence"] > 0 for row in ranked)
