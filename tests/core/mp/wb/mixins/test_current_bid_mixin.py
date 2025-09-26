import pytest

from app.core.mp.wb.mixins.current_bid_mixin import CurrentBidMixin


class FakePM:
    def __init__(self):
        self.called = None

    async def get_current_bids(self, shop_id, adv_id, nmids):
        self.called = (shop_id, adv_id, tuple(nmids))
        return {n: 6 for n in nmids}


@pytest.mark.asyncio
async def test_currentbid_mixin():
    pm = FakePM()
    mix = CurrentBidMixin("shopY", pm)
    res = await mix.get_current_bids(8, [3])
    assert res == {3: 6}
    assert pm.called == ("shopY", 8, (3,))


