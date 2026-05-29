"""Keyword-level data tier и eligibility для V3 (отдельно от ``CampaignMode``).

``allowed_modes`` — рабочие UP/realloc target modes **без OFF**. ``OFF`` допустим только
как результат DOWN/FORCE_OFF, не как UP-кандидат (см. ``can_target_mode``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
    _keyword_has_own_conv,
    keyword_has_v2_cpo,
    resolve_keyword_v3_decision,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)

if TYPE_CHECKING:
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
    """Keyword-level tier данных (не campaign state)."""

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
) -> KeywordV3Eligibility:
    """Свести conv/CH decision к продуктовому ``KeywordDataTier``."""
    decision = resolve_keyword_v3_decision(ctx, contexts)
    has_ch = decision.has_ch_position_profile
    eff = decision.effective_conv_views_to_orders
    keyword = ctx.keyword

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

    if decision.tier in (
        KeywordV3DecisionTier.RK_AGGREGATE,
        KeywordV3DecisionTier.PEER_MAX,
    ):
        if eff is None or eff <= 0:
            return _invalid_eligibility(decision)
        return KeywordV3Eligibility(
            data_tier=KeywordDataTier.KEYWORD_PESSIMISTIC_FALLBACK,
            allowed_modes=_FULL_LADDER_TARGET_MODES,
            max_allowed_mode=KeywordStrategyMode.MAX_CONVERSION,
            participates_in_ladder=True,
            target_place_fallback_zero=False,
            imputed=True,
            fallback_kind="pessimistic",
            decision_tier=decision.tier,
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
    """Индекс eligibility по ``keyword_setting_original_id``."""
    result: dict[int, KeywordV3Eligibility] = {}
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        result[int(ks_id)] = resolve_keyword_v3_eligibility(ctx, contexts)
    return result


def build_target_place_fallback_zero_by_keyword_id(
    contexts: list["KeywordV3Context"],
) -> dict[int, bool]:
    """Map ``ks_id → target_place_fallback_zero`` для sync при ``CAMPAIGN_NORMAL``."""
    out: dict[int, bool] = {}
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        elig = resolve_keyword_v3_eligibility(ctx, contexts)
        out[int(ks_id)] = elig.target_place_fallback_zero
    return out
