import pytest
import time

from app.core.mp.wb.services.promotion_bids_service import PromotionBidsService


class FakePM:
    def __init__(self):
        self.calls = []

    async def get_min_bids(self, shop_id: str, adv_id: int, nmids: list[int]):
        self.calls.append(("min", shop_id, adv_id, tuple(nmids)))
        return {n: 100 for n in nmids}

    async def get_current_bids(self, shop_id: str, adv_id: int, nmids: list[int]):
        self.calls.append(("cur", shop_id, adv_id, tuple(nmids)))
        return {n: 200 for n in nmids}

    async def update_bids(self, shop_id: str, batch: object):
        self.calls.append(("upd", shop_id, batch))


@pytest.mark.asyncio
async def test_min_bids_cache_behavior():
    pm = FakePM()
    svc = PromotionBidsService(pm, ttl_seconds=1)

    res1 = await svc.resolve_min_bids("s1", 1, [1, 2])
    assert res1 == {1: 100, 2: 100}
    assert len(pm.calls) == 1

    # second call within TTL should not call PM
    res2 = await svc.resolve_min_bids("s1", 1, [1, 2])
    assert res2 == res1
    assert len(pm.calls) == 1

    # after TTL, should call again
    time.sleep(1.1)
    res3 = await svc.resolve_min_bids("s1", 1, [1, 2])
    assert len(pm.calls) == 2


@pytest.mark.asyncio
async def test_current_and_update_delegate():
    pm = FakePM()
    svc = PromotionBidsService(pm)

    cur = await svc.resolve_current_bids("s2", 2, [3])
    assert cur == {3: 200}

    await svc.update_bids("s2", {"x": 1})
    assert pm.calls[-1][0] == "upd"


