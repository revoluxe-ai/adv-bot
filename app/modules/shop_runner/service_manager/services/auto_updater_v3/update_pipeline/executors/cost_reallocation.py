"""Фаза R: симметричный cost reallocation (DOWN дорогого + UP дешёвого).

Двойная защита от каннибализации лимита (намеренно, не баг):

1. ``state_cost`` — CPO **целевой ступени** лестницы (CH-профиль, ``StateBinding[2]``).
2. ``keyword.pay_for_order`` — операционная себестоимость заказа ключа (как в UI).

Пара фиксирована: **max-CPO active** (donor) ↔ **min-CPO potential** (recipient).
Оба условия проверяются на **этой одной паре**. При провале PFO у min-CPO recipient
цикл ``break`` — **без** перебора следующих potential с более высоким ladder CPO:
иначе ключ с плохим keyword PFO мог бы получить UP только потому, что у другого
кандидата PFO лучше, хотя по лестнице он уже не «самый дешёвый» — это и есть
каннибализация лимита (лестница обещает дешевизну, фактическая экономика ключа — нет).
"""

from __future__ import annotations

import logging

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    LadderStepSnapshot,
    classify_ladder_step,
    ladder_step_snapshot_from_dto,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    pick_effective_down_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.states_list_generator import (
    StateBinding,
    StatesListGenerator,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)

logger = logging.getLogger(__name__)

# Верхняя граница пар DOWN+UP за тик (каждая итерация — одна пара при наличии donor/recipient).
_MAX_REBALANCE_CYCLES = 3000

# Skip фазы (tick report / Telegram).
SKIP_NO_CURRENT_ACTIVE = "no_current_active"
SKIP_NO_POTENTIAL_UP = "no_potential_up"


