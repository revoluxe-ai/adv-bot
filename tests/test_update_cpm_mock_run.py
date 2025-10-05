import sys
import os
import asyncio

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
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


async def fake_keywords():
    return []


async def run_test():
    adv = DummyAdvSetting()
    dto = UpdateBidsInSearchAdvDTO(adv, fake_keywords())

    # Create CPM manager instance without running __init__
    from app.modules.shop_runner.service_manager.services.update_cpm.update_cpm_manager import (
        UpdateCPMManager,
    )

    mm = object.__new__(UpdateCPMManager)
    mm._shop_id = "shop1"
    mm._redis_manager = SimpleNamespace()

    # Setup dummy wb_api
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
    mm._access = SimpleNamespace(shop_id="shop1")
    mm._session = None

    # Mock parser to avoid real IO
    import sys
    import types

    parser_mod = types.SimpleNamespace(
        add_wb_positions=lambda text, pos, delay=0: asyncio.sleep(0)
    )
    sys.modules["app.modules.wb_keywords_parser.parser"] = parser_mod

    # Run the CPM update flow with a single DTO
    try:
        await mm.update_cpms_in_search_advs([dto])
        print("OK: update_cpms_in_search_advs ran without raising")
    except Exception as e:
        print("ERR:", type(e).__name__, e)


if __name__ == "__main__":
    asyncio.run(run_test())
