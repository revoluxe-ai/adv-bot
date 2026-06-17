"""In-place переходы ``KeywordDTO.current_mode`` для preamble executors."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    resolve_alias_collapse_up_state_at_same_target_place,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
    NextState,
    NextTargetPlace,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_mode import (
    KeywordMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.not_full_target_place import (
    adjust_not_full_target_place_for_plan_fact,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    HARD_STATUS_AUTO_MODE,
)


class NextStateManager:
    """Операции in-place над ``KeywordDTO``; ``executor_name`` пишется в каждый ``NextState``."""

    def __init__(self, executor_class: type, *, phase_id: str | None = None) -> None:
        self._executor_name = executor_class.__name__
        self._phase_id = phase_id or getattr(executor_class, "phase_name", self._executor_name)

    @property
    def executor_name(self) -> str:
        return self._executor_name

    def validate_state_by_hard_status(self, keyword: KeywordDTO) -> None:
        """``hard_status=1`` → ``OFF``."""
        if keyword.hard_status != HARD_STATUS_AUTO_MODE:
            return
        keyword.current_mode = NextState(
            new_mode=KeywordMode.OFF,
            executor_name=self._executor_name,
            phase_id=self._phase_id,
        )

    def validate_not_full_state(self, keyword: KeywordDTO) -> None:
        """Validate NOT FULL active keys → ``NOT_FULL_ACTIVATE`` (DTO → MIN_CPA)."""
        keyword.current_mode = NextState(
            new_mode=KeywordMode.NOT_FULL_ACTIVATE,
            executor_name=self._executor_name,
            phase_id=self._phase_id,
        )

    def adjust_not_full_target_place_plan_fact(
        self,
        keyword: KeywordDTO,
        *,
        fact_pay_for_order: float,
        resolve: float,
    ) -> None:
        """±1 ``target_place`` по plan-fact CPO vs resolve для NOT FULL MIN.

        Это последняя защита NF plan-fact от старого reset-в-0 бага. Даже если
        helper когда-нибудь ошибочно вернёт ``0``, этот слой мутации не запишет
        его в DTO: plan-fact имеет право только корректировать уже существующую
        рабочую позицию, а не выполнять reset или bootstrap.
        """
        new_place = adjust_not_full_target_place_for_plan_fact(
            keyword,
            fact_pay_for_order=fact_pay_for_order,
            resolve=resolve,
        )
        if new_place is None:
            return
        if new_place == 0:
            return
        keyword.current_target_place = NextTargetPlace(
            new_target_place=new_place,
            executor_name=self._executor_name,
        )

    def enable_gap_to_min_cpa(self, keyword: KeywordDTO) -> None:
        """GAP OFF → ``MIN_CPA`` + ``target_place=0`` (legacy enable UP без MIN в матрице)."""
        self.enable_off_to_min_cpa(keyword)

    def enable_off_to_min_cpa(self, keyword: KeywordDTO) -> None:
        """Explicit OFF → ``MIN_CPA`` + ``target_place=0`` via authorized executor path."""
        if keyword.current_mode != KeywordStrategyMode.OFF:
            return
        keyword.current_mode = NextState(
            new_mode=KeywordMode.MIN_CPA,
            executor_name=self._executor_name,
            phase_id=self._phase_id,
        )
        setting = keyword.calculated_keyword.keyword_setting
        setting.strategy_mode = KeywordStrategyMode.MIN_CPA
        setting.target_place = 0
        keyword.current_target_place = NextTargetPlace(
            new_target_place=0,
            executor_name=self._executor_name,
        )

    def raise_state_to_target_cpo(
        self,
        keyword: KeywordDTO,
        state: KeywordV3LadderState | None,
    ) -> None:
        """Применить ladder-state; ``None`` — no-op."""
        if state is None:
            return
        keyword.apply_ladder_state(
            state,
            executor_name=self._executor_name,
            phase_id=self._phase_id,
        )

    def set_keyword_strategy_mode(
        self,
        keyword: KeywordDTO,
        mode: KeywordStrategyMode,
    ) -> None:
        """Сменить strategy mode ключа in-place (shelf cleanup DOWN)."""
        keyword.current_mode = NextState(
            new_mode=KeywordMode.from_strategy_mode(mode),
            executor_name=self._executor_name,
            phase_id=self._phase_id,
        )

    def force_off(self, keyword: KeywordDTO) -> None:
        """FORCE_OFF для auto-mode ключей (hard_status=1)."""
        if keyword.current_mode != KeywordStrategyMode.OFF:
            self.set_keyword_strategy_mode(keyword, KeywordStrategyMode.OFF)

    def skip_up_same_target_place(
        self,
        keyword: KeywordDTO,
        catalog: dict[AggressionTargetMode, ModeCandidate],
        *,
        max_target_mode: KeywordStrategyMode | None = None,
        resolve: float | None = None,
    ) -> None:
        """Alias UP на текущем ``target_place`` → max режим группы через ``apply_ladder_state``.

        ``max_target_mode`` ограничивает alias-collapse сверху, чтобы UP bypass
        не мог перескочить выше policy cap. ``resolve`` ограничивает тот же
        alias-collapse по экономическому ceiling.
        """
        state = resolve_alias_collapse_up_state_at_same_target_place(
            keyword,
            keyword.current_mode,
            catalog,
            max_target_mode=max_target_mode,
            resolve=resolve,
        )
        if state is None:
            return
        keyword.apply_ladder_state(
            state,
            executor_name=self._executor_name,
            phase_id=self._phase_id,
        )
