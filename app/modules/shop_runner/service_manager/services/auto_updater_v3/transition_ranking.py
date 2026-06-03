"""Unified pooled UP ranking for V3 updater.

Контракт выбора UP:
- формируем общий пул кандидатов ``to_mode > current_mode``;
- в пул попадают только target-состояния, разрешённые ``aggressiveness``:
  ``1 -> MIN``, ``2 -> MIN/OPT``, ``3 -> MIN/OPT/C``;
- на полке rec-gate блокирует только ``above_rec=False`` (при ``shelf>=organic``/``UNKNOWN``);
- сортировка в пуле: ``rec_tier -> state_cost -> pay_for_order -> keyword_id``.

Два независимых сигнала:
- ``missing_target_matrix`` — нет валидной матрицы M/O/C; cost имьютится через worst-per-state,
  кроме collapsed CH + ``keyword.pay_for_order`` (SSOT ``cost_for_mode``);
- ``missing_above_rec`` — ``above_rec_conversion is None``; на полке tier ниже confirmed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
    stored_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    effective_conv_for_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    V3Action,
    V3ActionType,
    V3SelectionLog,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    candidate_for_strategy_mode,
    iter_effective_upper_modes,
    log_skipped_aliases,
    mode_candidates_same_effective_target,
    resolve_next_effective_step_down,
    resolve_next_effective_step_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

logger = logging.getLogger(__name__)

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2


def _hard_status_allows_up(hard_status: int) -> bool:
    """UP: авто (1) и белый список (2), как в ``rollout_planner``."""
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)

_PreparedEntry = tuple["KeywordV3Context", KeywordStrategyMode]
PreparedList = list[_PreparedEntry]


def build_prepared_from_contexts(
    contexts: list["KeywordV3Context"],
) -> PreparedList:
    """Собрать ``PreparedList`` из контекстов ключей.

    Каноническое определение для V3 planners; импортировать из ``transition_ranking``,
    не из ``selector``.
    """
    prepared: PreparedList = []
    for ctx in contexts:
        prepared.append((ctx, stored_strategy_mode(ctx.keyword)))
    return prepared


class RecTier(str, Enum):
    """Rec-уверенность для сортировки (полка)."""

    CONFIRMED = "confirmed"
    MISSING_ABOVE_REC = "missing_above_rec"
    NOT_APPLICABLE = "not_applicable"


class UpMoveKind(str, Enum):
    """Тип UP-перехода для логов."""

    OFF_TO_MIN = "off_to_min"
    OFF_TO_OPT = "off_to_opt"
    OFF_TO_MAX = "off_to_max"
    MIN_TO_OPT = "min_to_opt"
    MIN_TO_MAX = "min_to_max"
    OPT_TO_MAX = "opt_to_max"


@dataclass(frozen=True)
class TransitionCandidate:
    """Один допустимый UP-переход с метриками для ранжирования."""

    keyword_setting_id: int
    from_mode: KeywordStrategyMode
    to_mode: KeywordStrategyMode
    move_kind: UpMoveKind
    state_cost: float
    pay_for_order: float
    rec_tier: RecTier
    imputed: bool  # state_cost из worst-per-state при missing_target_matrix


@dataclass(frozen=True)
class SelectionPolicy:
    """Policy-переключатели unified ranking (rec-gate + агрессивность)."""

    click_mode: ShelfClickMode
    max_target_mode: KeywordStrategyMode

    @classmethod
    def from_aggressiveness(
        cls,
        *,
        click_mode: ShelfClickMode,
        aggressiveness: V3RolloutAggressiveness,
    ) -> "SelectionPolicy":
        """Создать policy из click-mode и 1..3 aggressiveness."""
        return cls(
            click_mode=click_mode,
            max_target_mode=max_target_mode_for_aggressiveness(aggressiveness),
        )


def max_target_mode_for_aggressiveness(
    aggressiveness: V3RolloutAggressiveness,
) -> KeywordStrategyMode:
    """Map aggressiveness to maximal allowed target mode."""
    if aggressiveness == V3RolloutAggressiveness.MIN:
        return KeywordStrategyMode.MIN_CPA
    if aggressiveness == V3RolloutAggressiveness.MID:
        return KeywordStrategyMode.OPTIMUM
    return KeywordStrategyMode.MAX_CONVERSION


def _ladder_inputs_for_prepared(
    prepared: PreparedList,
    ladder_inputs: "LadderInputs | None" = None,
) -> "LadderInputs":
    """Единый ``LadderInputs`` на проход pooled ranking (RK + worst_costs SSOT)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs as _LadderInputs,
    )

    if ladder_inputs is not None:
        return ladder_inputs
    contexts = [c for c, _ in prepared]
    return _LadderInputs.from_contexts(contexts)


