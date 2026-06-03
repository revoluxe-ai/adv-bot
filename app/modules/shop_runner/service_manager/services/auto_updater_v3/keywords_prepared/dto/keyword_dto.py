"""DTO одного ключa V3: CalculatedKeyword + матрица CH + цепочка NextState на тике."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    stored_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.next_state import (
    NextState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.target_place_matrix import (
    TargetPlaceMatrix,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.keyword_prepared_row import (
        KeywordPreparedRow,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )


class KeywordDTO:
    """Аккумулятор данных ключa на тик V3.

    Текущий режим — SSOT: последний ``NextState`` в ``_next_state`` или ``stored_mode``.
    Запись только через ``current_mode = NextState(...)``.
    """

    __slots__ = (
        "_calculated_keyword",
        "_position_profile",
        "_stored_mode",
        "_target_place_matrix",
        "_next_state",
    )

    def __init__(
        self,
        calculated_keyword: CalculatedKeyword,
        *,
        position_profile: list[PositionProfilePoint] | None,
        stored_mode: KeywordStrategyMode,
        target_place_matrix: TargetPlaceMatrix,
    ) -> None:
        self._calculated_keyword = calculated_keyword
        self._position_profile = position_profile
        self._stored_mode = stored_mode
        self._target_place_matrix = target_place_matrix
        self._next_state: list[NextState] = []

    @property
    def keyword_setting_id(self) -> int:
        return int(self._calculated_keyword.keyword_setting_original_id or 0)

    @property
    def text(self) -> str:
        return self._calculated_keyword.text

    @property
    def stored_mode(self) -> KeywordStrategyMode:
        """Режим из PG/Redis на старте тика."""
        return self._stored_mode

    @property
    def current_mode(self) -> KeywordStrategyMode:
        """Текущий рабочий режим: хвост ``_next_state`` или ``stored_mode``."""
        if self._next_state:
            return self._next_state[-1].new_mode
        return self._stored_mode

    @current_mode.setter
    def current_mode(self, step: NextState) -> None:
        """Append перехода (без dedup)."""
        self._next_state.append(step)

    @property
    def next_state(self) -> list[NextState]:
        """In-place цепочка переходов на текущем тике."""
        return self._next_state

    @property
    def target_place_matrix(self) -> TargetPlaceMatrix:
        """Ladder-матрица target_place/CPO из CH."""
        return self._target_place_matrix

    @property
    def ladder_states(self) -> tuple[KeywordV3LadderState, ...]:
        """Плоская проекция матрицы для planner/collector."""
        return self._target_place_matrix.states

    @property
    def position_profile(self) -> list[PositionProfilePoint] | None:
        return self._position_profile

    @property
    def hard_status(self) -> int:
        return self._calculated_keyword.hard_status

    @property
    def rating(self) -> float | None:
        return self._calculated_keyword.rating

    @property
    def context(self) -> KeywordV3Context:
        """Legacy ``KeywordV3Context`` для rollout planner."""
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
            KeywordV3Context,
        )

        return KeywordV3Context(
            keyword=self._calculated_keyword,
            position_profile=self._position_profile,
        )

    @property
    def calculated_keyword(self) -> CalculatedKeyword:
        """Legacy: доступ к ``CalculatedKeyword`` (миграция planner/ledger)."""
        return self._calculated_keyword

    def with_target_place_matrix(self, matrix: TargetPlaceMatrix) -> KeywordDTO:
        """Копия с обновлённой CH-матрицей после refresh tick state."""
        copy = KeywordDTO(
            self._calculated_keyword,
            position_profile=self._position_profile,
            stored_mode=self._stored_mode,
            target_place_matrix=matrix,
        )
        copy._next_state = list(self._next_state)
        return copy

    def to_prepared_row(self) -> KeywordPreparedRow:
        """Legacy строка ``KeywordsPreparedList.rows``."""
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto.keyword_prepared_row import (
            KeywordPreparedRow,
        )

        return KeywordPreparedRow(
            keyword=self._calculated_keyword,
            position_profile=self._position_profile,
            stored_mode=self._stored_mode,
            active_mode=self.current_mode,
            states=self.ladder_states,
        )

    @classmethod
    def from_prepared_row(cls, row: KeywordPreparedRow) -> KeywordDTO:
        """Обратная совместимость со старыми ``KeywordPreparedRow``."""
        dto = cls(
            row.keyword,
            position_profile=row.position_profile,
            stored_mode=row.stored_mode,
            target_place_matrix=TargetPlaceMatrix(row.states),
        )
        if row.active_mode != row.stored_mode:
            dto.current_mode = NextState(
                new_mode=row.active_mode,
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
        stored = stored_strategy_mode(ctx.keyword)
        return cls(
            ctx.keyword,
            position_profile=ctx.position_profile,
            stored_mode=stored,
            target_place_matrix=TargetPlaceMatrix(ladder_states),
        )
