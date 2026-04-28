from __future__ import annotations

from unittest.mock import patch

import pytest

from app.utils import backoff


@pytest.mark.unit
def test_exponential_retry_delay_matches_expected_series() -> None:
    assert backoff.exponential_retry_delay_seconds(
        1, base_seconds=10, max_seconds=120
    ) == 10.0
    assert backoff.exponential_retry_delay_seconds(
        2, base_seconds=10, max_seconds=120
    ) == 20.0
    assert backoff.exponential_retry_delay_seconds(
        100, base_seconds=10, max_seconds=120
    ) == 120.0


@pytest.mark.unit
def test_retry_delay_with_jitter_zero_ratio_equals_exponential() -> None:
    exp = backoff.exponential_retry_delay_seconds(
        3, base_seconds=5, max_seconds=300
    )
    assert backoff.retry_delay_with_jitter(
        3,
        base_seconds=5,
        max_seconds=300,
        jitter_ratio=0.0,
    ) == exp


@pytest.mark.unit
def test_retry_delay_with_jitter_at_ceiling_uniform_range_not_point_mass() -> None:
    """At max_seconds, jitter must vary in [max*(1-j), max], not always exactly max."""
    captured: list[tuple[float, float]] = []

    def _capture_uniform(low: float, high: float) -> float:
        captured.append((low, high))
        return low

    max_s = 120
    j = 0.3
    with patch.object(backoff.random, "uniform", side_effect=_capture_uniform):
        backoff.retry_delay_with_jitter(
            99,
            base_seconds=10,
            max_seconds=max_s,
            jitter_ratio=j,
        )

    assert len(captured) == 1
    low, high = captured[0]
    assert low == pytest.approx(max_s * (1.0 - j))
    assert high == pytest.approx(float(max_s))
    assert low < high


@pytest.mark.unit
def test_retry_delay_with_jitter_below_ceiling_uniform_range() -> None:
    captured: list[tuple[float, float]] = []

    def _capture_uniform(low: float, high: float) -> float:
        captured.append((low, high))
        return low

    with patch.object(backoff.random, "uniform", side_effect=_capture_uniform):
        backoff.retry_delay_with_jitter(
            3,
            base_seconds=10,
            max_seconds=300,
            jitter_ratio=0.3,
        )

    assert len(captured) == 1
    low, high = captured[0]
    # attempt 3 -> exp = 40
    assert low == pytest.approx(28.0)
    assert high == pytest.approx(52.0)