def _catalog_for_ctx(
    ctx: "KeywordV3Context",
    contexts: PreparedList | None = None,
    *,
    ladder_inputs: "LadderInputs | None" = None,
    rk_orders_per_cart: float | None = None,
    campaign_orders_per_cart_7d: float | None = None,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """Каталог M/O/C: через ``LadderInputs.orders_per_cart_for_ctx`` или legacy resolve."""
    if ladder_inputs is not None:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
            _catalog_for_ctx as _ladder_catalog_for_ctx,
        )

        return _ladder_catalog_for_ctx(ctx, ladder_inputs)

    from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
        resolve_orders_per_cart_for_cpo,
    )

    campaign_opc = (
        campaign_orders_per_cart_7d
        if campaign_orders_per_cart_7d is not None
        else rk_orders_per_cart
    )
    opc = resolve_orders_per_cart_for_cpo(
        campaign_orders_per_cart_7d=campaign_opc,
        key_orders=ctx.keyword.orders,
        key_carts=ctx.keyword.add_to_cart,
    )
    conv = None
    if opc is None or opc <= 0:
        peer = [c for c, _ in contexts] if contexts else [ctx]
        conv = effective_conv_for_v3(ctx, peer)
        if conv is None:
            conv = ctx.keyword.conv_views_to_orders
    return build_mode_candidates(
        profile=ctx.position_profile,
        keyword_text=ctx.keyword.text,
        conv_views_to_orders=conv,
        orders_per_cart=opc,
    )


