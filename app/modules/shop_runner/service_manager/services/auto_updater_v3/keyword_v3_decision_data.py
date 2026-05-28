"""Уровни данных V3 по ключу: свои CH+conv → агрегат РК → max среди ключей → N-state.

N-state (``NO_CH_MATRIX``) — только нет матрицы CH bid profile. Недостаток своей conv/CPO
не отправляет ключ в ``plan_no_data_keyword_actions``: подставляется ``effective_conv``
для ``build_mode_candidates`` / M1/M2/M3 с отдельным ``KeywordV3DecisionTier``.
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
            and self.tier != KeywordV3DecisionTier.NO_CH_MATRIX
            and self.effective_conv_views_to_orders is not None
            and self.effective_conv_views_to_orders > 0
        )


def _keyword_has_own_conv(keyword: CalculatedKeyword) -> bool:
    stat = keyword.cluster_stat
    return stat.views > 0 and keyword.conv_views_to_orders > 0


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
    """Цепочка: свои данные → агрегат РК → max по соседним ключам → N-state (нет CH)."""
    profile = ctx.position_profile
    has_ch = bool(profile)
    if not has_ch:
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
        tier=KeywordV3DecisionTier.NO_CH_MATRIX,
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
    """N-state preamble: нет CH или нельзя подобрать conv даже из РК/соседей."""
    return not resolve_keyword_v3_decision(ctx, contexts).in_ladder_pool


def keyword_v2_pay_for_order_unavailable_with_conv(
    keyword: CalculatedKeyword,
    *,
    conv_views_to_orders: float | None,
) -> bool:
    """Нет CPO при заданной conv (своя или импутированная)."""
    if conv_views_to_orders is None or conv_views_to_orders <= 0:
        return True
    if keyword.pay_for_order is not None:
        orders = calc_orders_per_1000_rub(conv_views_to_orders, keyword.cpm)
        if orders is not None and calc_pay_for_order(orders) is not None:
            return False
    orders = calc_orders_per_1000_rub(conv_views_to_orders, keyword.cpm)
    if orders is None:
        return True
    return calc_pay_for_order(orders) is None


def tier_label_ru(tier: KeywordV3DecisionTier) -> str:
    """Короткая подпись уровня данных для UI."""
    return {
        KeywordV3DecisionTier.FULL: "свои CH+conv",
        KeywordV3DecisionTier.RK_AGGREGATE: "агрегат РК",
        KeywordV3DecisionTier.PEER_MAX: "max conv по РК",
        KeywordV3DecisionTier.NO_CH_MATRIX: "нет матрицы CH",
    }[tier]
