from __future__ import annotations

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
