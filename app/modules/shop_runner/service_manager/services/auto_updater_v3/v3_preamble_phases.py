"""Preamble-фазы V3: B, U, enable, max CPA guard (cap, passing UP, NO DATA enable)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import V3Action
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3Eligibility,
    can_target_mode,
    clamp_target_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    is_keyword_no_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    _append_force_off_then_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    _HARD_STATUS_AUTO_MODE,
    _HARD_STATUS_WHITE_LIST,
    _hard_status_allows_up,
    plan_max_cpa_guard,
    plan_profitable_expansion,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    MAX_PAY_STABILIZATION_RATIO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    SelectionPolicy,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )


def plan_mode_cap_down(
    prepared: PreparedList,
    *,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility],
    covered: set[int] | None = None,
) -> list[V3Action]:
    """Фаза B: опустить ``strategy_mode`` выше cap по tier (FULL/PFO/NO DATA active)."""
    actions: list[V3Action] = []
    min_level = mode_level(KeywordStrategyMode.MIN_CPA)
    skip_ids = covered or set()

    for ctx, mode in prepared:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None or int(ks_id) in skip_ids:
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        elig = eligibility_by_ks_id.get(int(ks_id))
        if elig is None:
            continue

        if elig.data_tier == KeywordDataTier.KEYWORD_NO_DATA:
            if mode == KeywordStrategyMode.OFF:
                continue
            if mode_level(mode) > min_level:
                target = KeywordStrategyMode.MIN_CPA
                _append_cap_down(actions, ks_id=int(ks_id), target=target, hard_status=int(ctx.keyword.hard_status))
            continue

        if mode_level(mode) <= min_level:
            continue
        cap = clamp_target_mode(elig, mode)
        if mode_level(cap) >= mode_level(mode):
            continue
        if not can_target_mode(elig, cap):
            cap = KeywordStrategyMode.MIN_CPA
        _append_cap_down(actions, ks_id=int(ks_id), target=cap, hard_status=int(ctx.keyword.hard_status))

    return actions


def _append_cap_down(
    actions: list[V3Action],
    *,
    ks_id: int,
    target: KeywordStrategyMode,
    hard_status: int,
) -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        V3ActionType,
    )

    if hard_status == _HARD_STATUS_WHITE_LIST:
        actions.append(
            V3Action(
                action=V3ActionType.DOWN,
                keyword_setting_id=ks_id,
                target_strategy_mode=target,
                reason="cap_bootstrap_down",
            )
        )
    elif hard_status == _HARD_STATUS_AUTO_MODE:
        _append_force_off_then_up(
            actions,
            ks_id=ks_id,
            target_strategy_mode=target,
            reason="cap_bootstrap_down",
        )


def plan_passing_up(
    prepared: PreparedList,
    *,
    resolve: float,
    policy: SelectionPolicy,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: LadderInputs | None = None,
) -> list[V3Action]:
    """Фаза U: UP до max passing mode при cost/PFO ≤ resolve (alias profitable expansion)."""
    actions = plan_profitable_expansion(
        prepared,
        resolve=resolve,
        policy=policy,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder_inputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        V3ActionType,
    )

    return [
        a.model_copy(
            update={
                "reason": "passing_up"
                if a.reason == "profitable_expansion"
                else a.reason
            }
        )
        for a in actions
        if a.action == V3ActionType.UP
    ]


def plan_pay_for_order_gap_enable(
    prepared: PreparedList,
    *,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility],
    fact_pay_for_order: float | None,
    resolve: float,
    max_new_enables: int = 1,
    plan_fact_changed: bool,
    views_changed: bool,
) -> list[V3Action]:
    """Фаза enable: NO DATA + OFF → MIN, не более ``max_new_enables`` за тик.

    Зона headroom: ``fact_pay_for_order < MAX_PAY_STABILIZATION_RATIO × resolve`` (0.9).
    Тиковый gate: хотя бы одно из plan/fact или views изменилось (OR; калибровка — AND).

    Только ``KEYWORD_NO_DATA``; OFF с FULL/PFO enable не поднимает — см.
    ``collect_calibration_up_next_step_candidates`` (калибровка, ветка UP).

    При ``fact < 0.9×resolve`` тот же OFF NO DATA может дополнительно попасть в
    калибровку, ветку UP (фаза 8, min CPO, rec-gate, gate AND plan/views) после enable.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        V3ActionType,
    )

    if fact_pay_for_order is None:
        return []
    if float(resolve) <= 0:
        return []
    if float(fact_pay_for_order) >= MAX_PAY_STABILIZATION_RATIO * float(resolve):
        return []
    if not plan_fact_changed and not views_changed:
        return []
    if max_new_enables <= 0:
        return []

    candidates: list[tuple[int, str, int]] = []
    for ctx, mode in prepared:
        if mode != KeywordStrategyMode.OFF:
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        elig = eligibility_by_ks_id.get(int(ks_id))
        if elig is None or elig.data_tier != KeywordDataTier.KEYWORD_NO_DATA:
            continue
        if not is_keyword_no_data(ctx.keyword):
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        candidates.append((int(ks_id), ctx.keyword.text, int(ctx.keyword.hard_status)))

    candidates.sort(key=lambda x: (x[0], x[1]))
    actions: list[V3Action] = []
    for ks_id, _text, _hs in candidates[:max_new_enables]:
        actions.append(
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=ks_id,
                target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                reason="pay_for_order_gap_enable",
            )
        )
    return actions


def plan_max_cpa_guard_phase(
    prepared: PreparedList,
    *,
    max_pay_for_order: float,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: LadderInputs | None = None,
) -> list[V3Action]:
    """Фаза G.2: trim по ``plan.max_pay_for_order`` при overspend."""
    return plan_max_cpa_guard(
        prepared,
        max_pay_for_order=max_pay_for_order,
        shelf_click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder_inputs,
    )
