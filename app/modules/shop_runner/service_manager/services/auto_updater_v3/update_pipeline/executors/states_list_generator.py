"""Генератор списков current/potential states для rebalance и calibration."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    deep_overspend_blocks_ladder_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    is_keyword_no_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.state_rec_gate import (
    RecGateStatus,
    rec_gate_allows_up,
    state_rec_gate_status_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    shelf_rec_conversion_policy_active,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    OPERABLE_LADDER_STAGES,
    current_aggression_rank,
    ladder_aggression_rank,
    mode_catalog_from_dto,
    resolve_current_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    is_v3_operable_hard_status,
)

StateBinding = tuple[KeywordDTO, KeywordV3LadderState, float]


class StatesListGenerator:
    """Два списка связок ``(KeywordDTO, ladder-state, cpo)`` для rebalance/calibration."""

    def __init__(
        self,
        adv_state: AdvState,
        *,
        for_calibration: bool = False,
    ) -> None:
        self._adv_state = adv_state
        self._for_calibration = for_calibration

    def get_current_states(
        self,
        keywords: list[KeywordDTO],
    ) -> tuple[list[StateBinding], list[StateBinding]]:
        """``(current_active, potential_up)`` по operable ключам тика.

        ``current_active``: ключ не ``OFF``, текущая operable-ступень + CPO.
        ``potential_up``: пары (ключ, ступень) **строго выше** текущего ранга
        (``ladder_aggression_rank(state) > current_aggression_rank(dto)``),
        с CPO и shelf/rec gates. Пустой ``potential_up`` — все operable «в упор»
        вверх или некуда поднимать в рамках policy.
        """
        current_active: list[StateBinding] = []
        potential_up: list[StateBinding] = []

        for dto in keywords:
            if not is_v3_operable_hard_status(dto.hard_status):
                continue
            if dto.keyword_setting_id == 0:
                continue
            participates = _keyword_participates_in_ladder(dto, self._adv_state)
            off_no_data = (
                self._for_calibration and _is_calibration_off_no_data(dto, self._adv_state)
            )
            if not participates and not off_no_data:
                continue

            rank = current_aggression_rank(dto)

            if participates and dto.current_mode != KeywordStrategyMode.OFF:
                binding = _current_binding(dto, self._adv_state)
                if binding is not None:
                    current_active.append(binding)

            for state in _operable_ladder_states(dto):
                if not _state_above_rank(state, rank):
                    continue
                if not _target_mode_allowed(state.strategy_mode, self._adv_state):
                    continue
                if state.cpo is None:
                    continue
                if not _shelf_participating_state(dto, state, self._adv_state):
                    continue
                if not _shelf_allows_up(dto, state, self._adv_state):
                    continue
                if deep_overspend_blocks_ladder_up(dto, self._adv_state):
                    continue
                potential_up.append((dto, state, float(state.cpo)))

        return current_active, potential_up


def _keyword_participates_in_ladder(dto: KeywordDTO, adv_state: AdvState) -> bool:
    """Operable ключ участвует в ladder (``participates_in_ladder``)."""
    elig = adv_state.eligibility_by_ks_id.get(dto.keyword_setting_id)
    if elig is not None and not elig.participates_in_ladder:
        return False
    return True


def _is_calibration_off_no_data(dto: KeywordDTO, adv_state: AdvState) -> bool:
    """OFF + NO DATA для ослабленного list2 calibration UP."""
    if dto.current_mode != KeywordStrategyMode.OFF:
        return False
    elig = adv_state.eligibility_by_ks_id.get(dto.keyword_setting_id)
    if elig is None or elig.data_tier != KeywordDataTier.KEYWORD_NO_DATA:
        return False
    return is_keyword_no_data(dto.calculated_keyword)


def _operable_ladder_states(dto: KeywordDTO) -> tuple[KeywordV3LadderState, ...]:
    return tuple(
        state
        for state in dto.ladder_states
        if state.stage in OPERABLE_LADDER_STAGES
    )


def _current_binding(dto: KeywordDTO, adv_state: AdvState) -> StateBinding | None:
    """Текущая active-ступень для list1 (не OFF, известный CPO)."""
    state = resolve_current_ladder_state(dto)
    if state is None or state.stage not in OPERABLE_LADDER_STAGES:
        return None
    if state.cpo is None:
        return None
    if not _shelf_participating_state(dto, state, adv_state):
        return None
    return (dto, state, float(state.cpo))


def _state_above_rank(
    state: KeywordV3LadderState,
    current_rank: tuple[int, int],
) -> bool:
    return ladder_aggression_rank(state) > current_rank


def _target_mode_allowed(mode: KeywordStrategyMode, adv_state: AdvState) -> bool:
    return int(mode) <= int(adv_state.policy.max_target_mode)


def _shelf_filter_active(adv_state: AdvState) -> bool:
    return adv_state.shelf_active and shelf_rec_conversion_policy_active(
        adv_state.shelf_click_mode
    )


def is_shelf_participating_state(
    dto: KeywordDTO,
    state: KeywordV3LadderState,
    adv_state: AdvState,
) -> bool:
    """При полочном режиме — только state с активным rec-gate (не organic INACTIVE)."""
    return _shelf_participating_state(dto, state, adv_state)


def _shelf_participating_state(
    dto: KeywordDTO,
    state: KeywordV3LadderState,
    adv_state: AdvState,
) -> bool:
    if not _shelf_filter_active(adv_state):
        return True
    status = _rec_gate_status(dto, state, adv_state)
    return status != RecGateStatus.INACTIVE


def _shelf_allows_up(
    dto: KeywordDTO,
    state: KeywordV3LadderState,
    adv_state: AdvState,
) -> bool:
    """Для list2: UP только если rec-gate не FAIL."""
    if not _shelf_filter_active(adv_state):
        return True
    return rec_gate_allows_up(_rec_gate_status(dto, state, adv_state))


def _rec_gate_status(
    dto: KeywordDTO,
    state: KeywordV3LadderState,
    adv_state: AdvState,
) -> RecGateStatus:
    catalog = mode_catalog_from_dto(dto)
    ladder = adv_state.ladder_inputs
    return state_rec_gate_status_for_mode(
        catalog,
        state.strategy_mode,
        adv_state.policy,
        rec_orders_per_view=ladder.rec_orders_per_view,
        orders_per_cart=ladder.orders_per_cart_for_ctx(dto.context),
    )
