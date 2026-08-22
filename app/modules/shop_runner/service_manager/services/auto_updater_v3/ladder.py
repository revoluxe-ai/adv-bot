"""Aggression ladder: KeywordStrategyMode as integer levels."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


def mode_level(mode: KeywordStrategyMode) -> int:
    return int(mode)


def clamp_level(level: int) -> KeywordStrategyMode:
    return KeywordStrategyMode(max(0, min(3, level)))


def can_step_up(current: KeywordStrategyMode) -> bool:
    return current < KeywordStrategyMode.MAX_CONVERSION


def can_step_down(current: KeywordStrategyMode) -> bool:
    return current > KeywordStrategyMode.OFF


def step_up(current: KeywordStrategyMode) -> KeywordStrategyMode | None:
    if not can_step_up(current):
        return None
    return clamp_level(mode_level(current) + 1)


def step_down(current: KeywordStrategyMode) -> KeywordStrategyMode | None:
    if not can_step_down(current):
        return None
    return clamp_level(mode_level(current) - 1)


def is_new_keyword_for_v3(
    *,
    has_ad_stats: bool,
) -> bool:
    """New/unproven keys must enter at MIN_CPA only (no skip to OPTIMUM/MAX)."""
    return not has_ad_stats
