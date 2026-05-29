"""Уровни данных V3 по ключу: свои CH+conv → агрегат РК → max среди ключей → N-state.

``NO_CH_MATRIX`` — нет CH bid profile. ``NO_CONV`` — матрица есть, conv нельзя импутировать.
Недостаток своей conv/CPO не отправляет ключ в ``plan_no_data_keyword_actions``: подставляется
``effective_conv`` для ``build_mode_candidates`` / M1/M2/M3 с отдельным ``KeywordV3DecisionTier``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )


class KeywordV3DecisionTier(str, Enum):
    """Источник conv/CPO для лестницы V3 (не путать с ``SalesStates.NO_DATA`` кампании)."""

    FULL = "full"
    """Свои показы и conv_views_to_orders + CH-матрица."""

    RK_AGGREGATE = "rk_aggregate"
    """Средневзвешенная conv по ключам РК с показами (как общая статистика V2/CH)."""

    PEER_MAX = "peer_max"
    """Max conv среди других ключей РК с показами (нет своих показов)."""

    NO_CH_MATRIX = "no_ch_matrix"
    """Нет CH bid profile — только N-state activation (MIN_CPA / target_place=0)."""

    NO_CONV = "no_conv"
    """CH bid profile есть, conv нельзя импутировать ни из одного источника."""


_N_STATE_TIERS: frozenset[KeywordV3DecisionTier] = frozenset(
    {
        KeywordV3DecisionTier.NO_CH_MATRIX,
        KeywordV3DecisionTier.NO_CONV,
    }
)


@dataclass(frozen=True, slots=True)
class KeywordV3Decision:
    """Решение по данным ключа для одного тика V3."""

    tier: KeywordV3DecisionTier
    effective_conv_views_to_orders: float | None
    imputed: bool
    has_ch_position_profile: bool

    @property
    def in_ladder_pool(self) -> bool:
        """Участвует в M1/M2/M3 / gap-rebalance с CH (не N-state preamble)."""
        return (
            self.has_ch_position_profile
            and self.tier not in _N_STATE_TIERS
            and self.effective_conv_views_to_orders is not None
            and self.effective_conv_views_to_orders > 0
        )


def _keyword_has_own_conv(keyword: CalculatedKeyword) -> bool:
    stat = keyword.cluster_stat
    return stat.views > 0 and keyword.conv_views_to_orders > 0


def rating_aligned_cpm(keyword: CalculatedKeyword) -> float | None:
    """CPM как в рейтинге/карточке: set_bid → stats → cluster_stat, без bid_log/api.

    Нулевые значения пропускаются (не блокируют fall-through), как для ``cluster_stat.cpm``.
    """
    sources = keyword.cpm_sources
    if sources is not None:
        if sources.cpm_set_bid is not None and int(sources.cpm_set_bid) > 0:
            return float(sources.cpm_set_bid)
        if sources.cpm_from_stats is not None and float(sources.cpm_from_stats) > 0:
            return float(sources.cpm_from_stats)
    stat_cpm = getattr(keyword.cluster_stat, "cpm", None)
    if stat_cpm is not None and float(stat_cpm) > 0:
        return float(stat_cpm)
    return None


def pessimistic_min_cpa_cost(
    worst_costs: dict[AggressionTargetMode, float] | None,
) -> float | None:
    """Worst (max) predicted CPA по MIN_CPA среди ключей РК с CH-матрицей."""
    if worst_costs is None:
        return None
    cost = worst_costs.get(AggressionTargetMode.MIN_CPA)
    if cost is None or cost <= 0:
        return None
    return float(cost)


def keyword_has_v2_cpo(
    keyword: CalculatedKeyword,
    *,
    worst_costs: dict[AggressionTargetMode, float] | None = None,
) -> bool:
    """Есть V2 CPO: rating CPM + conv или pessimistic MIN с других ключей."""
    return (
        resolve_keyword_v2_pay_for_order_cost(keyword, worst_costs=worst_costs)
        is not None
    )


def resolve_keyword_v2_pay_for_order_cost(
    keyword: CalculatedKeyword,
    *,
    worst_costs: dict[AggressionTargetMode, float] | None = None,
) -> float | None:
    """Себестоимость для NO-CH MIN: conv + rating CPM; иначе pessimistic MIN с РК.

    Не использует ``keyword.pay_for_order`` (каскад с bid_log). При отсутствии CPM
    возвращает ``worst_costs[MIN_CPA]`` — worst predicted CPA по ключам с CH-матрицей.
    """
    conv = keyword.conv_views_to_orders
    if conv is None or conv <= 0:
        return None
    cpm = rating_aligned_cpm(keyword)
    if cpm is not None and cpm > 0:
        orders = calc_orders_per_1000_rub(float(conv), cpm)
        if orders is None:
            return None
        result = calc_pay_for_order(orders)
        return None if result is None else float(result)
    return pessimistic_min_cpa_cost(worst_costs)


def _weighted_campaign_conv(contexts: list["KeywordV3Context"]) -> float | None:
    """Средневзвешенная conv показ→заказ по ключам РК с показами в окне."""
    num = 0.0
    den = 0.0
    for ctx in contexts:
        stat = ctx.keyword.cluster_stat
        views = int(stat.views)
        if views <= 0:
            continue
        conv = float(ctx.keyword.conv_views_to_orders)
        if conv <= 0:
            continue
        num += conv * views
        den += float(views)
    if den <= 0:
        return None
    return num / den


def _peer_max_conv(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
) -> float | None:
    """Максимум conv среди других ключей РК с показами."""
    own_text = ctx.keyword.text.lower()
    best: float | None = None
    for other in contexts:
        if other.keyword.text.lower() == own_text:
            continue
        conv = float(other.keyword.conv_views_to_orders)
        if conv <= 0:
            continue
        if best is None or conv > best:
            best = conv
    return best


def resolve_keyword_v3_decision(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
) -> KeywordV3Decision:
    """Цепочка: свои данные → агрегат РК → max по соседям → N-state (нет CH или conv)."""
    profile = ctx.position_profile
    has_ch = bool(profile)
    if not has_ch:
        if keyword_has_v2_cpo(ctx.keyword):
            conv = ctx.keyword.conv_views_to_orders
            eff_conv = float(conv) if conv is not None and conv > 0 else None
            return KeywordV3Decision(
                tier=KeywordV3DecisionTier.NO_CH_MATRIX,
                effective_conv_views_to_orders=eff_conv,
                imputed=False,
                has_ch_position_profile=False,
            )
        return KeywordV3Decision(
            tier=KeywordV3DecisionTier.NO_CH_MATRIX,
            effective_conv_views_to_orders=None,
            imputed=False,
            has_ch_position_profile=False,
        )

    if _keyword_has_own_conv(ctx.keyword):
        return KeywordV3Decision(
            tier=KeywordV3DecisionTier.FULL,
            effective_conv_views_to_orders=float(ctx.keyword.conv_views_to_orders),
            imputed=False,
            has_ch_position_profile=True,
        )

    agg = _weighted_campaign_conv(contexts)
    if agg is not None and agg > 0:
        return KeywordV3Decision(
            tier=KeywordV3DecisionTier.RK_AGGREGATE,
            effective_conv_views_to_orders=agg,
            imputed=True,
            has_ch_position_profile=True,
        )

    peer = _peer_max_conv(ctx, contexts)
    if peer is not None and peer > 0:
        return KeywordV3Decision(
            tier=KeywordV3DecisionTier.PEER_MAX,
            effective_conv_views_to_orders=peer,
            imputed=True,
            has_ch_position_profile=True,
        )

    return KeywordV3Decision(
        tier=KeywordV3DecisionTier.NO_CONV,
        effective_conv_views_to_orders=None,
        imputed=False,
        has_ch_position_profile=True,
    )


def effective_conv_for_v3(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
) -> float | None:
    """Conv для ``build_mode_candidates`` с учётом импутации."""
    return resolve_keyword_v3_decision(ctx, contexts).effective_conv_views_to_orders


def keyword_lacks_v3_decision_data(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
) -> bool:
    """Keyword-level bootstrap (INVALID tier): нет данных даже для MIN-only ladder."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
        resolve_keyword_v3_eligibility,
    )

    return (
        resolve_keyword_v3_eligibility(ctx, contexts).data_tier
        == KeywordDataTier.KEYWORD_INVALID
    )


def keyword_v2_pay_for_order_unavailable_with_conv(
    keyword: CalculatedKeyword,
    *,
    conv_views_to_orders: float | None,
    worst_costs: dict[AggressionTargetMode, float] | None = None,
) -> bool:
    """Нет CPO: rating CPM + conv или pessimistic MIN; без каскада bid_log."""
    if conv_views_to_orders is None or conv_views_to_orders <= 0:
        return True
    return (
        resolve_keyword_v2_pay_for_order_cost(
            keyword, worst_costs=worst_costs
        )
        is None
    )


def tier_label_ru(tier: KeywordV3DecisionTier) -> str:
    """Короткая подпись уровня данных для UI."""
    return {
        KeywordV3DecisionTier.FULL: "свои CH+conv",
        KeywordV3DecisionTier.RK_AGGREGATE: "агрегат РК",
        KeywordV3DecisionTier.PEER_MAX: "max conv по РК",
        KeywordV3DecisionTier.NO_CH_MATRIX: "нет матрицы CH",
        KeywordV3DecisionTier.NO_CONV: "нет conv (импутация невозможна)",
    }[tier]
