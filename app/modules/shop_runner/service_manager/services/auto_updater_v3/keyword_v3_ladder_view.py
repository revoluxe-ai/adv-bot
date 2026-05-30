"""SSOT лестницы M/O/C для UI и updater (без импорта ``orchestrator``).

``LadderInputs`` строится один раз на тик / карточку; ``cost_for_mode`` только читает
предрасчёт (без повторного ``build_worst_per_state_costs``).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
    resolve_effective_state_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    CampaignV3DecisionCache,
    effective_conv_for_v3,
    resolve_no_ch_operational_pay_for_order_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3Eligibility,
    can_target_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    build_prepared_from_contexts,
    build_worst_per_state_costs,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class LadderCostSource(str, Enum):
    """Источник CPO ступени лестницы."""

    PROFILE = "profile"
    WORST = "worst"
    NONE = "none"
    V2_CPO = "v2_cpo"
    PAY_FOR_ORDER = "pay_for_order"


@dataclass(frozen=True, slots=True)
class LadderStageResult:
    """Одна ступень M/O/C: валидность, CPO и происхождение cost."""

    mode: AggressionTargetMode
    is_valid: bool
    cost: float | None
    source: LadderCostSource
    conv_imputed: bool = False
    cost_imputed: bool = False
    reason: str | None = None
    candidate: ModeCandidate | None = None


@dataclass(frozen=True, slots=True)
class LadderView:
    """Полная лестница M/O/C для одного ключа."""

    stages: dict[AggressionTargetMode, LadderStageResult]


@dataclass(frozen=True, slots=True)
class LadderInputs:
    """Предрасчёт на список contexts; переиспользуется всеми ``cost_for_mode`` на тике."""

    all_contexts: list[KeywordV3Context]
    prepared: PreparedList
    worst_costs: dict[AggressionTargetMode, float]
    campaign_cache: CampaignV3DecisionCache
    rk_orders_per_cart: float | None = None

    @classmethod
    def from_contexts(
        cls,
        contexts: list[KeywordV3Context],
        *,
        rk_orders_per_cart: float | None = None,
    ) -> LadderInputs:
        """Один проход: prepared + worst_costs + campaign_cache."""
        prepared = build_prepared_from_contexts(contexts)
        return cls(
            all_contexts=list(contexts),
            prepared=prepared,
            worst_costs=build_worst_per_state_costs(
                prepared, rk_orders_per_cart=rk_orders_per_cart
            ),
            campaign_cache=CampaignV3DecisionCache.from_contexts(contexts),
            rk_orders_per_cart=rk_orders_per_cart,
        )


async def cache_worst_costs_for_adv(
    adv_id: int,
    worst_costs: dict[AggressionTargetMode, float],
) -> None:
    """Записать worst CPO M/O/C в Redis (TTL 10 мин) после расчёта ``LadderInputs``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_worst_costs_cache import (
        V3WorstCostsRedisCache,
    )

    try:
        await V3WorstCostsRedisCache().set_worst_costs(adv_id, worst_costs)
    except Exception:
        logger.exception(
            "v3 worst_costs cache write failed adv_id=%s",
            adv_id,
        )


def _catalog_for_ctx(
    ctx: KeywordV3Context,
    ladder_inputs: LadderInputs,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """Каталог M/O/C: CPO на точке CH × RK корзина→заказ (7 дней)."""
    rk = ladder_inputs.rk_orders_per_cart
    conv = None
    if rk is None or rk <= 0:
        conv = effective_conv_for_v3(
            ctx,
            ladder_inputs.all_contexts,
            campaign_cache=ladder_inputs.campaign_cache,
        )
        if conv is None:
            conv = ctx.keyword.conv_views_to_orders
    return build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
        conv_views_to_orders=conv,
        rk_orders_per_cart=rk,
    )


def _strategy_mode_for_agg(mode: AggressionTargetMode) -> KeywordStrategyMode:
    return KeywordStrategyMode[mode.name]


