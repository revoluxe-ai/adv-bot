"""CampaignsInfoV2Adapter raw read strict boundary tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.adapter import (
    CampaignsInfoV2Adapter,
)

pytestmark = pytest.mark.unit


def _adapter() -> CampaignsInfoV2Adapter:
    auth_handler = MagicMock()
    auth_handler.shop_id = "shop-test"
    auth_handler.get_proxy_client = AsyncMock(return_value=MagicMock())
    request_limit_manager = MagicMock()
    request_limit_manager.api_call_state = {}
    return CampaignsInfoV2Adapter(
        "https://example.test", auth_handler, request_limit_manager
    )


@pytest.mark.asyncio
async def test_raw_method_fails_on_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _adapter()

    async def _bad_response(*_args: object, **_kwargs: object) -> MagicMock:
        resp = MagicMock()
        resp.content = b"not-json"
        return resp

    monkeypatch.setattr(
        "app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.adapter.with_raise_errors",
        AsyncMock(side_effect=_bad_response),
    )

    with pytest.raises(ValueError, match="not valid JSON"):
        await adapter.get_campaigns_info_raw_by_ids([101])


@pytest.mark.asyncio
async def test_raw_method_fails_on_missing_adverts(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _adapter()

    async def _empty_object(*_args: object, **_kwargs: object) -> MagicMock:
        resp = MagicMock()
        resp.content = json.dumps({}).encode()
        return resp

    monkeypatch.setattr(
        "app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.adapter.with_raise_errors",
        AsyncMock(side_effect=_empty_object),
    )

    with pytest.raises(ValueError, match="missing adverts"):
        await adapter.get_campaigns_info_raw_by_ids([101])


@pytest.mark.asyncio
async def test_raw_method_fails_on_advert_without_id(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _adapter()

    async def _no_id(*_args: object, **_kwargs: object) -> MagicMock:
        resp = MagicMock()
        resp.content = json.dumps({"adverts": [{"bid_type": "unified"}]}).encode()
        return resp

    monkeypatch.setattr(
        "app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.adapter.with_raise_errors",
        AsyncMock(side_effect=_no_id),
    )

    with pytest.raises(ValueError, match="missing id"):
        await adapter.get_campaigns_info_raw_by_ids([101])


@pytest.mark.asyncio
async def test_raw_method_returns_valid_adverts(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _adapter()

    async def _ok(*_args: object, **_kwargs: object) -> MagicMock:
        resp = MagicMock()
        resp.content = json.dumps(
            {"adverts": [{"id": 101, "bid_type": "unified"}]}
        ).encode()
        return resp

    monkeypatch.setattr(
        "app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.adapter.with_raise_errors",
        AsyncMock(side_effect=_ok),
    )

    items = await adapter.get_campaigns_info_raw_by_ids([101])
    assert len(items) == 1
    assert items[0]["id"] == 101
