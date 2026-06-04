"""Keyword-level data tier и eligibility для V3: FULL / PFO / NO DATA."""

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
    keyword_has_own_conv,
    resolve_keyword_v3_decision,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    is_keyword_no_data,
    keyword_pfo_value,
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

FallbackKind = Literal["none", "v2_cpo"]

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
    """Keyword-level tier: FULL / PFO / NO DATA."""

    KEYWORD_FULL = "keyword_full"
    KEYWORD_PFO = "keyword_pfo"
    KEYWORD_NO_DATA = "keyword_no_data"

    # Legacy aliases (logs/tests migration)
    KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV = "keyword_pfo"
    KEYWORD_INVALID = "keyword_no_data"
    KEYWORD_PESSIMISTIC_FALLBACK = "keyword_pfo"


@dataclass(frozen=True, slots=True)
class KeywordV3Eligibility:
    """Eligibility ключа для ladder-фаз и preamble."""

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


def min_cpa_operational_via_pay_for_order(
    ctx: "KeywordV3Context",
    eligibility: KeywordV3Eligibility | None,
    catalog: dict[AggressionTargetMode, ModeCandidate] | None = None,
) -> bool:
    """MIN через ``keyword.pay_for_order``: tier PFO или collapsed CH + PFO."""
    _ = catalog
    if eligibility is not None and eligibility.data_tier == KeywordDataTier.KEYWORD_PFO:
        return keyword_pfo_value(ctx.keyword) is not None
    return False


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


def resolve_keyword_v3_eligibility(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
    *,
    campaign_cache: "CampaignV3DecisionCache | None" = None,
    campaign_orders_per_cart_7d: float | None = None,
) -> KeywordV3Eligibility:
    """Свести данные ключа к ``KeywordDataTier`` FULL / PFO / NO DATA."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache as _CampaignV3DecisionCache,
    )

    _ = campaign_orders_per_cart_7d
    cache = campaign_cache or _CampaignV3DecisionCache.from_contexts(contexts)
    decision = resolve_keyword_v3_decision(ctx, contexts, campaign_cache=cache)

    if (
        decision.tier == KeywordV3DecisionTier.FULL
        and decision.effective_conv_views_to_orders is not None
    ):
        return KeywordV3Eligibility(
            data_tier=KeywordDataTier.KEYWORD_FULL,
            allowed_modes=_FULL_LADDER_TARGET_MODES,
            max_allowed_mode=KeywordStrategyMode.MAX_CONVERSION,
            participates_in_ladder=True,
            target_place_fallback_zero=False,
            imputed=False,
            fallback_kind="none",
            decision_tier=decision.tier,
        )

    if is_keyword_no_data(ctx.keyword):
        return KeywordV3Eligibility(
            data_tier=KeywordDataTier.KEYWORD_NO_DATA,
            allowed_modes=_EMPTY_TARGET_MODES,
            max_allowed_mode=KeywordStrategyMode.OFF,
            participates_in_ladder=False,
            target_place_fallback_zero=True,
            imputed=False,
            fallback_kind=None,
            decision_tier=decision.tier,
        )

    return KeywordV3Eligibility(
        data_tier=KeywordDataTier.KEYWORD_PFO,
        allowed_modes=_MIN_ONLY_TARGET_MODES,
        max_allowed_mode=KeywordStrategyMode.MIN_CPA,
        participates_in_ladder=True,
        target_place_fallback_zero=True,
        imputed=False,
        fallback_kind="none" if keyword_has_own_conv(ctx.keyword) else "v2_cpo",
        decision_tier=decision.tier,
    )


def build_eligibility_map(
    contexts: list["KeywordV3Context"],
    *,
    campaign_orders_per_cart_7d: float | None = None,
) -> dict[int, KeywordV3Eligibility]:
    """Индекс eligibility по ``keyword_setting_original_id``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache,
    )

    campaign_cache = CampaignV3DecisionCache.from_contexts(contexts)
    result: dict[int, KeywordV3Eligibility] = {}
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id <= 0:
            continue
        result[ks_id] = resolve_keyword_v3_eligibility(
            ctx,
            contexts,
            campaign_cache=campaign_cache,
            campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        )
    return result


def build_target_place_fallback_zero_by_keyword_id(
    contexts: list["KeywordV3Context"],
    *,
    campaign_orders_per_cart_7d: float | None = None,
) -> dict[int, bool]:
    """Map ``ks_id → target_place_fallback_zero`` для sync при ``CAMPAIGN_NORMAL``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache,
    )

    campaign_cache = CampaignV3DecisionCache.from_contexts(contexts)
    out: dict[int, bool] = {}
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id <= 0:
            continue
        elig = resolve_keyword_v3_eligibility(
            ctx,
            contexts,
            campaign_cache=campaign_cache,
            campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        )
        mode = ctx.keyword.keyword_setting.strategy_mode
        out[int(ks_id)] = (
            elig.target_place_fallback_zero and mode != KeywordStrategyMode.OFF
        )
    return out
