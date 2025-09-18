from app.shared.application.dto.update_bids_in_advs.update_bids_in_search_adv_dto import (
    UpdateBidsInSearchAdvDTO,
)
from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidForNmidTask,
    UpdateBidsSearchAdvInShopBatch,
)


class DummyAdvSetting:
    def __init__(self):
        self.adv_id = 1
        self.search_adv_id = 101
        self.nmids = [2001, 2002]
        self.max_cpm = 120
        self.max_place = 5


async def dummy_keywords():
    return []


def main():
    adv = DummyAdvSetting()
    dto = UpdateBidsInSearchAdvDTO(adv, dummy_keywords())
    batch = UpdateBidsSearchAdvInShopBatch("shop1")

    async def dummy_bid():
        return 42

    for nmid in adv.nmids:
        task = UpdateBidForNmidTask(adv.adv_id, nmid, dummy_bid())
        batch.add_task(task)

    print("Batch shop_id:", batch.shop_id)
    print("Batch tasks:", len(batch.tasks))


if __name__ == "__main__":
    main()
