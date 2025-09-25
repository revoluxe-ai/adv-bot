import pytest

from app.core.mp.wb.mixins.bid_update_mixin import BidUpdateMixin


class FakePM:
    def __init__(self):
        self.called = None

    async def update_bids(self, shop_id, batch):
        self.called = (shop_id, batch)


@pytest.mark.asyncio
async def test_bidupdate_mixin():
    pm = FakePM()
    mix = BidUpdateMixin("shopZ", pm)
    await mix.update_bids({"x": 1})
    assert pm.called == ("shopZ", {"x": 1})


