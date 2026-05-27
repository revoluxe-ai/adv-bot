"""RolloutPlanner для non-shelf: pooled выбор UP с ограничением по aggressiveness.

Вне полочной фазы ``UNDERPERFORM`` использует единый планировщик переходов вверх:
из всех ``to_mode > current`` выбирается самый дешевый кандидат после фильтра
по максимальному target-состоянию (``aggressiveness`` 1/2/3).

При ``SalesStates.OVERSPEND`` (факт кампании выше ``max_pay_for_order``): сначала
``plan_overspend_force_off_over_max`` — все активные ключи с ``pay_for_order > max`` сразу в OFF;
если таких нет — один шаг ``plan_rollout_down_one``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    V3Action,
    V3ActionType,
    V3SelectionLog,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
    step_down,
    step_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    SelectionPolicy,
    build_worst_per_state_costs,
    collect_transition_candidates,
    passes_rec_gate_for_up,
    plan_one_up_by_policy,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

logger = logging.getLogger(__name__)

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2


def _hard_status_allows_up(hard_status: int) -> bool:
    """UP (ladder): авто (1) и белый список (2)."""
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


# If more than this many OFF→MIN candidates exist, stay on strict MIN-first (level 2).
_LEVEL2_OFF_STRICT_ABOVE = 3
# Level 3: allow mixed pool unless this many OFF→MIN remain.
_LEVEL3_OFF_STRICT_ABOVE = 8


def _conv_sort_key(ctx: KeywordV3Context) -> float:
    return float(ctx.keyword.conv_views_to_orders)


def _down_sort_key(ctx: KeywordV3Context) -> tuple[float, float]:
    pfo = ctx.keyword.pay_for_order
    pay = float("-inf") if pfo is None else float(pfo)
    rating = ctx.keyword.rating or 0.0
    return (pay, rating)


def _active_entries(prepared: PreparedList) -> PreparedList:
    return [(c, m) for c, m in prepared if m != KeywordStrategyMode.OFF]


def _off_entries(prepared: PreparedList) -> PreparedList:
    return [(c, m) for c, m in prepared if m == KeywordStrategyMode.OFF]


def _strict_min_first(aggr: V3RolloutAggressiveness, off_with_min_count: int) -> bool:
    if aggr == V3RolloutAggressiveness.MIN:
        return True
    if aggr == V3RolloutAggressiveness.MID:
        return off_with_min_count > _LEVEL2_OFF_STRICT_ABOVE
    return off_with_min_count > _LEVEL3_OFF_STRICT_ABOVE


def _up_move_kind(
    mode: KeywordStrategyMode,
) -> str | None:
    if mode == KeywordStrategyMode.OFF:
        return "off_to_min"
    if mode == KeywordStrategyMode.MIN_CPA:
        return "min_to_opt"
    if mode == KeywordStrategyMode.OPTIMUM:
        return "opt_to_max"
    return None


def try_valid_rollout_up(
    ctx: KeywordV3Context,
    mode: KeywordStrategyMode,
) -> V3Action | None:
    if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
        return None

    if mode == KeywordStrategyMode.OFF:
        cand = build_mode_candidates(
            profile=ctx.position_profile,
            keyword_text=ctx.keyword.text,
        )
        min_c = cand.get(AggressionTargetMode.MIN_CPA)
        if min_c is None or not min_c.is_valid:
            return None
        return V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=ctx.keyword.keyword_setting_original_id,
            reason="rollout_off_to_min",
        )

    if mode == KeywordStrategyMode.MAX_CONVERSION:
        return None
    nxt = step_up(mode)
    if nxt is None:
        return None
    cand = build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
    )
    try:
        target = AggressionTargetMode[nxt.name]
    except KeyError:
        return None
    mc = cand.get(target)
    if mc is None or not mc.is_valid:
        logger.debug(
            "v3 skip UP kw=%s: invalid candidate for %s",
            ctx.keyword.text,
            target,
        )
        return None
    return V3Action(
        action=V3ActionType.UP,
        keyword_setting_id=ctx.keyword.keyword_setting_original_id,
        reason="rollout_step_up",
    )


def plan_rollout_underperform_one(
    prepared: PreparedList,
    aggressiveness: V3RolloutAggressiveness,
) -> list[V3Action]:
    """Single UP per cycle with pooled ranking and aggressiveness target cap."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
        ShelfClickMode,
    )

    policy = SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=aggressiveness,
    )
    return plan_one_up_by_policy(prepared, policy=policy)