def has_campaign_worst_costs(worst_costs: dict[AggressionTargetMode, float]) -> bool:
    """Есть хотя бы один per-mode worst (max state_cost) по донорам РК."""
    return any(
        worst_costs.get(mode) is not None
        for mode in (
            AggressionTargetMode.MIN_CPA,
            AggressionTargetMode.OPTIMUM,
            AggressionTargetMode.MAX_CONVERSION,
        )
    )


def _keyword_has_ch_profile(ctx: KeywordV3Context) -> bool:
    return bool(ctx.position_profile)


def _stage_from_campaign_worst(
    target: AggressionTargetMode,
    ladder_inputs: LadderInputs,
    *,
    candidate: ModeCandidate | None,
    conv_imputed: bool = False,
) -> LadderStageResult | None:
    """Ступень только из ``worst_costs`` (нет CH-профиля на ключе)."""
    worst = ladder_inputs.worst_costs.get(target)
    if worst is None:
        return None
    return LadderStageResult(
        mode=target,
        is_valid=True,
        cost=float(worst),
        source=LadderCostSource.WORST,
        conv_imputed=conv_imputed,
        cost_imputed=True,
        candidate=candidate,
    )


def cost_for_mode(
    ctx: KeywordV3Context,
    to_mode: KeywordStrategyMode,
    *,
    ladder_inputs: LadderInputs,
    eligibility: KeywordV3Eligibility | None = None,
) -> tuple[float, bool]:
    """Себестоимость target mode: NO CH → ``pay_for_order``; CH → profile → per-mode worst.

    Args:
        ctx: Контекст ключа.
        to_mode: Целевой режим (M/O/C).
        ladder_inputs: Предрасчёт на тик (обязателен).
        eligibility: Tier/allowed_modes; если ``None`` — без NO_CH-ветки.

    Returns:
        ``(state_cost, cost_imputed)``; ``inf`` если ступень недоступна.
    """
    target = AggressionTargetMode[to_mode.name]

    if eligibility is not None:
        if eligibility.data_tier == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV:
            if to_mode == KeywordStrategyMode.MIN_CPA:
                pfo_cost = resolve_no_ch_operational_pay_for_order_cost(ctx.keyword)
                if pfo_cost is not None:
                    return float(pfo_cost), False
            return float("inf"), False
        if not eligibility.participates_in_ladder or not can_target_mode(
            eligibility, to_mode
        ):
            return float("inf"), False

    if not _keyword_has_ch_profile(ctx):
        worst_stage = _stage_from_campaign_worst(
            target, ladder_inputs, candidate=None
        )
        if worst_stage is not None:
            return float(worst_stage.cost), True

    catalog = _catalog_for_ctx(ctx, ladder_inputs)
    mc = catalog.get(target)
    profile_cost: float | None = None
    if mc is not None and mc.is_valid and mc.predicted_cpa is not None:
        profile_cost = float(mc.predicted_cpa)
    return resolve_effective_state_cost(
        profile_cost=profile_cost,
        worst_cost=ladder_inputs.worst_costs.get(target),
        allow_worst_imputation=True,
    )