def missing_target_matrix_from_catalog(
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> bool:
    """Нет ни одного валидного M/O/C в уже построенном каталоге кандидатов."""
    return not any(mc.is_valid for mc in catalog.values())


def missing_target_matrix(
    ctx: "KeywordV3Context",
    contexts: PreparedList | None = None,
) -> bool:
    """Нет ни одного валидного целевого места M/O/C в матрице профиля."""
    return missing_target_matrix_from_catalog(_catalog_for_ctx(ctx, contexts))


def missing_above_rec(ctx: "KeywordV3Context") -> bool:
    """Нет подтверждённого rec-сигнала (``above_rec_conversion is None``)."""
    return ctx.keyword.above_rec_conversion is None


def upper_target_modes(current: KeywordStrategyMode) -> list[KeywordStrategyMode]:
    """Все режимы строго выше текущего (jump разрешён)."""
    cur = int(current)
    out: list[KeywordStrategyMode] = []
    for mode in (
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ):
        if int(mode) > cur:
            out.append(mode)
    return out


def move_kind_for(
    from_mode: KeywordStrategyMode,
    to_mode: KeywordStrategyMode,
) -> UpMoveKind:
    pair = (from_mode, to_mode)
    mapping: dict[tuple[KeywordStrategyMode, KeywordStrategyMode], UpMoveKind] = {
        (KeywordStrategyMode.OFF, KeywordStrategyMode.MIN_CPA): UpMoveKind.OFF_TO_MIN,
        (KeywordStrategyMode.OFF, KeywordStrategyMode.OPTIMUM): UpMoveKind.OFF_TO_OPT,
        (
            KeywordStrategyMode.OFF,
            KeywordStrategyMode.MAX_CONVERSION,
        ): UpMoveKind.OFF_TO_MAX,
        (
            KeywordStrategyMode.MIN_CPA,
            KeywordStrategyMode.OPTIMUM,
        ): UpMoveKind.MIN_TO_OPT,
        (
            KeywordStrategyMode.MIN_CPA,
            KeywordStrategyMode.MAX_CONVERSION,
        ): UpMoveKind.MIN_TO_MAX,
        (
            KeywordStrategyMode.OPTIMUM,
            KeywordStrategyMode.MAX_CONVERSION,
        ): UpMoveKind.OPT_TO_MAX,
    }
    return mapping[pair]


def _target_mode_for_strategy(mode: KeywordStrategyMode) -> AggressionTargetMode:
    return AggressionTargetMode[mode.name]


def _target_allowed(
    *,
    to_mode: KeywordStrategyMode,
    max_target_mode: KeywordStrategyMode,
) -> bool:
    return int(to_mode) <= int(max_target_mode)


def _has_valid_target_place_data(
    catalog: dict[AggressionTargetMode, ModeCandidate],
) -> bool:
    return any(mc.is_valid for mc in catalog.values())


def shelf_rec_conversion_policy_active(click_mode: ShelfClickMode) -> bool:
    """Активно ли полочное правило по ``above_rec`` (shelf >= organic или нет traffic DTO).

    Единый триггер для:
    - rec-gate на UP: state-level ``rec_gate_allows_up`` (PASS/UNKNOWN/INACTIVE);
    - cleanup (``plan_shelf_rec_false_cleanup_down``): только state с ``FAIL``.

    Args:
        click_mode: Режим organic/shelf из ``resolve_shelf_click_mode`` (полочная фаза).

    Returns:
        True, если применяем полочный фильтр и cleanup (не ``ORGANIC_DOMINANT``).
    """
    return click_mode in (
        ShelfClickMode.SHELF_DOMINANT_OR_EQUAL,
        ShelfClickMode.UNKNOWN,
    )


def passes_rec_gate_for_up(
    above_rec: bool | None,
    *,
    click_mode: ShelfClickMode,
    to_mode: KeywordStrategyMode | None = None,
) -> bool:
    """UP разрешён с учётом полочного ``above_rec``.

    Organic — без rec-барьера. На полке при ``above_rec=False``:
    - в ``MIN_CPA`` (в т.ч. OFF→MIN bootstrap) — по экономике, rec не режет;
    - в ``OPTIMUM`` / ``MAX_CONVERSION`` — блок (STEP_UP агрессии).

    Args:
        above_rec: Сигнал ``above_rec_conversion`` ключа.
        click_mode: Режим organic/shelf кампании.
        to_mode: Целевой режим UP; ``None`` — legacy: любой UP кроме MIN блокируется.
    """
    if not shelf_rec_conversion_policy_active(click_mode):
        return True
    if above_rec is not False:
        return True
    if to_mode == KeywordStrategyMode.MIN_CPA:
        return True
    if to_mode is None:
        return False
    return False


def _rec_tier_for_keyword(
    above_rec: bool | None,
    *,
    click_mode: ShelfClickMode,
) -> RecTier:
    if not shelf_rec_conversion_policy_active(click_mode):
        return RecTier.NOT_APPLICABLE
    if above_rec is True:
        return RecTier.CONFIRMED
    if above_rec is None:
        return RecTier.MISSING_ABOVE_REC
    return RecTier.NOT_APPLICABLE


def _resolve_state_cost(
    mc: ModeCandidate,
    target: AggressionTargetMode,
    *,
    use_imputation: bool = False,
) -> tuple[float, bool]:
    """Вернуть state_cost только из профиля CH (worst-imputation удалён)."""
    _ = target, use_imputation
    if mc.is_valid and mc.predicted_cpa is not None:
        return float(mc.predicted_cpa), False
    return float("inf"), False


def build_worst_per_state_costs(
    prepared: PreparedList,
    *,
    rk_orders_per_cart: float | None = None,
    campaign_orders_per_cart_7d: float | None = None,
    ladder_inputs: "LadderInputs | None" = None,
) -> dict[AggressionTargetMode, float]:
    """Deprecated: worst-imputation удалён; возвращает пустой словарь."""
    _ = prepared, rk_orders_per_cart, campaign_orders_per_cart_7d, ladder_inputs
    return {}


def collect_transition_candidates(
    prepared: PreparedList,
    *,
    policy: SelectionPolicy,
    ladder_inputs: "LadderInputs | None" = None,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
) -> list[TransitionCandidate]:
    """Все допустимые UP-переходы с метриками (effective upper modes + RK catalog)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordV3Eligibility,
        build_eligibility_map,
        can_target_mode,
        min_cpa_operational_via_pay_for_order,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        cost_for_mode,
    )

    ladder = _ladder_inputs_for_prepared(prepared, ladder_inputs)
    elig_map: dict[int, KeywordV3Eligibility] = (
        eligibility_by_ks_id
        if eligibility_by_ks_id is not None
        else build_eligibility_map(
            ladder.all_contexts,
            campaign_orders_per_cart_7d=ladder.campaign_orders_per_cart_7d,
        )
    )
    out: list[TransitionCandidate] = []

    for ctx, current_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if current_mode == KeywordStrategyMode.MAX_CONVERSION:
            continue

        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue

        catalog = _catalog_for_ctx(ctx, prepared, ladder_inputs=ladder)
        use_matrix_imputation = missing_target_matrix_from_catalog(catalog)
        elig = (
            elig_map.get(int(ks_id)) if ks_id is not None else None
        )
        pfo_operational = min_cpa_operational_via_pay_for_order(ctx, elig, catalog)
        tier = _rec_tier_for_keyword(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        )
        pfo = float(ctx.keyword.pay_for_order or 0.0)

        for to_mode in iter_effective_upper_modes(current_mode, catalog):
            target = _target_mode_for_strategy(to_mode)
            mc = catalog.get(target)
            if mc is None:
                continue
            if elig is not None and not can_target_mode(elig, to_mode):
                continue
            from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
                rec_gate_allows_up,
                state_rec_gate_status_for_mode,
            )

            gate_status = state_rec_gate_status_for_mode(
                catalog,
                to_mode,
                policy,
                rec_orders_per_view=ladder.rec_orders_per_view,
                orders_per_cart=ladder.orders_per_cart_for_ctx(ctx),
            )
            if not rec_gate_allows_up(gate_status):
                continue
            if not _target_allowed(
                to_mode=to_mode,
                max_target_mode=policy.max_target_mode,
            ):
                continue
            if pfo_operational or elig is not None:
                cost, imputed = cost_for_mode(
                    ctx,
                    to_mode,
                    ladder_inputs=ladder,
                    eligibility=elig,
                )
            else:
                cost, imputed = _resolve_state_cost(mc, target)
            if cost == float("inf"):
                continue
            out.append(
                TransitionCandidate(
                    keyword_setting_id=ks_id,
                    from_mode=current_mode,
                    to_mode=to_mode,
                    move_kind=move_kind_for(current_mode, to_mode),
                    state_cost=cost,
                    pay_for_order=pfo,
                    rec_tier=tier,
                    imputed=imputed,
                )
            )
    return out


def collect_calibration_up_next_step_candidates(
    prepared: PreparedList,
    *,
    policy: SelectionPolicy,
    ladder_inputs: "LadderInputs | None" = None,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
) -> list[TransitionCandidate]:
    """Следующий effective-шаг UP на ключ; без потолка resolve (калибровка UP).

    Один переход на ключ — ``resolve_next_effective_step_up``; итоговый выбор
    ключа — ``pick_one_up_cost_first`` (минимальный state_cost / PFO).
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordV3Eligibility,
        build_eligibility_map,
        can_target_mode,
        min_cpa_operational_via_pay_for_order,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        cost_for_mode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
        rec_gate_allows_up,
        state_rec_gate_status_for_mode,
    )

    ladder = _ladder_inputs_for_prepared(prepared, ladder_inputs)
    elig_map: dict[int, KeywordV3Eligibility] = (
        eligibility_by_ks_id
        if eligibility_by_ks_id is not None
        else build_eligibility_map(
            ladder.all_contexts,
            campaign_orders_per_cart_7d=ladder.campaign_orders_per_cart_7d,
        )
    )
    out: list[TransitionCandidate] = []

    for ctx, current_mode in prepared:
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        if current_mode == KeywordStrategyMode.OFF:
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        catalog = _catalog_for_ctx(ctx, prepared, ladder_inputs=ladder)
        elig = elig_map.get(int(ks_id))
        if elig is not None and not elig.participates_in_ladder:
            continue
        step = resolve_next_effective_step_up(current_mode, catalog)
        log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
        to_mode = step.next_mode
        if to_mode is None:
            continue
        target = _target_mode_for_strategy(to_mode)
        mc = catalog.get(target)
        if mc is None:
            continue
        if elig is not None and not can_target_mode(elig, to_mode):
            continue
        gate_status = state_rec_gate_status_for_mode(
            catalog,
            to_mode,
            policy,
            rec_orders_per_view=ladder.rec_orders_per_view,
            orders_per_cart=ladder.orders_per_cart_for_ctx(ctx),
        )
        if not rec_gate_allows_up(gate_status):
            continue
        if not _target_allowed(to_mode=to_mode, max_target_mode=policy.max_target_mode):
            continue
        pfo_operational = min_cpa_operational_via_pay_for_order(ctx, elig, catalog)
        tier = _rec_tier_for_keyword(
            ctx.keyword.above_rec_conversion,
            click_mode=policy.click_mode,
        )
        pfo = float(ctx.keyword.pay_for_order or 0.0)
        if pfo_operational or elig is not None:
            cost, imputed = cost_for_mode(
                ctx,
                to_mode,
                ladder_inputs=ladder,
                eligibility=elig,
            )
        else:
            cost, imputed = _resolve_state_cost(mc, target)
        if cost == float("inf"):
            continue
        current_c = candidate_for_strategy_mode(current_mode, catalog)
        target_c = candidate_for_strategy_mode(to_mode, catalog)
        if mode_candidates_same_effective_target(current_c, target_c):
            continue
        out.append(
            TransitionCandidate(
                keyword_setting_id=int(ks_id),
                from_mode=current_mode,
                to_mode=to_mode,
                move_kind=move_kind_for(current_mode, to_mode),
                state_cost=cost,
                pay_for_order=pfo,
                rec_tier=tier,
                imputed=imputed,
            )
        )
    return out


