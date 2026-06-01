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
    """Exponential backoff capped at ``max_seconds``, with proportional jitter.

    Draws uniformly from ``[exp*(1-j), min(max_seconds, exp*(1+j))]`` where ``exp`` is
    the capped exponential delay and ``j`` is ``jitter_ratio``. Below the cap this
    spreads retries around ``exp``; at the ceiling (``exp == max_seconds``) the interval
    becomes ``[max_seconds*(1-j), max_seconds]``, so jitter still separates workers
    instead of collapsing to a single delay after ``min(..., exp + jitter)``.
    """
    exp = exponential_retry_delay_seconds(
        attempt, base_seconds=base_seconds, max_seconds=max_seconds
    )
    if jitter_ratio <= 0.0:
        return exp
    low = max(0.0, exp * (1.0 - jitter_ratio))
    high = min(float(max_seconds), exp * (1.0 + jitter_ratio))
    if high <= low:
        return exp
    return random.uniform(low, high)
