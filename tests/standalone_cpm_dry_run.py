import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass


@dataclass
class UpdateBidForNmidTask:
    adv_id: int
    nmid: int
    new_bid_coro: Awaitable[int]


@dataclass
class UpdateBidsSearchAdvInShopBatch:
    shop_id: str
    tasks: list[UpdateBidForNmidTask]

    def add_task(self, task: UpdateBidForNmidTask) -> None:
        self.tasks.append(task)


async def fake_bid(adv_id: int, nmid: int) -> int:
    await asyncio.sleep(0)
    return 100 + adv_id + nmid


async def run():
    shop_id = "shop1"
    batch = UpdateBidsSearchAdvInShopBatch(shop_id=shop_id, tasks=[])
    adv_id = 1
    nmids = [2001, 2002, 2003]
    for nmid in nmids:
        batch.add_task(UpdateBidForNmidTask(adv_id=adv_id, nmid=nmid, new_bid_coro=fake_bid(adv_id, nmid)))
    print(f"Batch prepared: {len(batch.tasks)} tasks for shop {shop_id}")
    print("Computing new bids...")
    for t in batch.tasks:
        bid = await t.new_bid_coro
        print(f"adv_id={t.adv_id}, nmid={t.nmid}, new_bid={bid}")


if __name__ == "__main__":
    asyncio.run(run())