def _tier_sort_key(tier: RecTier) -> int:
    order = {
        RecTier.CONFIRMED: 0,
        RecTier.MISSING_ABOVE_REC: 1,
        RecTier.NOT_APPLICABLE: 2,
    }
    return order.get(tier, 3)


def _candidate_sort_key(c: TransitionCandidate) -> tuple[int, float, float, int]:
    return (
        _tier_sort_key(c.rec_tier),
        c.state_cost,
        c.pay_for_order,
        c.keyword_setting_id,
    )


def pick_one_up_cost_first(
    candidates: list[TransitionCandidate],
    *,
    reason_prefix: str = "up_cost_first_pooled",
) -> V3Action | None:
    """Один UP: минимальный state_cost, tie-break pay_for_order."""
    if not candidates:
        return None
    best = min(candidates, key=_candidate_sort_key)
    return _candidate_to_action(best, pool_size=len(candidates), reason_prefix=reason_prefix)


def _candidate_to_action(
    cand: TransitionCandidate,
    *,
    pool_size: int,
    reason_prefix: str,
) -> V3Action:
    if cand.imputed:
        reason = "up_imputed_missing_target_matrix"
    elif cand.rec_tier == RecTier.MISSING_ABOVE_REC:
        reason = "up_missing_above_rec"
    else:
        reason = reason_prefix
    return V3Action(
        action=V3ActionType.UP,
        keyword_setting_id=cand.keyword_setting_id,
        target_strategy_mode=cand.to_mode,
        reason=reason,
        selection_log=V3SelectionLog(
            pool_size=pool_size,
            pool_size_after_rec=pool_size,
            rec_tier=cand.rec_tier.value,
            state_cost=cand.state_cost,
            pay_for_order=cand.pay_for_order,
            from_mode=cand.from_mode.name,
            to_mode=cand.to_mode.name,
            move_kind=cand.move_kind.value,
            imputed=cand.imputed,
        ),
    )


