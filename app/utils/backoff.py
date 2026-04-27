"""Exponential backoff for asyncio retry loops (single source of truth for the formula)."""

from __future__ import annotations

import random


def exponential_retry_delay_seconds(
    attempt: int,
    *,
    base_seconds: int,
    max_seconds: int,
) -> float:
    """Return ``min(max_seconds, base_seconds * 2 ** (attempt - 1))``."""
    exp = base_seconds * (2 ** max(0, attempt - 1))
    return float(min(max_seconds, exp))


def retry_delay_with_jitter(
    attempt: int,
    *,
    base_seconds: int,
    max_seconds: int,
    jitter_ratio: float = 0.3,
) -> float:
    """Exponential backoff capped at ``max_seconds``, plus uniform jitter.

    Jitter spans ``[0, jitter_ratio * exp]`` where ``exp`` is the capped exponential
    delay, then the sum is capped again at ``max_seconds`` (same as wb_adv_updater runner).
    """
    exp = exponential_retry_delay_seconds(
        attempt, base_seconds=base_seconds, max_seconds=max_seconds
    )
    if jitter_ratio <= 0.0:
        return exp
    jitter = random.uniform(0.0, jitter_ratio * exp)
    return min(float(max_seconds), exp + jitter)
