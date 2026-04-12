"""Unit tests for MinBidsAdapter batch split (bisection) on invalid nm_ids."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.mp.wb.api.adapter.promotion_client.min_bids.adapter import (
    MinBidsAdapter,
    _is_nms_not_belong_to_advert_error,
)
from app.core.mp.wb.api.adapter.promotion_client.min_bids.command import (
    GetMinBidsCommand,
    GetMinBidsCommandItem,
)
from app.core.mp.wb.api.adapter.promotion_client.min_bids.dto import MinBidForNmid
from app.core.mp.wb.api.excs import BadRequestError
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType


def _nms_not_belong_detail(*, request_id: str | None = None) -> str:
    payload: dict[str, object] = {
        "title": "Bad Request",
        "detail": "some nms are not belong to advert",
    }
    if request_id is not None:
        payload["request_id"] = request_id
    return json.dumps(payload)


@pytest.fixture
def mock_auth_client_handler() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_request_limit_manager() -> MagicMock:
    mock = MagicMock(spec=RequestLimitManager)
    mock.api_call_state = {}
    return mock


@pytest.fixture
def min_bids_adapter(
    mock_auth_client_handler: AsyncMock,
    mock_request_limit_manager: MagicMock,
) -> MinBidsAdapter:
    return MinBidsAdapter(
        base_url="http://test",
        auth_client_handler=mock_auth_client_handler,
        request_limit_manager=mock_request_limit_manager,
    )


def test_is_nms_not_belong_to_advert_error_json() -> None:
    exc = BadRequestError(_nms_not_belong_detail(request_id="rid-1"))
    assert _is_nms_not_belong_to_advert_error(exc) is True


def test_is_nms_not_belong_to_advert_error_plain_string() -> None:
    exc = BadRequestError("some nms are not belong to advert")
    assert _is_nms_not_belong_to_advert_error(exc) is True


def test_is_nms_not_belong_to_advert_error_other_bad_request() -> None:
    exc = BadRequestError(json.dumps({"title": "x", "detail": "other"}))
    assert _is_nms_not_belong_to_advert_error(exc) is False


def test_is_nms_not_belong_to_advert_error_none_detail() -> None:
    exc = BadRequestError(None)
    assert _is_nms_not_belong_to_advert_error(exc) is False


@pytest.mark.asyncio
async def test_post_api_success_without_split(
    min_bids_adapter: MinBidsAdapter,
) -> None:
    item = GetMinBidsCommandItem(
        adv_id=1,
        nmids=[10, 20],
        placement_type=AdvPlacementType.AUTO_ADV,
    )
    expected = [
        MinBidForNmid(
            nmid=10,
            placement_type=AdvPlacementType.AUTO_ADV,
            min_cpm=5,
        ),
        MinBidForNmid(
            nmid=20,
            placement_type=AdvPlacementType.AUTO_ADV,
            min_cpm=7,
        ),
    ]
    with patch.object(
        min_bids_adapter,
        "_http_post_min_bids",
        new_callable=AsyncMock,
        return_value=expected,
    ):
        out = await min_bids_adapter.post_api_advert_v1_bids_min(
            GetMinBidsCommand(items=[item])
        )
    assert out == expected


@pytest.mark.asyncio
async def test_bisect_batch_then_partial_success(
    min_bids_adapter: MinBidsAdapter,
) -> None:
    """Batch fails with nms error; one half is bad nmid (singleton), other succeeds."""
    bad_nmid = 999
    good_nmid = 1000
    item = GetMinBidsCommandItem(
        adv_id=42,
        nmids=[bad_nmid, good_nmid],
        placement_type=AdvPlacementType.AUTO_ADV,
    )
    good_bid = MinBidForNmid(
        nmid=good_nmid,
        placement_type=AdvPlacementType.AUTO_ADV,
        min_cpm=11,
    )

    async def fake_http(ci: GetMinBidsCommandItem) -> list[MinBidForNmid]:
        if set(ci.nmids) == {bad_nmid, good_nmid}:
            raise BadRequestError(_nms_not_belong_detail())
        if ci.nmids == [bad_nmid]:
            raise BadRequestError(_nms_not_belong_detail())
        if ci.nmids == [good_nmid]:
            return [good_bid]
        raise AssertionError(f"unexpected nmids {ci.nmids}")

    with patch.object(
        min_bids_adapter,
        "_http_post_min_bids",
        side_effect=fake_http,
    ):
        out = await min_bids_adapter.post_api_advert_v1_bids_min(
            GetMinBidsCommand(items=[item])
        )
    assert out == [good_bid]


@pytest.mark.asyncio
async def test_singleton_invalid_nmid_logs_error_and_returns_empty(
    caplog: pytest.LogCaptureFixture,
    min_bids_adapter: MinBidsAdapter,
) -> None:
    caplog.set_level("ERROR")
    nmid = 777
    item = GetMinBidsCommandItem(
        adv_id=99,
        nmids=[nmid],
        placement_type=AdvPlacementType.SEARCH_ADV,
    )

    async def fake_http(_ci: GetMinBidsCommandItem) -> list[MinBidForNmid]:
        raise BadRequestError(_nms_not_belong_detail(request_id="req-xyz"))

    with patch.object(
        min_bids_adapter,
        "_http_post_min_bids",
        side_effect=fake_http,
    ):
        out = await min_bids_adapter.post_api_advert_v1_bids_min(
            GetMinBidsCommand(items=[item])
        )
    assert out == []
    assert "min_bids invalid nmid for advert (dropped)" in caplog.text
    assert "req-xyz" in caplog.text
    assert str(nmid) in caplog.text


@pytest.mark.asyncio
async def test_unrelated_bad_request_propagates(
    min_bids_adapter: MinBidsAdapter,
) -> None:
    item = GetMinBidsCommandItem(
        adv_id=1,
        nmids=[1],
        placement_type=AdvPlacementType.AUTO_ADV,
    )

    async def fake_http(_ci: GetMinBidsCommandItem) -> list[MinBidForNmid]:
        raise BadRequestError(json.dumps({"title": "x", "detail": "other error"}))

    with (
        patch.object(
            min_bids_adapter,
            "_http_post_min_bids",
            side_effect=fake_http,
        ),
        pytest.raises(BadRequestError),
    ):
        await min_bids_adapter.post_api_advert_v1_bids_min(
            GetMinBidsCommand(items=[item])
        )


@pytest.mark.asyncio
async def test_empty_nmids_returns_empty(
    min_bids_adapter: MinBidsAdapter,
) -> None:
    item = GetMinBidsCommandItem(
        adv_id=1,
        nmids=[],
        placement_type=AdvPlacementType.AUTO_ADV,
    )
    with patch.object(
        min_bids_adapter,
        "_http_post_min_bids",
        new_callable=AsyncMock,
    ) as mock_http:
        out = await min_bids_adapter.post_api_advert_v1_bids_min(
            GetMinBidsCommand(items=[item])
        )
    assert out == []
    mock_http.assert_not_called()