def _keyword_exceeds_max_pfo(
    ctx: KeywordV3Context,
    *,
    max_pay_for_order: float,
) -> bool:
    """True, если у ключа известен pay_for_order и он строго выше максимального порога."""
    pfo = ctx.keyword.pay_for_order
    if pfo is None:
        return False
    return float(pfo) > float(max_pay_for_order)


def plan_overspend_force_off_over_max(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
    reason: str = "overspend_max_pfo",
) -> list[V3Action]:
    """Массовый сброс в OFF: активные ключи с себестоимостью выше ``max_pay_for_order``.

    Args:
        prepared: Контексты ключей с текущим ``strategy_mode``.
        max_pay_for_order: Плановый максимальный себес заказа (руб.).
        reason: Код причины в логах/applier.

    Returns:
        Список ``FORCE_OFF`` (может быть пустым).
    """
    actions: list[V3Action] = []
    for ctx, mode in prepared:
        if mode == KeywordStrategyMode.OFF:
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if not _keyword_exceeds_max_pfo(ctx, max_pay_for_order=max_pay_for_order):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        actions.append(
            V3Action(
                action=V3ActionType.FORCE_OFF,
                keyword_setting_id=ks_id,
                reason=reason,
            )
        )
    return actions


def plan_overspend_actions(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
) -> list[V3Action]:
    """OVERSPEND: массовый OFF по ключам выше max, иначе один DOWN."""
    forced = plan_overspend_force_off_over_max(
        prepared, max_pay_for_order=max_pay_for_order
    )
    if forced:
        return forced
    return plan_rollout_down_one(prepared, reason="overspend")


def plan_rollout_down_one(
    prepared: PreparedList,
    *,
    reason: str,
) -> list[V3Action]:
    """Single DOWN: highest pay_for_order first (expensive → cheap)."""
    actives = _active_entries(prepared)
    actives.sort(key=lambda t: _down_sort_key(t[0]), reverse=True)
    for ctx, mode in actives:
        if int(ctx.keyword.hard_status) != _HARD_STATUS_WHITE_LIST:
            continue
        if mode == KeywordStrategyMode.OFF:
            continue
        nxt = step_down(mode)
        if nxt is None:
            continue
        cand = build_mode_candidates(
            profile=ctx.position_profile,
            keyword_text=ctx.keyword.text,
        )
        if nxt != KeywordStrategyMode.OFF:
            try:
                target = AggressionTargetMode[nxt.name]
            except KeyError:
                continue
            mc = cand.get(target)
            if mc is None or not mc.is_valid:
                logger.debug(
                    "v3 skip DOWN kw=%s: invalid candidate for %s",
                    ctx.keyword.text,
                    target,
                )
                continue
        return [
            V3Action(
                action=V3ActionType.DOWN,
                keyword_setting_id=ctx.keyword.keyword_setting_original_id,
                reason=reason,
            )
        ]
    return [V3Action(action=V3ActionType.DO_NOTHING, reason=f"{reason}_no_down")]


@dataclass(frozen=True)
class _StateView:
    """Проекция состояния с расчётной стоимостью для rebalance-прохода."""

    ks_id: int
    strategy_mode: KeywordStrategyMode
    cost: float
    from_mode: KeywordStrategyMode
    to_mode: KeywordStrategyMode
    imputed: bool


def compute_resolve_cost_threshold(plan: PlanData, fact: FactData) -> float:
    """Вернуть текущий resolve порог: target при выполнении плана, иначе max."""
    if float(fact.predict_orders) >= float(plan.orders):
        return float(plan.target_pay_for_order)
    return float(plan.max_pay_for_order)


def is_resolve_valid(plan: PlanData, resolve: float) -> bool:
    """Проверить, что порог пригоден для state-решений."""
    return float(plan.max_pay_for_order) > 0 and float(resolve) > 0


