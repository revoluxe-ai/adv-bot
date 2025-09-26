import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.core.mp.wb.base_wb_api import BaseWBApi
from app.core.mp.wb.mixins.bid_update import MinBidMixin, CurrentBidMixin, BidUpdateMixin


@pytest.fixture
def mock_adapter_factory():
    factory = Mock()
    adapter = Mock()
    adapter.get_min_bids = AsyncMock(return_value={})
    adapter.get_current_bids = AsyncMock(return_value={})
    adapter.update_bids = AsyncMock()
    factory.get_adapter.return_value = adapter
    return factory, adapter


@pytest.mark.asyncio
async def test_minbid_mixin_delegates(mock_adapter_factory):
    factory, adapter = mock_adapter_factory
    with patch.object(BaseWBApi, 'adapter_factory', new=factory):
        mix = MinBidMixin("s1")
        adapter.get_min_bids.return_value = {7: 1, 8: 1}
        res = await mix.get_min_bids(10, [7, 8])
        assert res == {7: 1, 8: 1}
        adapter.get_min_bids.assert_called_once_with(10, [7, 8])


@pytest.mark.asyncio
async def test_currentbid_mixin_delegates(mock_adapter_factory):
    factory, adapter = mock_adapter_factory
    with patch.object(BaseWBApi, 'adapter_factory', new=factory):
        mix = CurrentBidMixin("s2")
        adapter.get_current_bids.return_value = {3: 2}
        res = await mix.get_current_bids(11, [3])
        assert res == {3: 2}
        adapter.get_current_bids.assert_called_once_with(11, [3])


@pytest.mark.asyncio
async def test_updatebid_mixin_delegates(mock_adapter_factory):
    factory, adapter = mock_adapter_factory
    with patch.object(BaseWBApi, 'adapter_factory', new=factory):
        mix = BidUpdateMixin("s3")
        await mix.update_bids({"a": 1})
        adapter.update_bids.assert_called_once_with({"a": 1})


