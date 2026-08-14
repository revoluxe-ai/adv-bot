"""Terminal pause Авто при исчерпании теста полок (INC-AUTO-SHELF-PAUSE-01).

Shelf owns detect + PG SoT; activity-control owns WB pause/start + Redis reason
mirror. Spec: ``auto-shelf-exhausted-pause``.
"""

from .decision import (
    DEFAULT_RETEST_INTERVAL_DAYS,
    ResolveCpoKind,
    TerminalDetectInput,
    TerminalDetectResult,
    clear_our_block_due_to_calendar,
    clear_our_block_due_to_plan_fit,
    gate_allows_shelf_exhausted_path,
    has_resolve_cpo_plan_fit,
    is_shelf_exhausted_reason,
    should_latch_terminal_block,
)
from .messages import (
    RESET_PAUSE_BUTTON_TEXT,
    build_shelf_exhausted_pause_message,
    build_shelf_exhausted_reset_callback_data,
)

__all__ = [
    "DEFAULT_RETEST_INTERVAL_DAYS",
    "RESET_PAUSE_BUTTON_TEXT",
    "ResolveCpoKind",
    "TerminalDetectInput",
    "TerminalDetectResult",
    "build_shelf_exhausted_pause_message",
    "build_shelf_exhausted_reset_callback_data",
    "clear_our_block_due_to_calendar",
    "clear_our_block_due_to_plan_fit",
    "gate_allows_shelf_exhausted_path",
    "has_resolve_cpo_plan_fit",
    "is_shelf_exhausted_reason",
    "should_latch_terminal_block",
]