def _resolve_state_cost_for_mode(
    *,
    ctx: KeywordV3Context,
    to_mode: KeywordStrategyMode,
    worst_costs: dict[AggressionTargetMode, float],
) -> tuple[float, bool]:
    catalog = build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
    )
    target = AggressionTargetMode[to_mode.name]
    mc = catalog.get(target)
    if mc is not None and mc.is_valid and mc.predicted_cpa is not None:
        return float(mc.predicted_cpa), False
    worst = worst_costs.get(target)
    if worst is not None:
        return float(worst), True
    return float("inf"), False


def _iter_upper_modes(current: KeywordStrategyMode) -> list[KeywordStrategyMode]:
    out: list[KeywordStrategyMode] = []
    cursor = current
    while True:
        nxt = step_up(cursor)
        if nxt is None:
            return out
        out.append(nxt)
        cursor = nxt


def _iter_one_step(current: KeywordStrategyMode) -> list[KeywordStrategyMode]:
    nxt = step_up(current)
    return [] if nxt is None else [nxt]


def build_worst_costs(prepared: PreparedList) -> dict[AggressionTargetMode, float]:
    """Адаптер для имьютации worst-per-state стоимости."""
    return build_worst_per_state_costs(prepared)


def plan_mass_cheap_promotion(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    worst_costs: dict[AggressionTargetMode, float],
) -> list[V3Action]:
    """M1: для каждого ключа поднять до highest passing state из класса A."""
    actions: list[V3Action] = []
    for ctx, current_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        ):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        best_mode: KeywordStrategyMode | None = None
        best_cost: float | None = None
        best_imputed = False
        for to_mode in _iter_upper_modes(current_mode):
            if mode_level(to_mode) > mode_level(policy.max_target_mode):
                continue
            cost, imputed = _resolve_state_cost_for_mode(
                ctx=ctx,
                to_mode=to_mode,
                worst_costs=worst_costs,
            )
            if cost == float("inf") or cost > resolve:
                continue
            if best_mode is None or mode_level(to_mode) > mode_level(best_mode):
                best_mode = to_mode
                best_cost = cost
                best_imputed = imputed
        if best_mode is None:
            continue
        actions.append(
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=ks_id,
                target_strategy_mode=best_mode,
                reason="m1_mass_cheap_promotion",
                selection_log=V3SelectionLog(
                    mechanism="m1",
                    state_cost=best_cost,
                    pay_for_order=float(ctx.keyword.pay_for_order or 0.0),
                    from_mode=current_mode.name,
                    to_mode=best_mode.name,
                    move_kind=f"{current_mode.name.lower()}_to_{best_mode.name.lower()}",
                    imputed=best_imputed,
                ),
            )
        )
    return actions


def _collect_active_expensive(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    worst_costs: dict[AggressionTargetMode, float],
    overrides: dict[int, KeywordStrategyMode] | None = None,
) -> list[_StateView]:
    overrides = overrides or {}
    out: list[_StateView] = []
    for ctx, stored_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        ):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        current = overrides.get(ks_id, stored_mode)
        if current == KeywordStrategyMode.OFF:
            continue
        if mode_level(current) > mode_level(policy.max_target_mode):
            continue
        cost, imputed = _resolve_state_cost_for_mode(
            ctx=ctx,
            to_mode=current,
            worst_costs=worst_costs,
        )
        if cost == float("inf") or cost <= resolve:
            continue
        out.append(
            _StateView(
                ks_id=ks_id,
                strategy_mode=current,
                cost=cost,
                from_mode=current,
                to_mode=current,
                imputed=imputed,
            )
        )
    out.sort(key=lambda x: x.cost, reverse=True)
    return out


def _collect_potential_expensive(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    worst_costs: dict[AggressionTargetMode, float],
    overrides: dict[int, KeywordStrategyMode] | None = None,
) -> list[_StateView]:
    overrides = overrides or {}
    out: list[_StateView] = []
    for ctx, stored_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if not passes_rec_gate_for_up(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        ):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        current = overrides.get(ks_id, stored_mode)
        for to_mode in _iter_one_step(current):
            if mode_level(to_mode) > mode_level(policy.max_target_mode):
                continue
            cost, imputed = _resolve_state_cost_for_mode(
                ctx=ctx,
                to_mode=to_mode,
                worst_costs=worst_costs,
            )
            if cost == float("inf") or cost <= resolve:
                continue
            out.append(
                _StateView(
                    ks_id=ks_id,
                    strategy_mode=to_mode,
                    cost=cost,
                    from_mode=current,
                    to_mode=to_mode,
                    imputed=imputed,
                )
            )
    out.sort(key=lambda x: x.cost)
    return out