def plan_shelf_rec_false_cleanup_down(
    prepared: PreparedList,
    *,
    click_mode: ShelfClickMode,
    ladder_inputs: "LadderInputs | None" = None,
    policy: SelectionPolicy | None = None,
) -> list[V3Action]:
    """Полка: cleanup активных ключей, у которых **текущий** state = ``RecGateStatus.FAIL``.

    - ``rec_orders_per_view is None`` — gate неактивен, cleanup не выполняется;
    - текущий state PASS / UNKNOWN / INACTIVE — не трогаем;
    - текущий state FAIL, MIN PASS/UNKNOWN — effective DOWN до MIN для БС (``hard_status=2``);
      для авто (``hard_status=1``) — ``FORCE_OFF`` (applier не применяет DOWN);
    - ``hard_status=2`` (БС): DOWN по лестнице; при MIN и ``step_down`` без цели — fallback OFF;
    - ``hard_status=1`` (авто): FORCE_OFF только если MIN тоже FAIL.

    Key-level ``above_rec_conversion`` не используется.
    """
    if not shelf_rec_conversion_policy_active(click_mode):
        return []

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
        rec_gate_allows_up,
        rec_gate_triggers_cleanup,
        state_rec_gate_status_for_mode,
    )

    ladder = _ladder_inputs_for_prepared(prepared, ladder_inputs)
    gate_policy = policy or SelectionPolicy.from_aggressiveness(
        click_mode=click_mode,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    rec = ladder.rec_orders_per_view
    if rec is None:
        return []

    actions: list[V3Action] = []
    for ctx, mode in prepared:
        if mode == KeywordStrategyMode.OFF:
            continue
        hard_status = int(ctx.keyword.hard_status)
        if hard_status not in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue

        state_candidates = _catalog_for_ctx(ctx, prepared, ladder_inputs=ladder)
        opc = ladder.orders_per_cart_for_ctx(ctx)
        current_status = state_rec_gate_status_for_mode(
            state_candidates,
            mode,
            gate_policy,
            rec_orders_per_view=rec,
            orders_per_cart=opc,
        )
        if not rec_gate_triggers_cleanup(current_status):
            continue

        min_status = state_rec_gate_status_for_mode(
            state_candidates,
            KeywordStrategyMode.MIN_CPA,
            gate_policy,
            rec_orders_per_view=rec,
            orders_per_cart=opc,
        )

        if rec_gate_allows_up(min_status) and mode != KeywordStrategyMode.MIN_CPA:
            if hard_status == _HARD_STATUS_WHITE_LIST:
                actions.append(
                    V3Action(
                        action=V3ActionType.DOWN,
                        keyword_setting_id=ks_id,
                        target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                        reason="shelf_rec_false_cleanup",
                    )
                )
            else:
                actions.append(
                    V3Action(
                        action=V3ActionType.FORCE_OFF,
                        keyword_setting_id=ks_id,
                        reason="shelf_rec_false_cleanup",
                    )
                )
            continue

        if hard_status == _HARD_STATUS_WHITE_LIST:
            step = resolve_next_effective_step_down(mode, state_candidates)
            log_skipped_aliases(ctx.keyword.text, step.skipped_aliases)
            nxt = step.next_mode
            if nxt is None:
                if mode == KeywordStrategyMode.MIN_CPA:
                    logger.warning(
                        "v3 shelf_rec_false_cleanup: whitelist ks_id=%s at MIN, "
                        "step_down returned None; fallback OFF",
                        ks_id,
                    )
                    nxt = KeywordStrategyMode.OFF
                else:
                    logger.warning(
                        "v3 shelf_rec_false_cleanup: whitelist ks_id=%s mode=%s, "
                        "step_down returned None; skip cleanup",
                        ks_id,
                        mode.name,
                    )
                    continue
            actions.append(
                V3Action(
                    action=V3ActionType.DOWN,
                    keyword_setting_id=ks_id,
                    target_strategy_mode=nxt,
                    reason="shelf_rec_false_cleanup",
                )
            )
        else:
            actions.append(
                V3Action(
                    action=V3ActionType.FORCE_OFF,
                    keyword_setting_id=ks_id,
                    reason="shelf_rec_false_cleanup",
                )
            )
    return actions


def plan_one_up_by_policy(
    prepared: PreparedList,
    *,
    policy: SelectionPolicy,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """Unified pooled planner: один UP из общего пула кандидатов."""
    candidates = collect_transition_candidates(
        prepared, policy=policy, ladder_inputs=ladder_inputs
    )
    if not candidates:
        return [
            V3Action(
                action=V3ActionType.DO_NOTHING,
                reason="no_valid_up_after_rec_filter",
            )
        ]

    action = pick_one_up_cost_first(candidates, reason_prefix="up_cost_first_pooled")

    if action is None:
        return [
            V3Action(
                action=V3ActionType.DO_NOTHING,
                reason="no_valid_up_after_policy_filter",
            )
        ]
    return [action]


def plan_cost_first_up_one(
    prepared: PreparedList,
    *,
    click_mode: ShelfClickMode,
    layered: bool,
    aggressiveness: V3RolloutAggressiveness,
    piecewise_shelf: bool,
    ladder_inputs: "LadderInputs | None" = None,
) -> list[V3Action]:
    """Backward-compatible wrapper around unified pooled planner."""
    _ = (layered, piecewise_shelf)  # deprecated knobs, kept for compatibility
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=click_mode,
        aggressiveness=aggressiveness,
    )
    return plan_one_up_by_policy(
        prepared, policy=policy, ladder_inputs=ladder_inputs
    )
