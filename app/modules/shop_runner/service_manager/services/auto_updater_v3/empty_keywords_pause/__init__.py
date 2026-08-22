"""Pause-on-empty-keywords: detect after OFF, pause, notify pause/resume.

Spec: ``pause-on-empty-keywords``. ADL: ``empty-keywords-pause-write-path``.
Resume/re-enable notify — sibling of pause notify after delivered episode.
"""

from .apply_hook import maybe_set_empty_keywords_pause_intent
from .decision import (
    count_active_keywords,
    had_force_off_action,
    should_request_empty_keywords_pause_intent,
)
from .intent import EmptyKeywordsPauseIntentManager
from .messages import (
    build_empty_keywords_pause_message,
    build_empty_keywords_resume_message,
)
from .notify import notify_empty_keywords_pause, notify_empty_keywords_resume

__all__ = [
    "EmptyKeywordsPauseIntentManager",
    "build_empty_keywords_pause_message",
    "build_empty_keywords_resume_message",
    "count_active_keywords",
    "had_force_off_action",
    "maybe_set_empty_keywords_pause_intent",
    "notify_empty_keywords_pause",
    "notify_empty_keywords_resume",
    "should_request_empty_keywords_pause_intent",
]
