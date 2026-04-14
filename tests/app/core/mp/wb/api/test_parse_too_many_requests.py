"""Unit tests for parse_too_many_requests_error."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from app.core.mp.wb.api.utils import parse_too_many_requests_error


def _resp(headers: dict[str, str]) -> MagicMock:
    r = MagicMock()
    r.headers = headers
    return r


def test_parse_uses_retry_only_when_no_reset() -> None:
    assert (
        parse_too_many_requests_error(
            _resp({"X-RateLimit-Retry": "2"}),
        )
        == 2
    )


def test_parse_max_of_retry_and_small_reset() -> None:
    """WB s2s: Retry=1, Reset=13 → ждём не меньше окна (13 с)."""
    assert (
        parse_too_many_requests_error(
            _resp(
                {
                    "X-RateLimit-Retry": "1",
                    "X-RateLimit-Reset": "13",
                }
            )
        )
        == 13
    )


def test_parse_unix_reset() -> None:
    future = int(time.time()) + 42
    assert parse_too_many_requests_error(
        _resp(
            {
                "X-RateLimit-Retry": "1",
                "X-RateLimit-Reset": str(future),
            }
        )
    ) in (41, 42, 43)


def test_parse_caps_at_120() -> None:
    assert (
        parse_too_many_requests_error(
            _resp(
                {
                    "X-RateLimit-Retry": "1",
                    "X-RateLimit-Reset": "500",
                }
            )
        )
        == 120
    )


def test_parse_missing_headers_default() -> None:
    r = MagicMock()
    r.headers = None
    assert parse_too_many_requests_error(r) == 5
