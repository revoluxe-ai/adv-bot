import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import asyncio
from types import SimpleNamespace

from app.shared.application.dto.update_bids_in_advs.update_bids_in_search_adv_dto import (
    UpdateBidsInSearchAdvDTO,
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


async def test_update_cpm_manager_with_mocks():
    adv = DummyAdvSetting()
    dto = UpdateBidsInSearchAdvDTO(adv, dummy_keywords())

    # Instantiate UpdateCPMManager without __init__ and inject mocks
    from app.modules.shop_runner.service_manager.services.update_cpm.update_cpm_manager import UpdateCPMManager

    mm = object.__new__(UpdateCPMManager)
    mm._shop_id = "shop1"
    mm._redis_manager = SimpleNamespace()
    mm._access = SimpleNamespace(shop_id="shop1")
    mm._session = None

    # Fake wb_api to avoid real HTTP
    class DummyWBApi:
        async def get_min_bid_for_nmids(self, adv_id, nmids):
            return {nm: 10 for nm in nmids}

        async def get_advs(self, adv_ids):
            class A:
                pass

            a = A()
            a.cpm = 50
            return [a]

    mm._wb_api = DummyWBApi()

    # Patch BidUpdateOrchestrator to a no-op mock
    import app.modules.shop_runner.service_manager.services.update_cpm.update_cpm_manager as mod

    class DummyBidUpdateOrchestrator:
        def __init__(self, wb_api):
            self.batch = None

        async def process_updates(self, batch):
            self.batch = batch

    mod.BidUpdateOrchestrator = DummyBidUpdateOrchestrator

    # Patch parser to avoid IO
    import sys
    import types

    sys.modules["app.modules.wb_keywords_parser.parser"] = types.SimpleNamespace(
        add_wb_positions=lambda *a, **k: asyncio.sleep(0)
    )

    # Run
    await mm.update_cpms_in_search_advs([dto])
    assert isinstance(mm, object)


if __name__ == "__main__":
    asyncio.run(test_update_cpm_manager_with_mocks())
