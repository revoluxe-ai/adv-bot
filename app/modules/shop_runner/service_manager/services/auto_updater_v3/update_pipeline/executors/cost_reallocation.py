"""Фаза R: симметричный cost reallocation (DOWN дорогого + UP дешёвого).

Помимо сравнения ``state_cost`` (CPO ступени) требуется ``recipient.pay_for_order <
donor.pay_for_order`` по keyword-level PFO (как в карточке UI).
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
    ``StatesListGenerator``). Пока есть куда поднимать и есть дорогой active —
    режем донора, поднимаем recipient. Выход:

    - ``no_potential_up`` — некуда поднимать (все operable на потолке / list2 пуст);
    - ``no_current_active`` — нечего резать (все OFF или нет CPO в active);
    - в цикле: нет DOWN донора, нет учтённого UP, CPO-донор ≤ min potential (равновесие),
      или PFO recipient ≥ PFO donor (нет оснований по операционной себестоимости ключа).
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
        current_states, potential_states = generator.get_current_states(
            context.keywords
        )
        if not current_states:
            self._skip_reason = SKIP_NO_CURRENT_ACTIVE
            return
        if not potential_states:
            self._skip_reason = SKIP_NO_POTENTIAL_UP
            return

        for _ in range(_MAX_REBALANCE_CYCLES):
            current_states, potential_states = generator.get_current_states(
                context.keywords
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


def _phase_skip_reason(context: UpdateContext) -> str | None:
    if not context.adv_state.resolve_valid:
        return "resolve_invalid"
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
    """Минимальный CPO в ``potential_up``, для которого UP попадёт в audit."""
    for binding in sorted(
        potential_states, key=lambda item: (item[2], item[0].keyword_setting_id)
    ):
        if _ladder_step_would_change(binding[0], binding[1]):
            return binding
    return None


def _pick_most_expensive(states: list[StateBinding]) -> StateBinding:
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
    """``True``, если PFO recipient строго ниже PFO donor (основание для перетекания)."""
    donor_pfo = _keyword_pay_for_order(donor[0], role="donor")
    recipient_pfo = _keyword_pay_for_order(recipient[0], role="recipient")
    return recipient_pfo < donor_pfo