class RebalanceExecutor:
    """COST_REALLOCATION: перетекание cost из active в potential.

    ``potential_up`` — ступени MIN/OPT/MAX **выше** текущего ранга ключа (см.
    ``StatesListGenerator``). На каждой итерации одна пара:

    - donor — active с **максимальным** ``state_cost``;
    - recipient — potential с **минимальным** ``state_cost`` (actionable UP).

    Условия перетекания (оба на **этой** паре, без fallback на другие potential):

    - ``donor.state_cost > recipient.state_cost`` — по лестнице есть куда переливать;
    - ``recipient.keyword.pay_for_order < donor.keyword.pay_for_order`` — операционная
      экономика ключа подтверждает (anti-cannibalization: низкий ladder CPO при
      плохом keyword PFO не даёт UP).

    Если min-CPO recipient не проходит PFO-гейт — ``break`` всей фазы на тик.
    Следующие potential (дороже по ladder CPO, но с лучшим PFO) **намеренно**
    не перебираются: это уже другая операция, не «max-active → min-potential».

    Выход:

    - ``no_potential_up`` — некуда поднимать (все operable на потолке / list2 пуст);
    - ``no_current_active`` — нечего резать (все OFF или нет CPO в active);
    - в цикле: нет DOWN донора, нет учтённого UP, CPO-донор ≤ min potential (равновесие),
      или PFO min-CPO recipient ≥ PFO donor (двойная защита: оснований нет).
    """

    phase_name = "cost_reallocation"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(RebalanceExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = _phase_skip_reason(context)
        if self._skip_reason is not None:
            return
        generator = StatesListGenerator(context.adv_state)
        resolve = float(context.adv_state.resolve)
        current_states, potential_states = _filter_rebalance_candidates(
            generator.get_current_states(context.keywords),
            resolve=resolve,
        )

        if not current_states:
            self._skip_reason = SKIP_NO_CURRENT_ACTIVE
            return
        if not potential_states:
            self._skip_reason = SKIP_NO_POTENTIAL_UP
            return

        for _ in range(_MAX_REBALANCE_CYCLES):
            current_states, potential_states = _filter_rebalance_candidates(
                generator.get_current_states(context.keywords),
                resolve=resolve,
            )
            if not current_states:
                break
            if not potential_states:
                # Все поднялись до потолка / policy — принять некуда, перетекание стоп.
                break
            donor = _pick_most_expensive(current_states)
            down_state = pick_effective_down_ladder_state(donor[0])
            if down_state is None:
                break
            if not _ladder_step_would_change(donor[0], down_state):
                break
            recipient = _pick_cheapest_actionable_recipient(potential_states)
            if recipient is None:
                break
            if donor[2] <= recipient[2]:
                break
            # PFO только для пары max-active ↔ min-potential; break без перебора
            # других potential — намеренная anti-cannibalization (см. module docstring).
            if not _rebalance_allowed_by_pay_for_order(donor, recipient):
                break
            self._next_state_manager.raise_state_to_target_cpo(donor[0], down_state)
            self._next_state_manager.raise_state_to_target_cpo(
                recipient[0],
                recipient[1],
            )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _filter_rebalance_candidates(
    states: tuple[list[StateBinding], list[StateBinding]],
    *,
    resolve: float,
) -> tuple[list[StateBinding], list[StateBinding]]:
    """Оставить только donor/recipient candidates с ladder CPO выше ``resolve``."""
    current_states, potential_states = states
    return (
        [row for row in current_states if row[2] > resolve],
        [row for row in potential_states if row[2] > resolve],
    )


def _phase_skip_reason(context: UpdateContext) -> str | None:
    """Phase-level rebalance gate.

    Rebalance intentionally yields to any earlier preamble mutation. Executors
    before this phase may already have scheduled deterministic safety,
    correction, activation, or target-place changes for the current tick.
    Mixing cost reallocation with those prior decisions in the same preamble
    would combine independent actions. Therefore any non-empty ``next_state``
    or ``history_target_place`` produced before this phase blocks rebalance.

    No-op phases do not append to these lists and do not block the phase.
    """
    if not context.adv_state.resolve_valid:
        return "resolve_invalid"
    for dto in context.keywords:
        # Broad business rule: any prior real mutation blocks rebalance.
        # ``next_state`` means a planned mode/state transition; ``history_target_place``
        # means a planned target-place transition. Empty lists indicate no-op phases.
        if dto.next_state or dto.history_target_place:
            return "prior_executor_applied"
    return None


def _snapshot_for_ladder_state(state: KeywordV3LadderState) -> LadderStepSnapshot:
    place = (
        None
        if state.strategy_mode == KeywordStrategyMode.OFF
        else int(state.target_position)
    )
    return LadderStepSnapshot(state.strategy_mode, place)


def _ladder_step_would_change(dto: KeywordDTO, state: KeywordV3LadderState) -> bool:
    """``True``, если применение ``state`` попадёт в audit как UP/DOWN/OFF."""
    before = ladder_step_snapshot_from_dto(dto)
    after = _snapshot_for_ladder_state(state)
    return classify_ladder_step(before, after) is not None


def _pick_cheapest_actionable_recipient(
    potential_states: list[StateBinding],
) -> StateBinding | None:
    """Единственный candidate recipient: min ``state_cost`` в ``potential_up`` с audit UP.

    Возвращает ровно одну связку — самую дешёвую по ladder CPO. PFO-гейт в ``execute``
    проверяется только для неё; при провале другие potential не рассматриваются
    (см. ``RebalanceExecutor``).
    """
    for binding in sorted(
        potential_states, key=lambda item: (item[2], item[0].keyword_setting_id)
    ):
        if _ladder_step_would_change(binding[0], binding[1]):
            return binding
    return None


def _pick_most_expensive(states: list[StateBinding]) -> StateBinding:
    """Donor: active-связка с максимальным ``state_cost`` (пара к min-potential recipient)."""
    return max(states, key=lambda item: (item[2], item[0].keyword_setting_id))


def _keyword_pay_for_order(dto: KeywordDTO, *, role: str) -> float:
    """Вернуть ``keyword.pay_for_order``; при ``None`` — error-лог и ``ValueError``.

    Args:
        dto: Ключ donor/recipient.
        role: ``"donor"`` или ``"recipient"`` для диагностики.

    Returns:
        Положительный PFO ключа.

    Raises:
        ValueError: PFO недоступен при наличии operable state (инвариант нарушен).
    """
    pfo = dto.calculated_keyword.pay_for_order
    if pfo is None:
        logger.error(
            "rebalance: keyword pay_for_order missing role=%s ks_id=%s adv_id=%s",
            role,
            dto.keyword_setting_id,
            dto.calculated_keyword.adv_id,
        )
        raise ValueError(
            f"rebalance: keyword pay_for_order missing "
            f"(role={role}, ks_id={dto.keyword_setting_id})"
        )
    return float(pfo)


def _rebalance_allowed_by_pay_for_order(
    donor: StateBinding,
    recipient: StateBinding,
) -> bool:
    """Второй слой гейта: keyword PFO recipient < keyword PFO donor.

    ``recipient`` всегда min-CPO potential из ``_pick_cheapest_actionable_recipient``.
    ``False`` означает «лестница дешевле, но ключ дорогой по факту» — UP не даём.
    Вызывающий код делает ``break`` без поиска альтернативного recipient: перебор
    potential с большим ladder CPO ослабил бы требование min-potential и открыл бы
    каннибализацию лимита в ключ с плохой операционной экономикой.
    """
    donor_pfo = _keyword_pay_for_order(donor[0], role="donor")
    recipient_pfo = _keyword_pay_for_order(recipient[0], role="recipient")
    return recipient_pfo < donor_pfo