def _resolve_stage(
    ctx: KeywordV3Context,
    target: AggressionTargetMode,
    *,
    ladder_inputs: LadderInputs,
    eligibility: KeywordV3Eligibility | None,
) -> LadderStageResult:
    """Одна ступень для UI с ``source`` и ``ModeCandidate``."""
    to_mode = _strategy_mode_for_agg(target)
    catalog = _catalog_for_ctx(ctx, ladder_inputs)
    mc = catalog.get(target)
    eff_conv = effective_conv_for_v3(ctx, ladder_inputs.all_contexts)
    own_conv = ctx.keyword.conv_views_to_orders
    conv_imputed = eff_conv is not None and (own_conv is None or own_conv <= 0)

    if eligibility is not None:
        if eligibility.data_tier == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV:
            if target == AggressionTargetMode.MIN_CPA:
                pfo_cost = resolve_no_ch_operational_pay_for_order_cost(ctx.keyword)
                if pfo_cost is not None:
                    return LadderStageResult(
                        mode=target,
                        is_valid=True,
                        cost=float(pfo_cost),
                        source=LadderCostSource.PAY_FOR_ORDER,
                        conv_imputed=conv_imputed,
                        cost_imputed=False,
                        candidate=mc,
                    )
            return LadderStageResult(
                mode=target,
                is_valid=False,
                cost=None,
                source=LadderCostSource.NONE,
                conv_imputed=conv_imputed,
                reason="no_ch_min_only",
                candidate=mc,
            )
        if not eligibility.participates_in_ladder or not can_target_mode(
            eligibility, to_mode
        ):
            return LadderStageResult(
                mode=target,
                is_valid=False,
                cost=None,
                source=LadderCostSource.NONE,
                conv_imputed=conv_imputed,
                reason="not_allowed_mode",
                candidate=mc,
            )

    if not _keyword_has_ch_profile(ctx):
        worst_only = _stage_from_campaign_worst(
            target, ladder_inputs, candidate=mc, conv_imputed=conv_imputed
        )
        if worst_only is not None:
            return worst_only

    profile_cost: float | None = None
    if mc is not None and mc.is_valid and mc.predicted_cpa is not None:
        profile_cost = float(mc.predicted_cpa)
    cost_val, cost_imputed = resolve_effective_state_cost(
        profile_cost=profile_cost,
        worst_cost=ladder_inputs.worst_costs.get(target),
        allow_worst_imputation=True,
    )
    if profile_cost is not None:
        source = LadderCostSource.PROFILE
        is_valid = True
        display_cost: float | None = profile_cost
    elif cost_imputed and not math.isinf(cost_val):
        source = LadderCostSource.WORST
        is_valid = True
        display_cost = float(cost_val)
    else:
        source = LadderCostSource.NONE
        is_valid = mc.is_valid if mc is not None else False
        display_cost = None if math.isinf(cost_val) else float(cost_val)
        if mc is not None and not mc.is_valid:
            is_valid = False

    return LadderStageResult(
        mode=target,
        is_valid=is_valid,
        cost=display_cost,
        source=source,
        conv_imputed=conv_imputed,
        cost_imputed=cost_imputed,
        reason=mc.invalid_reason if mc is not None and not is_valid else None,
        candidate=mc,
    )


def resolve_ladder_stage_display(
    ctx: KeywordV3Context,
    ladder_inputs: LadderInputs,
    *,
    eligibility: KeywordV3Eligibility | None = None,
) -> LadderView:
    """Полная лестница M/O/C для UI (те же правила, что ``cost_for_mode``)."""
    stages: dict[AggressionTargetMode, LadderStageResult] = {}
    for target in (
        AggressionTargetMode.MIN_CPA,
        AggressionTargetMode.OPTIMUM,
        AggressionTargetMode.MAX_CONVERSION,
    ):
        stages[target] = _resolve_stage(
            ctx,
            target,
            ladder_inputs=ladder_inputs,
            eligibility=eligibility,
        )
    return LadderView(stages=stages)


def ladder_view_to_candidates(view: LadderView) -> dict[AggressionTargetMode, ModeCandidate]:
    """Преобразовать ``LadderView`` в ``ModeCandidate`` для Telegram UI."""
    out: dict[AggressionTargetMode, ModeCandidate] = {}
    for mode, stage in view.stages.items():
        base = stage.candidate
        if base is not None:
            out[mode] = base.model_copy(
                update={
                    "is_valid": stage.is_valid,
                    "predicted_cpa": stage.cost,
                }
            )
        else:
            out[mode] = ModeCandidate(
                mode=mode,
                is_valid=stage.is_valid,
                predicted_cpa=stage.cost,
                invalid_reason=stage.reason,
            )
    return out
