"""Tests for CpmSourcesResolver.get_all_sources: returns set_bid, api, bid_log per text."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.cpm_sources_resolver.dto import AllCpmSourcesPerText
from app.modules.cpm_sources_resolver.resolver import CpmSourcesResolver


@pytest.mark.asyncio
async def test_get_all_sources_returns_set_bid_bid_log_and_api() -> None:
    """When maps and api_bids have data for a text, get_all_sources returns all three in AllCpmSourcesPerText."""
    text = "платье"
    ts = datetime(2025, 3, 1, 12, 0)
    set_bid_map = {text: (100.0, ts)}
    bid_log_map = {text: (80.0, ts)}
    api_bids = {text: 90}
    complex_adv = None
    with (
        patch(
            "app.modules.cpm_sources_resolver.resolver._fetch_set_bid_and_bid_log_maps",
            new_callable=AsyncMock,
            return_value=(set_bid_map, bid_log_map),
        ),
        patch(
            "app.modules.cpm_sources_resolver.resolver._fetch_api_bids",
            new_callable=AsyncMock,
            return_value=api_bids,
        ),
    ):
        result = await CpmSourcesResolver.get_all_sources(complex_adv, [text])
    assert text in result
    row = result[text]
    assert isinstance(row, AllCpmSourcesPerText)
    assert row.text == text
    assert row.cpm_set_bid == 100
    assert row.cpm_set_bid_date == ts
    assert row.cpm_from_api == 90
    assert row.cpm_from_bid_log == 80.0
    assert row.cpm_from_bid_log_date == ts


@pytest.mark.asyncio
async def test_get_all_sources_empty_texts_returns_empty_dict() -> None:
    """get_all_sources([], []) returns {}."""
    result = await CpmSourcesResolver.get_all_sources(None, [])
    assert result == {}
