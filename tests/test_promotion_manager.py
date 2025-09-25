import pytest

from app.core.mp.wb.managers.promotion import PromotionManager


class FakeAdapter:
    def __init__(self) -> None:
        self.called_update = False

    async def get_min_bids(self, adv_id: int, nmids: list[int]) -> dict[int, int]:
        return {n: 10 for n in nmids}

    async def get_current_bids(self, adv_id: int, nmids: list[int]) -> dict[int, int]:
        return {n: 20 for n in nmids}

    async def update_bids(self, payload: object) -> None:
        self.called_update = True


class FakeFactory:
    def __init__(self, adapter: FakeAdapter) -> None:
        self.adapter = adapter

    def get_adapter(self, shop_id: str, section: str, version: str):
        return self.adapter


@pytest.mark.asyncio
async def test_promotion_manager_delegation():
    fake = FakeAdapter()
    factory = FakeFactory(fake)
    mgr = PromotionManager(factory)

    res_min = await mgr.get_min_bids("shop1", 123, [1, 2, 3])
    assert res_min == {1: 10, 2: 10, 3: 10}

    res_cur = await mgr.get_current_bids("shop1", 123, [4, 5])
    assert res_cur == {4: 20, 5: 20}

    await mgr.update_bids("shop1", {"batch": []})
    assert fake.called_update is True


