import pytest

from app.core.mp.wb.mixins.min_bid_mixin import MinBidMixin


class FakePM:
    def __init__(self):
        self.called = None

    async def get_min_bids(self, shop_id, adv_id, nmids):
        self.called = (shop_id, adv_id, tuple(nmids))
        return {n: 5 for n in nmids}


@pytest.mark.asyncio
async def test_minbid_mixin():
    pm = FakePM()
    mix = MinBidMixin("shopX", pm)
    res = await mix.get_min_bids(7, [1, 2])
    assert res == {1: 5, 2: 5}
    assert pm.called == ("shopX", 7, (1, 2))


