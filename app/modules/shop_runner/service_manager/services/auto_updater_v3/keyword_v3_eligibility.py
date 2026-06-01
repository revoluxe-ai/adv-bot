"""Keyword-level data tier и eligibility для V3 (отдельно от ``CampaignMode``).

``allowed_modes`` — рабочие UP/realloc target modes **без OFF**. ``OFF`` допустим только
как результат DOWN/FORCE_OFF, не как UP-кандидат (см. ``can_target_mode``).

Tier ``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV``: нет CH-матрицы, но есть свой V2 CPO на ключе.
Границы UP/trim — ``keyword.pay_for_order`` (UI), не imputed conv и не
``resolve_keyword_v2_pay_for_order_cost``. Tier ``KEYWORD_PESSIMISTIC_FALLBACK``: CH есть,
conv импутирована с РК — лестница через ``effective_conv_for_v3``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
    _keyword_has_own_conv,
    effective_conv_for_v3,
    keyword_has_v2_cpo,
    resolve_keyword_v3_decision,
    resolve_no_ch_operational_pay_for_order_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

FallbackKind = Literal["none", "pessimistic", "v2_cpo"]

_FULL_LADDER_TARGET_MODES: frozenset[KeywordStrategyMode] = frozenset(
    {
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    }
)
_MIN_ONLY_TARGET_MODES: frozenset[KeywordStrategyMode] = frozenset(
    {KeywordStrategyMode.MIN_CPA}
)
_EMPTY_TARGET_MODES: frozenset[KeywordStrategyMode] = frozenset()


class KeywordDataTier(str, Enum):
    """Keyword-level tier данных (не campaign state).

    ``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV`` — нет CH bid profile, свой V2 CPO на ключе;
    MIN-only; границы UP/trim — ``keyword.pay_for_order`` (как в UI).
    """

    KEYWORD_FULL = "keyword_full"
    KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV = "keyword_no_ch_profile_with_own_conv"
    KEYWORD_PESSIMISTIC_FALLBACK = "keyword_pessimistic_fallback"
    KEYWORD_INVALID = "keyword_invalid"


@dataclass(frozen=True, slots=True)
class KeywordV3Eligibility:
    """Eligibility ключа для ladder-фаз и bootstrap."""

    data_tier: KeywordDataTier
    allowed_modes: frozenset[KeywordStrategyMode]
    max_allowed_mode: KeywordStrategyMode
    participates_in_ladder: bool
    target_place_fallback_zero: bool
    imputed: bool
    fallback_kind: FallbackKind | None
    decision_tier: KeywordV3DecisionTier


def can_target_mode(
    eligibility: KeywordV3Eligibility,
    mode: KeywordStrategyMode,
) -> bool:
    """UP/realloc target: ``OFF`` всегда False; иначе ``mode in allowed_modes``."""
    if mode == KeywordStrategyMode.OFF:
        return False
    return mode in eligibility.allowed_modes


def collapsed_ch_ladder_with_pay_for_order(
    ctx: "KeywordV3Context",
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> bool:
    """CH raw есть, usable M/O/C нет, operational cost — ``keyword.pay_for_order``.

    Stored mode остаётся ``MIN_CPA``; отличие — ``target_place=0`` и ``PAY_FOR_ORDER`` в ladder.
    """
    if not ctx.position_profile:
        return False
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        missing_target_matrix_from_catalog,
    )

    if not missing_target_matrix_from_catalog(catalog):
        return False
    return resolve_no_ch_operational_pay_for_order_cost(ctx.keyword) is not None


def min_cpa_operational_via_pay_for_order(
    ctx: "KeywordV3Context",
    eligibility: KeywordV3Eligibility | None,
    catalog: dict[AggressionTargetMode, ModeCandidate] | None = None,
) -> bool:
    """MIN через ``pay_for_order``: NO CH tier или collapsed CH ladder + own PFO."""
    if (
        eligibility is not None
        and eligibility.data_tier == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV
    ):
        return True
    if catalog is None:
        return False
    return collapsed_ch_ladder_with_pay_for_order(ctx, catalog)


def clamp_target_mode(
    eligibility: KeywordV3Eligibility,
    mode: KeywordStrategyMode,
) -> KeywordStrategyMode:
    """Ограничить целевой режим ``allowed_modes`` и ``max_allowed_mode``."""
    if not eligibility.allowed_modes:
        return KeywordStrategyMode.OFF
    if not can_target_mode(eligibility, mode):
        return eligibility.max_allowed_mode
    if mode_level(mode) > mode_level(eligibility.max_allowed_mode):
        return eligibility.max_allowed_mode
    return mode


def _mode_catalog_for_eligibility(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
    campaign_cache: "CampaignV3DecisionCache",
) -> dict[AggressionTargetMode, ModeCandidate]:
    """Каталог M/O/C для предиката collapsed CH (как на тике ladder)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
        build_mode_candidates,
    )
    from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
        resolve_orders_per_cart_for_cpo,
    )

    opc = resolve_orders_per_cart_for_cpo(
        campaign_orders_per_cart_7d=None,
        key_orders=ctx.keyword.orders,
        key_carts=ctx.keyword.add_to_cart,
    )
    conv: float | None = None
    if opc is None or opc <= 0:
        conv = effective_conv_for_v3(
            ctx, contexts, campaign_cache=campaign_cache
        )
        if conv is None:
            conv = ctx.keyword.conv_views_to_orders
    return build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
        conv_views_to_orders=conv,
        orders_per_cart=opc,
    )


