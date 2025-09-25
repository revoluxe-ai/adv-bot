import pytest

from app.core.mp.wb.mixins.bid_update import MinBidMixin, CurrentBidMixin, BidUpdateMixin


class FakePromotionManager:
    def __init__(self) -> None:
        self.calls = []

    async def get_min_bids(self, shop_id: str, adv_id: int, nmids: list[int]):
        self.calls.append(("min", shop_id, adv_id, tuple(nmids)))
        return {n: 1 for n in nmids}

    async def get_current_bids(self, shop_id: str, adv_id: int, nmids: list[int]):
        self.calls.append(("cur", shop_id, adv_id, tuple(nmids)))
        return {n: 2 for n in nmids}

    async def update_bids(self, shop_id: str, batch: object):
        self.calls.append(("upd", shop_id, batch))


@pytest.mark.asyncio
async def test_minbid_mixin_delegates():
    mgr = FakePromotionManager()
    mix = MinBidMixin("s1", mgr)
    res = await mix.get_min_bids(10, [7, 8])
    assert res == {7: 1, 8: 1}
    assert mgr.calls[0][0] == "min"


@pytest.mark.asyncio
async def test_currentbid_mixin_delegates():
    mgr = FakePromotionManager()
    mix = CurrentBidMixin("s2", mgr)
    res = await mix.get_current_bids(11, [3])
    assert res == {3: 2}
    assert mgr.calls[0][0] == "cur"


@pytest.mark.asyncio
async def test_updatebid_mixin_delegates():
    mgr = FakePromotionManager()
    mix = BidUpdateMixin("s3", mgr)
    await mix.update_bids({"a": 1})
    assert mgr.calls[0][0] == "upd"
    assert mgr.calls[0][1] == "s3"


