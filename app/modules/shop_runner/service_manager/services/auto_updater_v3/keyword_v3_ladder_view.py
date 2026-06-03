"""SSOT лестницы M/O/C для UI и updater (без импорта ``orchestrator``).

``LadderInputs`` строится один раз на тик / карточку; ``cost_for_mode`` только читает
предрасчёт каталога M/O/C.
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
    predicted_pay_for_order_from_point,
    resolve_effective_state_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    CampaignV3DecisionCache,
    effective_conv_for_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    keyword_pfo_value,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordV3Eligibility,
    can_target_mode,
    min_cpa_operational_via_pay_for_order,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    build_prepared_from_contexts,
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
    campaign_cache: CampaignV3DecisionCache
    campaign_orders_per_cart_7d: float | None = None
    rec_orders_per_view: float | None = None

    @property
    def rk_orders_per_cart(self) -> float | None:
        """Deprecated: используйте ``campaign_orders_per_cart_7d`` (baseline РК для prior/UI)."""
        return self.campaign_orders_per_cart_7d

    def orders_per_cart_for_ctx(self, ctx: KeywordV3Context) -> float | None:
        """SSOT effective ``orders_per_cart`` для CPO V3 на ключе (сглажение к campaign 7d)."""
        from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
            resolve_orders_per_cart_for_cpo,
        )

        return resolve_orders_per_cart_for_cpo(
            campaign_orders_per_cart_7d=self.campaign_orders_per_cart_7d,
            key_orders=ctx.keyword.orders,
            key_carts=ctx.keyword.add_to_cart,
        )

    @classmethod
    def from_contexts(
        cls,
        contexts: list[KeywordV3Context],
        *,
        campaign_orders_per_cart_7d: float | None = None,
        rec_orders_per_view: float | None = None,
        rk_orders_per_cart: float | None = None,
    ) -> LadderInputs:
        """Один проход: prepared + campaign_cache."""
        campaign_opc = (
            campaign_orders_per_cart_7d
            if campaign_orders_per_cart_7d is not None
            else rk_orders_per_cart
        )
        prepared = build_prepared_from_contexts(contexts)
        return cls(
            all_contexts=list(contexts),
            prepared=prepared,
            campaign_cache=CampaignV3DecisionCache.from_contexts(contexts),
            campaign_orders_per_cart_7d=campaign_opc,
            rec_orders_per_view=rec_orders_per_view,
        )



def state_candidates_by_mode_for_ctx(
    ctx: KeywordV3Context,
    ladder_inputs: LadderInputs,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """SSOT: M/O/C ``ModeCandidate`` для ключа на тике (``orders_per_cart_for_ctx``)."""
    opc = ladder_inputs.orders_per_cart_for_ctx(ctx)
    conv = None
    if opc is None or opc <= 0:
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
        orders_per_cart=opc,
    )


def _catalog_for_ctx(
    ctx: KeywordV3Context,
    ladder_inputs: LadderInputs,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """Legacy name; delegates to ``state_candidates_by_mode_for_ctx``."""
    return state_candidates_by_mode_for_ctx(ctx, ladder_inputs)


def _strategy_mode_for_agg(mode: AggressionTargetMode) -> KeywordStrategyMode:
    return KeywordStrategyMode[mode.name] # type: ignore



def _keyword_has_ch_profile(ctx: KeywordV3Context) -> bool:
    return bool(ctx.position_profile)


def operational_cpo_at_keyword_target_place(
    ctx: KeywordV3Context,
    *,
    ladder_inputs: LadderInputs,
) -> float | None:
    """CPO на фактической ``target_place`` ключа (ставка в WB), RK SSOT как в каталоге.

    Для MAX_CPA_GUARD: режим в БД может быть OPTIMUM, а ставка ещё на дорогой позиции
    (до sync), хотя ``build_mode_candidates`` уже выбрал дешёвую точку для O/C.
    """
    place = ctx.keyword.target_place
    if place is None or int(place) <= 0:
        return None
    profile = ctx.position_profile
    if not profile:
        return None
    row = next((p for p in profile if int(p.position) == int(place)), None)
    if row is None:
        return None
    opc = ladder_inputs.orders_per_cart_for_ctx(ctx)
    conv: float | None = None
    if opc is None or opc <= 0:
        conv = effective_conv_for_v3(
            ctx,
            ladder_inputs.all_contexts,
            campaign_cache=ladder_inputs.campaign_cache,
        )
        if conv is None:
            conv = ctx.keyword.conv_views_to_orders
    cpo = predicted_pay_for_order_from_point(
        row,
        conv_views_to_orders=conv,
        orders_per_cart=opc if opc is not None and opc > 0 else None,
    )
    if cpo is None or not math.isfinite(float(cpo)):
        return None
    value = float(cpo)
    return value if value > 0 else None


_NO_CH_LADDER_REASON = "no_ch_min_only"
_COLLAPSED_CH_LADDER_REASON = "no_valid_ch_ladder"


def _min_pay_for_order_oc_reason(
    ctx: KeywordV3Context,
    eligibility: KeywordV3Eligibility | None,
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> str:
    """Reason для недоступных O/C при operational MIN через pay_for_order."""
    if eligibility is not None and min_cpa_operational_via_pay_for_order(
        ctx, eligibility, catalog
    ):
        if _keyword_has_ch_profile(ctx):
            return _COLLAPSED_CH_LADDER_REASON
        return _NO_CH_LADDER_REASON
    return _NO_CH_LADDER_REASON



def cost_for_mode(
    ctx: KeywordV3Context,
    to_mode: KeywordStrategyMode,
    *,
    ladder_inputs: LadderInputs,
    eligibility: KeywordV3Eligibility | None = None,
) -> tuple[float, bool]:
    """Себестоимость target mode: PFO → ``pay_for_order``; FULL → profile CPO; иначе ``inf``."""
    target = AggressionTargetMode[to_mode.name]
    catalog = _catalog_for_ctx(ctx, ladder_inputs)

    if eligibility is not None and min_cpa_operational_via_pay_for_order(
        ctx, eligibility, catalog
    ):
        if to_mode == KeywordStrategyMode.MIN_CPA:
            pfo_cost = keyword_pfo_value(ctx.keyword)
            if pfo_cost is not None:
                return float(pfo_cost), False
        return float("inf"), False
    if eligibility is not None:
        if not eligibility.participates_in_ladder or not can_target_mode(
            eligibility, to_mode
        ):
            return float("inf"), False

    if not _keyword_has_ch_profile(ctx):
        return float("inf"), False

    mc = catalog.get(target)  # type: ignore
    profile_cost: float | None = None
    if mc is not None and mc.is_valid and mc.predicted_cpa is not None:
        profile_cost = float(mc.predicted_cpa)
    return resolve_effective_state_cost(profile_cost=profile_cost)


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

    if eligibility is not None and min_cpa_operational_via_pay_for_order(
        ctx, eligibility, catalog
    ):
        if target == AggressionTargetMode.MIN_CPA:
            pfo_cost = keyword_pfo_value(ctx.keyword)
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
            reason=_min_pay_for_order_oc_reason(ctx, eligibility, catalog),
            candidate=mc,
        )
    if eligibility is not None:
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
        return LadderStageResult(
            mode=target,
            is_valid=False,
            cost=None,
            source=LadderCostSource.NONE,
            conv_imputed=conv_imputed,
            reason=_NO_CH_LADDER_REASON,
            candidate=mc,
        )

    profile_cost: float | None = None
    if mc is not None and mc.is_valid and mc.predicted_cpa is not None:
        profile_cost = float(mc.predicted_cpa)
    cost_val, cost_imputed = resolve_effective_state_cost(profile_cost=profile_cost)
    if profile_cost is not None:
        source = LadderCostSource.PROFILE
        is_valid = True
        display_cost: float | None = profile_cost
    else:
        source = LadderCostSource.NONE
        is_valid = False
        display_cost = None

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
    """Преобразовать ``LadderView`` в ``ModeCandidate`` для Telegram UI.

    ``stage.reason`` (например ``no_valid_ch_ladder``) всегда попадает в
    ``invalid_reason``, даже если в каталоге уже есть ``ModeCandidate``.
    """
    out: dict[AggressionTargetMode, ModeCandidate] = {}
    for mode, stage in view.stages.items():
        base = stage.candidate
        updates: dict[str, object] = {
            "is_valid": stage.is_valid,
            "predicted_cpa": stage.cost,
        }
        if (
            stage.source == LadderCostSource.PAY_FOR_ORDER
            and mode == AggressionTargetMode.MIN_CPA
            and stage.is_valid
        ):
            updates["position"] = 0
            updates["bid"] = None
        if stage.reason is not None:
            updates["invalid_reason"] = stage.reason
        elif stage.is_valid:
            updates["invalid_reason"] = None
        if base is not None:
            out[mode] = base.model_copy(update=updates)
            continue
        position = updates.get("position")
        bid = updates.get("bid")
        out[mode] = ModeCandidate(
            mode=mode,
            is_valid=stage.is_valid,
            predicted_cpa=stage.cost,
            position=int(position) if position is not None else None, # type: ignore
            bid=float(bid) if bid is not None else None, # type: ignore
            invalid_reason=stage.reason,
        )
    return out
