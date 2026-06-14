"""Operable keywords V3: фильтр hard_status 1|2.

Источник истины — ``hard_status`` из БД; ``strategy_mode`` подтягивается к нему:
``HardStatusValidateExecutor`` (preamble фаза V) — авто (1) → ``OFF``.

Ограничение mode по tier без CH-профиля — **NF** (``NotFullValidateExecutor`` + tp migrate/plan-fact):
нет ``position_profile`` → MIN; ``target_place`` — migrate (0→current) и plan-fact ±1. Legacy ``cap_down``
не используется (есть профиль → лестница из CH). См. ``docks/V3_UPDATER_VALIDATION.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    hard_status_for_strategy_mode,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

HARD_STATUS_AUTO_MODE = 1
HARD_STATUS_WHITE_LIST = 2
HARD_STATUS_MODE_SYNC_REASON = "hard_status_mode_sync"
HARD_STATUS_PERSIST_NORMALIZE_REASON = "hard_status_persist_normalize"


def is_v3_operable_hard_status(hard_status: int) -> bool:
    """Ladder UP/DOWN/FORCE_OFF: только авто (1) и белый список (2)."""
    return int(hard_status) in (HARD_STATUS_AUTO_MODE, HARD_STATUS_WHITE_LIST)


def is_v3_operable_keyword(keyword: CalculatedKeyword) -> bool:
    """Ключ участвует в V3 ladder-фазах."""
    return is_v3_operable_hard_status(keyword.hard_status)


def expected_hard_status_for_strategy_mode(
    mode: KeywordStrategyMode,
) -> int:
    """OFF → 1, любой активный mode → 2 (контракт applier)."""
    return hard_status_for_strategy_mode(mode)


def hard_status_matches_strategy_mode(
    *,
    strategy_mode: KeywordStrategyMode,
    hard_status: int,
) -> bool:
    """``hard_status`` согласован с ``strategy_mode`` для operable-ключей."""
    return int(hard_status) == expected_hard_status_for_strategy_mode(strategy_mode)


def filter_operable_v3_contexts(
    contexts: list[KeywordV3Context],
) -> list[KeywordV3Context]:
    """Оставить только контексты с ``hard_status in {1, 2}``."""
    return [ctx for ctx in contexts if is_v3_operable_keyword(ctx.keyword)]
