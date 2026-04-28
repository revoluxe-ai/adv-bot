"""Unit tests for parse_min_bid_from_bad_request_detail."""

from __future__ import annotations

import pytest

from app.core.mp.wb.api.domain_managers.promotion.methods.set_cluster_bids.parse_min_bid_from_error import (
    parse_min_bid_from_bad_request_detail,
)


@pytest.mark.unit
def test_parse_wrong_bid_value_legacy_shape() -> None:
    detail = (
        '{"errors":[{"detail":"wrong bid value min: 42 for field bids[0].bid",'
        '"field":"bids[0].bid"}],"status":400,"title":"Invalid request body"}'
    )
    assert parse_min_bid_from_bad_request_detail(detail) == 42


@pytest.mark.unit
def test_parse_returns_none_without_wrong_bid() -> None:
    detail = '{"errors":[{"detail":"other error","field":"x"}],"status":400}'
    assert parse_min_bid_from_bad_request_detail(detail) is None


@pytest.mark.unit
def test_parse_plain_text_wrong_bid() -> None:
    detail = 'wrong bid value min: 99'
    assert parse_min_bid_from_bad_request_detail(detail) == 99
