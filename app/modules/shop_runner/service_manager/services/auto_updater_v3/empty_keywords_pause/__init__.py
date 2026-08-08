"""Pause-on-empty-keywords: detect after OFF, pause as next shop-runner step.

Spec: ``pause-on-empty-keywords``. ADL: ``empty-keywords-pause-write-path``.
"""

from .apply_hook import maybe_set_empty_keywords_pause_intent
from .decision import (
    STATS_WINDOW_DAYS_MAX,
    count_active_keywords,
    had_force_off_action,
    is_empty_keywords_reason,
    should_request_empty_keywords_pause_intent,
    stats_window_compatible_with_recheck,
)
from .intent import EmptyKeywordsPauseIntentManager
from .messages import build_empty_keywords_pause_message
from .notify import notify_empty_keywords_pause

__all__ = [
    "STATS_WINDOW_DAYS_MAX",
    "EmptyKeywordsPauseIntentManager",
    "build_empty_keywords_pause_message",
    "count_active_keywords",
    "had_force_off_action",
    "is_empty_keywords_reason",
    "maybe_set_empty_keywords_pause_intent",
    "notify_empty_keywords_pause",
    "should_request_empty_keywords_pause_intent",
    "stats_window_compatible_with_recheck",
]