def plan_state_rebalance(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    worst_costs: dict[AggressionTargetMode, float],
) -> list[V3Action]:
    """M2: итеративно убрать разрыв max(active_B) > min(potential_B)."""
    overrides: dict[int, KeywordStrategyMode] = {}
    down_actions: list[V3Action] = []
    up_actions: list[V3Action] = []
    budget = 0
    for _ in range(50):
        active_expensive = _collect_active_expensive(
            prepared,
            resolve=resolve,
            policy=policy,
            worst_costs=worst_costs,
            overrides=overrides,
        )
        potential_expensive = _collect_potential_expensive(
            prepared,
            resolve=resolve,
            policy=policy,
            worst_costs=worst_costs,
            overrides=overrides,
        )
        if not active_expensive or not potential_expensive:
            break
        worst_active = active_expensive[0]
        cheapest_potential = potential_expensive[0]
        if worst_active.cost <= cheapest_potential.cost:
            break
        nxt = step_down(worst_active.strategy_mode)
        if nxt is None:
            break
        overrides[worst_active.ks_id] = nxt
        budget += 1
        if nxt == KeywordStrategyMode.OFF:
            down_actions.append(
                V3Action(
                    action=V3ActionType.FORCE_OFF,
                    keyword_setting_id=worst_active.ks_id,
                    reason="m2_rebalance_force_off",
                )
            )
        else:
            down_actions.append(
                V3Action(
                    action=V3ActionType.DOWN,
                    keyword_setting_id=worst_active.ks_id,
                    target_strategy_mode=nxt,
                    reason="m2_rebalance_down",
                )
            )
    for _ in range(budget):
        potential_expensive = _collect_potential_expensive(
            prepared,
            resolve=resolve,
            policy=policy,
            worst_costs=worst_costs,
            overrides=overrides,
        )
        if not potential_expensive:
            break
        target = potential_expensive[0]
        overrides[target.ks_id] = target.to_mode
        up_actions.append(
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=target.ks_id,
                target_strategy_mode=target.to_mode,
                reason="m2_rebalance_up",
            )
        )
    return down_actions + up_actions


def plan_headroom_plus_one(
    prepared: PreparedList,
    *,
    resolve: float,
    fact_pay_for_order: float | None,
    policy: SelectionPolicy,
) -> list[V3Action]:
    """M3: один UP на cheapest potential если есть headroom."""
    if fact_pay_for_order is None or fact_pay_for_order >= 0.9 * resolve:
        return []
    candidates = collect_transition_candidates(prepared, policy=policy)
    one_step = [
        c for c in candidates if mode_level(c.to_mode) == mode_level(c.from_mode) + 1
    ]
    if not one_step:
        return []
    best = min(one_step, key=lambda c: c.state_cost)
    return [
        V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=best.keyword_setting_id,
            target_strategy_mode=best.to_mode,
            reason="m3_headroom_plus_one",
            selection_log=V3SelectionLog(
                mechanism="m3",
                state_cost=best.state_cost,
                pay_for_order=best.pay_for_order,
                from_mode=best.from_mode.name,
                to_mode=best.to_mode.name,
                move_kind=best.move_kind.value,
                imputed=best.imputed,
            ),
        )
    ]


def merge_and_dedup_actions(
    m1_actions: list[V3Action],
    m2_actions: list[V3Action],
    m3_actions: list[V3Action],
) -> list[V3Action]:
    """Слить действия с приоритетом M2 > M1 > M3 по keyword_setting_id."""
    merged: dict[int, V3Action] = {}
    for action in m3_actions + m1_actions + m2_actions:
        if action.action == V3ActionType.DO_NOTHING:
            continue
        if action.keyword_setting_id is None:
            continue
        merged[action.keyword_setting_id] = action
    return list(merged.values())