def _apply_min_only_pay_for_order_override(
    base: KeywordV3Eligibility,
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
    campaign_cache: "CampaignV3DecisionCache",
) -> KeywordV3Eligibility:
    """Collapsed CH + pay_for_order: MIN-only и ``target_place=0``, ``data_tier`` без смены."""
    catalog = _mode_catalog_for_eligibility(ctx, contexts, campaign_cache)
    if not collapsed_ch_ladder_with_pay_for_order(ctx, catalog):
        return base
    return KeywordV3Eligibility(
        data_tier=base.data_tier,
        allowed_modes=_MIN_ONLY_TARGET_MODES,
        max_allowed_mode=KeywordStrategyMode.MIN_CPA,
        participates_in_ladder=True,
        target_place_fallback_zero=True,
        imputed=base.imputed,
        fallback_kind=base.fallback_kind,
        decision_tier=base.decision_tier,
    )


def resolve_keyword_v3_eligibility(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
    *,
    campaign_cache: "CampaignV3DecisionCache | None" = None,
) -> KeywordV3Eligibility:
    """Свести conv/CH decision к продуктовому ``KeywordDataTier``.

    NO CH + ``keyword_has_v2_cpo`` → MIN-only, ``target_place_fallback_zero=True``.
    CH + imputed conv → полная лестница с ``fallback_kind="pessimistic"`` (не V2 CPO path).

    Args:
        campaign_cache: предрасчёт агрегата РК (см. ``CampaignV3DecisionCache``).
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache as _CampaignV3DecisionCache,
    )

    cache = campaign_cache or _CampaignV3DecisionCache.from_contexts(contexts)
    decision = resolve_keyword_v3_decision(ctx, contexts, campaign_cache=cache)
    has_ch = decision.has_ch_position_profile
    eff = decision.effective_conv_views_to_orders
    keyword = ctx.keyword

    def _with_collapsed_override(base: KeywordV3Eligibility) -> KeywordV3Eligibility:
        return _apply_min_only_pay_for_order_override(base, ctx, contexts, cache)

    if not has_ch:
        if keyword_has_v2_cpo(keyword):
            return KeywordV3Eligibility(
                data_tier=KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV,
                allowed_modes=_MIN_ONLY_TARGET_MODES,
                max_allowed_mode=KeywordStrategyMode.MIN_CPA,
                participates_in_ladder=True,
                target_place_fallback_zero=True,
                imputed=False,
                fallback_kind="none" if _keyword_has_own_conv(keyword) else "v2_cpo",
                decision_tier=decision.tier,
            )
        return _invalid_eligibility(decision)

    if decision.tier == KeywordV3DecisionTier.FULL:
        return _with_collapsed_override(
            KeywordV3Eligibility(
                data_tier=KeywordDataTier.KEYWORD_FULL,
                allowed_modes=_FULL_LADDER_TARGET_MODES,
                max_allowed_mode=KeywordStrategyMode.MAX_CONVERSION,
                participates_in_ladder=True,
                target_place_fallback_zero=False,
                imputed=False,
                fallback_kind="none",
                decision_tier=decision.tier,
            )
        )

    if decision.tier in (
        KeywordV3DecisionTier.RK_AGGREGATE,
        KeywordV3DecisionTier.PEER_MAX,
    ):
        if eff is None or eff <= 0:
            return _invalid_eligibility(decision)
        return _with_collapsed_override(
            KeywordV3Eligibility(
                data_tier=KeywordDataTier.KEYWORD_PESSIMISTIC_FALLBACK,
                allowed_modes=_FULL_LADDER_TARGET_MODES,
                max_allowed_mode=KeywordStrategyMode.MAX_CONVERSION,
                participates_in_ladder=True,
                target_place_fallback_zero=False,
                imputed=True,
                fallback_kind="pessimistic",
                decision_tier=decision.tier,
            )
        )

    if decision.tier == KeywordV3DecisionTier.NO_CONV:
        # CH есть, conv импутировать нельзя — worst только без own pay_for_order.
        return _with_collapsed_override(
            KeywordV3Eligibility(
                data_tier=KeywordDataTier.KEYWORD_PESSIMISTIC_FALLBACK,
                allowed_modes=_FULL_LADDER_TARGET_MODES,
                max_allowed_mode=KeywordStrategyMode.MAX_CONVERSION,
                participates_in_ladder=True,
                target_place_fallback_zero=False,
                imputed=False,
                fallback_kind="pessimistic",
                decision_tier=decision.tier,
            )
        )

    return _invalid_eligibility(decision)


def _invalid_eligibility(decision: object) -> KeywordV3Eligibility:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        KeywordV3Decision,
    )

    assert isinstance(decision, KeywordV3Decision)
    return KeywordV3Eligibility(
        data_tier=KeywordDataTier.KEYWORD_INVALID,
        allowed_modes=_EMPTY_TARGET_MODES,
        max_allowed_mode=KeywordStrategyMode.OFF,
        participates_in_ladder=False,
        target_place_fallback_zero=False,
        imputed=decision.imputed,
        fallback_kind=None,
        decision_tier=decision.tier,
    )


def build_eligibility_map(
    contexts: list["KeywordV3Context"],
) -> dict[int, KeywordV3Eligibility]:
    """Индекс eligibility по ``keyword_setting_original_id`` (один агрегат РК на тик)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache,
    )

    campaign_cache = CampaignV3DecisionCache.from_contexts(contexts)
    result: dict[int, KeywordV3Eligibility] = {}
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        result[int(ks_id)] = resolve_keyword_v3_eligibility(
            ctx, contexts, campaign_cache=campaign_cache
        )
    return result


def build_target_place_fallback_zero_by_keyword_id(
    contexts: list["KeywordV3Context"],
) -> dict[int, bool]:
    """Map ``ks_id → target_place_fallback_zero`` для sync при ``CAMPAIGN_NORMAL``.

    Один ``CampaignV3DecisionCache`` на вызов (как в ``build_eligibility_map``).
    ``OFF`` не включается: после MAX_CPA_GUARD / FORCE_OFF sync ставит ``None``, не 0.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache,
    )

    campaign_cache = CampaignV3DecisionCache.from_contexts(contexts)
    out: dict[int, bool] = {}
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        elig = resolve_keyword_v3_eligibility(
            ctx, contexts, campaign_cache=campaign_cache
        )
        mode = ctx.keyword.keyword_setting.strategy_mode
        out[int(ks_id)] = (
            elig.target_place_fallback_zero
            and mode != KeywordStrategyMode.OFF
        )
    return out
