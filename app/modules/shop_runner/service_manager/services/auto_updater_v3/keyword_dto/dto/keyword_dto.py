"""DTO одного ключa V3: CalculatedKeyword + матрица CH + цепочка NextState на тике."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    stored_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_mode import (
    KeywordMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_prepared_row import (
    KeywordPreparedRow,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.next_state import (
    NextState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.next_target_place import (
    NextTargetPlace,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.target_place_matrix import (
    TargetPlaceMatrix,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    KeywordV3DataTier,
    resolve_keyword_v3_data_tier,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

@dataclass(slots=True)
class KeywordDTO:
    """Аккумулятор данных ключa на тик V3.

    DTO хранит и состояние ladder, и текущий operational tier ключа. ``current_mode``
    остаётся SSOT для режима, а ``data_tier`` отделяет FULL от PFO/GAP и позволяет
    NF-фазам не пользоваться размытым ``is_not_full()``.
    """

    calculated_keyword: CalculatedKeyword
    position_profile: list[PositionProfilePoint] | None
    stored_mode: KeywordStrategyMode
    target_place_matrix: TargetPlaceMatrix
    next_state: list[NextState] = field(default_factory=lambda: list[NextState]())
    history_target_place: list[NextTargetPlace] = field(
        default_factory=lambda: list[NextTargetPlace]()
    )

    @property
    def keyword_setting_id(self) -> int:
        """``keyword_setting_original_id`` (0 если нет id)."""
        return int(self.calculated_keyword.keyword_setting_original_id or 0)

    @property
    def current_mode(self) -> KeywordStrategyMode:
        """Текущий рабочий режим: хвост ``next_state`` или ``stored_mode``."""
        if self.next_state:
            return self.next_state[-1].new_mode.to_strategy_mode()
        return self.stored_mode

    @current_mode.setter
    def current_mode(self, step: NextState) -> None:
        """Append перехода или validate-команда ``NOT_FULL_ACTIVATE``."""
        if step.new_mode is KeywordMode.NOT_FULL_ACTIVATE:
            self._validate_not_full_state(step.executor_name)
            return
        strategy = step.new_mode.to_strategy_mode()
        if strategy == self.current_mode:
            return
        self.next_state.append(step)

    @property
    def current_target_place(self) -> int:
        """Текущий target_place: хвост history или значение из keyword setting."""
        if self.history_target_place:
            return self.history_target_place[-1].new_target_place
        place = self.calculated_keyword.target_place
        return 0 if place is None else int(place)

    @current_target_place.setter
    def current_target_place(self, step: NextTargetPlace) -> None:
        """Append target_place; skip если значение не изменилось."""
        if step.new_target_place == self.current_target_place:
            return
        self.history_target_place.append(step)
        self.calculated_keyword.keyword_setting.target_place = step.new_target_place

    @property
    def target_place(self) -> int | None:
        """Текущий ``target_place`` ключа."""
        return self.calculated_keyword.target_place

    @property
    def hard_status(self) -> int:
        return self.calculated_keyword.hard_status

    @property
    def ladder_states(self) -> tuple[KeywordV3LadderState, ...]:
        """Плоская проекция матрицы для planner/collector."""
        return self.target_place_matrix.states

    @property
    def data_tier(self) -> KeywordV3DataTier:
        """FULL/PFO/GAP по профилю позиций и operational ``pay_for_order``.

        Возвращает классификацию, которую используют NF validate/migrate/plan-fact,
        а также ladder-ветки, чтобы явно различать:
        - ``FULL``: ключ следует ladder-профилю;
        - ``PFO``: профиля нет, но есть operational PFO;
        - ``GAP``: нет ни профиля, ни operational PFO.
        """
        return resolve_keyword_v3_data_tier(
            position_profile=self.position_profile,
            keyword=self.calculated_keyword,
        )

    def is_no_data_singleton(self) -> bool:
        """NO DATA singleton: единственный synthetic MIN_CPA-state с fact pay_for_order."""
        states = self.ladder_states
        return (
            len(states) == 1
            and states[0].synthetic_no_data
        )

    def _validate_not_full_state(self, executor_name: str) -> None:
        """PFO/GAP + active: принудительно свести режим к ``MIN_CPA``.

        FULL ключи не трогаем. OFF тоже оставляем без изменений: ``NOT_FULL_ACTIVATE``
        не должен оживлять выключенные ключи. Эта команда используется только для
        активных NO-CH/PFO/GAP ключей, которым далее нужны NF-migrate и NF-plan-fact.
        """
        if self.data_tier == KeywordV3DataTier.FULL:
            return
        if self.current_mode == KeywordStrategyMode.OFF:
            return
        if self.current_mode != KeywordStrategyMode.MIN_CPA:
            self.current_mode = NextState(
                new_mode=KeywordMode.MIN_CPA,
                executor_name=executor_name,
            )

    def apply_ladder_state(
        self,
        state: KeywordV3LadderState,
        *,
        executor_name: str,
    ) -> None:
        """Сменить режим и ``target_place`` атомарно из ladder-state."""
        self.current_mode = NextState(
            new_mode=KeywordMode.from_strategy_mode(state.strategy_mode),
            executor_name=executor_name,
        )
        target_place = (
            None
            if state.strategy_mode == KeywordStrategyMode.OFF
            else state.target_position
        )
        setting = self.calculated_keyword.keyword_setting
        setting.strategy_mode = state.strategy_mode
        setting.target_place = target_place
        if target_place is not None:
            self.current_target_place = NextTargetPlace(
                new_target_place=int(target_place),
                executor_name=executor_name,
            )

    @property
    def context(self) -> KeywordV3Context:
        """Legacy ``KeywordV3Context`` для rollout planner."""
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
            KeywordV3Context,
        )

        return KeywordV3Context(
            keyword=self.calculated_keyword,
            position_profile=self.position_profile,
        )

    def to_prepared_row(self) -> KeywordPreparedRow:
        """Legacy строка ``KeywordsPreparedList.rows``."""
        return KeywordPreparedRow(
            keyword=self.calculated_keyword,
            position_profile=self.position_profile,
            stored_mode=self.stored_mode,
            active_mode=self.current_mode,
            states=self.ladder_states,
        )

    @classmethod
    def from_prepared_row(cls, row: KeywordPreparedRow) -> KeywordDTO:
        """Обратная совместимость со старыми ``KeywordPreparedRow``."""
        dto = cls(
            calculated_keyword=row.keyword,
            position_profile=row.position_profile,
            stored_mode=row.stored_mode,
            target_place_matrix=TargetPlaceMatrix(row.states),
        )
        if row.active_mode != row.stored_mode:
            dto.current_mode = NextState(
                new_mode=KeywordMode.from_strategy_mode(row.active_mode),
                executor_name="from_prepared_row",
            )
        return dto

    @classmethod
    def from_context(
        cls,
        ctx: KeywordV3Context,
        *,
        ladder_states: tuple[KeywordV3LadderState, ...],
    ) -> KeywordDTO:
        """Сборка из ``KeywordV3Context`` + ladder states."""
        stored_mode = stored_strategy_mode(ctx.keyword)
        return cls(
            calculated_keyword=ctx.keyword,
            position_profile=ctx.position_profile,
            stored_mode=stored_mode,
            target_place_matrix=TargetPlaceMatrix(ladder_states),
        )
