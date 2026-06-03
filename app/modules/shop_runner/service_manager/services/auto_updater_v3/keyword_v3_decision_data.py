"""Уровни данных V3 по ключу: FULL (CH+своя conv), иначе tier через ``keyword_v3_eligibility``.

``NO_CH_MATRIX`` / ``NO_CONV`` — decision tier для диагностики; продуктовый tier — FULL/PFO/NO DATA.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
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
    """Источник conv для диагностики (не путать с ``KeywordDataTier``)."""

    FULL = "full"
    NO_CH_MATRIX = "no_ch_matrix"
    NO_CONV = "no_conv"


_N_STATE_TIERS: frozenset[KeywordV3DecisionTier] = frozenset(
    {
        KeywordV3DecisionTier.NO_CH_MATRIX,
        KeywordV3DecisionTier.NO_CONV,
    }
)


@dataclass(frozen=True, slots=True)
class CampaignV3DecisionCache:
    """Заглушка для совместимости call sites (агрегат РК удалён)."""

    @classmethod
    def from_contexts(cls, contexts: list["KeywordV3Context"]) -> CampaignV3DecisionCache:
        return cls()


@dataclass(frozen=True, slots=True)
class KeywordV3Decision:
    """Решение по данным ключа для одного тика V3."""

    tier: KeywordV3DecisionTier
    effective_conv_views_to_orders: float | None
    has_ch_position_profile: bool

    @property
    def imputed(self) -> bool:
        """Imputed conv удалён — всегда ``False``."""
        return False

    @property
    def in_ladder_pool(self) -> bool:
        """Участвует в ladder-фазах только FULL с своей conv."""
        return (
            self.has_ch_position_profile
            and self.tier == KeywordV3DecisionTier.FULL
            and self.effective_conv_views_to_orders is not None
            and self.effective_conv_views_to_orders > 0
        )


def _keyword_has_own_conv(keyword: CalculatedKeyword) -> bool:
    stat = keyword.cluster_stat
    return stat.views > 0 and keyword.conv_views_to_orders > 0


def rating_aligned_cpm(keyword: CalculatedKeyword) -> float | None:
    """CPM как в рейтинге/карточке: set_bid → stats → cluster_stat, без bid_log/api."""
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


def keyword_has_v2_cpo(keyword: CalculatedKeyword) -> bool:
    """Есть **свой** V2 CPO: conv ключа + rating CPM."""
    return resolve_keyword_v2_pay_for_order_cost(keyword) is not None


def resolve_keyword_v2_pay_for_order_cost(keyword: CalculatedKeyword) -> float | None:
    """Себестоимость V2: только conv ключа + rating CPM (без worst/imputed)."""
    conv = keyword.conv_views_to_orders
    if conv is None or conv <= 0:
        return None
    cpm = rating_aligned_cpm(keyword)
    if cpm is None or cpm <= 0:
        return None
    orders = calc_orders_per_1000_rub(float(conv), cpm)
    if orders is None:
        return None
    result = calc_pay_for_order(orders)
    return None if result is None else float(result)


def resolve_keyword_v3_decision(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
    *,
    campaign_cache: CampaignV3DecisionCache | None = None,
) -> KeywordV3Decision:
    """Цепочка: CH+своя conv → FULL; иначе NO_CH / NO_CONV без импутации."""
    _ = contexts, campaign_cache
    profile = ctx.position_profile
    has_ch = bool(profile)
    if not has_ch:
        conv = ctx.keyword.conv_views_to_orders
        eff_conv = float(conv) if conv is not None and conv > 0 else None
        return KeywordV3Decision(
            tier=KeywordV3DecisionTier.NO_CH_MATRIX,
            effective_conv_views_to_orders=eff_conv,
            has_ch_position_profile=False,
        )

    if _keyword_has_own_conv(ctx.keyword):
        return KeywordV3Decision(
            tier=KeywordV3DecisionTier.FULL,
            effective_conv_views_to_orders=float(ctx.keyword.conv_views_to_orders),
            has_ch_position_profile=True,
        )

    return KeywordV3Decision(
        tier=KeywordV3DecisionTier.NO_CONV,
        effective_conv_views_to_orders=None,
        has_ch_position_profile=True,
    )


def effective_conv_for_v3(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
    *,
    campaign_cache: CampaignV3DecisionCache | None = None,
) -> float | None:
    """Conv для ``build_mode_candidates`` — только FULL (своя conv)."""
    decision = resolve_keyword_v3_decision(
        ctx, contexts, campaign_cache=campaign_cache
    )
    if decision.tier != KeywordV3DecisionTier.FULL:
        return None
    return decision.effective_conv_views_to_orders


def keyword_lacks_v3_decision_data(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
) -> bool:
    """Keyword-level NO DATA tier."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
        resolve_keyword_v3_eligibility,
    )

    return (
        resolve_keyword_v3_eligibility(ctx, contexts).data_tier
        == KeywordDataTier.KEYWORD_NO_DATA
    )


def keyword_v2_pay_for_order_unavailable_with_conv(
    keyword: CalculatedKeyword,
    *,
    conv_views_to_orders: float | None,
) -> bool:
    """«Нет своего V2 CPO» для диагностики."""
    if conv_views_to_orders is None or conv_views_to_orders <= 0:
        return True
    return resolve_keyword_v2_pay_for_order_cost(keyword) is None


def tier_label_ru(tier: KeywordV3DecisionTier) -> str:
    """Короткая подпись уровня данных для UI."""
    return {
        KeywordV3DecisionTier.FULL: "свои CH+conv",
        KeywordV3DecisionTier.NO_CH_MATRIX: "нет матрицы CH",
        KeywordV3DecisionTier.NO_CONV: "нет своей conv",
    }[tier]
