import asyncio
from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.update_cpm.bid_orchestrator import BidUpdateOrchestrator
from app.modules.shop_runner.service_manager.services.update_cpm.update_cpm_manager import UpdateCPMManager
from app.shared.application.dto.update_bids_in_advs.update_bids_in_search_adv_dto import (
    UpdateBidsInSearchAdvDTO,
)
from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidTask,
)


class DummyPromotionAdapter:
    def __init__(self, *, min_map=None, curr_map=None, fail_min=False, fail_curr=False):
        self._min_map = min_map or {}
        self._curr_map = curr_map or {}
        self._fail_min = fail_min
        self._fail_curr = fail_curr
        self.updated_payloads = []

    async def get_min_bids(self, shop_id, *, adv_id, nmids):
        if self._fail_min:
            raise RuntimeError("min_bids failed")
        return {int(k): int(v) for k, v in self._min_map.items() if int(k) in set(nmids)}

    async def get_current_bids(self, shop_id, *, adv_id, nmids):
        if self._fail_curr:
            raise RuntimeError("current_bids failed")
        return {int(k): int(v) for k, v in self._curr_map.items() if int(k) in set(nmids)}

    async def update_bids(self, shop_id, *, payload):
        self.updated_payloads.append(payload)


async def kw_coro_factory(text="kw"):
    return [SimpleNamespace(text=text)]


@pytest.mark.asyncio
async def test_min_bids_unavailable_raises(monkeypatch):
    adapter = DummyPromotionAdapter(fail_min=True)
    mgr = UpdateCPMManager("shop1", promotion_adapter=adapter)

    # Patch best keyword selector to return first
    import app.modules.wb_adv_updater.data_manager as dm
    monkeypatch.setattr(dm, "get_best_keyword", lambda keywords: keywords[0] if keywords else None)

    # Patch parser and redis
    import app.modules.wb_keywords_parser as parser_mod

    async def _add_wb_positions(text, nmids, delay=0.1):
        return None

    monkeypatch.setattr(parser_mod.parser, "add_wb_positions", _add_wb_positions)

    import app.utils.redis_manager as rdm

    async def _get_keyword_position(text, nmid):
        return SimpleNamespace(position=3)

    monkeypatch.setattr(rdm, "get_keyword_position", _get_keyword_position)

    dto = UpdateBidsInSearchAdvDTO(SimpleNamespace(search_adv_id=1, nmids=[1], max_cpm=100, bidder_step=2, max_place=5),
                                   kw_coro_factory())

    with pytest.raises(ExceptionGroup):
        await mgr.update_cpms_in_search_advs([dto])


@pytest.mark.asyncio
async def test_current_bids_unavailable_raises(monkeypatch):
    adapter = DummyPromotionAdapter(fail_curr=True, min_map={1: 10})
    mgr = UpdateCPMManager("shop1", promotion_adapter=adapter)

    import app.modules.wb_adv_updater.data_manager as dm
    monkeypatch.setattr(dm, "get_best_keyword", lambda keywords: keywords[0] if keywords else None)

    import app.modules.wb_keywords_parser as parser_mod

    async def _add_wb_positions(text, nmids, delay=0.1):
        return None

    monkeypatch.setattr(parser_mod.parser, "add_wb_positions", _add_wb_positions)

    import app.utils.redis_manager as rdm

    async def _get_keyword_position(text, nmid):
        return SimpleNamespace(position=10)

    monkeypatch.setattr(rdm, "get_keyword_position", _get_keyword_position)

    dto = UpdateBidsInSearchAdvDTO(SimpleNamespace(search_adv_id=1, nmids=[1], max_cpm=100, bidder_step=2, max_place=5),
                                   kw_coro_factory())

    with pytest.raises(ExceptionGroup):
        await mgr.update_cpms_in_search_advs([dto])


@pytest.mark.asyncio
async def test_position_zero_skip(monkeypatch):
    adapter = DummyPromotionAdapter(min_map={1: 10}, curr_map={1: 20})
    mgr = UpdateCPMManager("shop1", promotion_adapter=adapter)

    import app.modules.wb_adv_updater.data_manager as dm
    monkeypatch.setattr(dm, "get_best_keyword", lambda keywords: keywords[0] if keywords else None)

    import app.modules.wb_keywords_parser as parser_mod

    async def _add_wb_positions(text, nmids, delay=0.1):
        return None

    monkeypatch.setattr(parser_mod.parser, "add_wb_positions", _add_wb_positions)

    import app.utils.redis_manager as rdm

    async def _get_keyword_position(text, nmid):
        return SimpleNamespace(position=0)

    monkeypatch.setattr(rdm, "get_keyword_position", _get_keyword_position)

    dto = UpdateBidsInSearchAdvDTO(SimpleNamespace(search_adv_id=1, nmids=[1], max_cpm=100, bidder_step=2, max_place=5),
                                   kw_coro_factory())

    # Should not raise, just skip
    await mgr.update_cpms_in_search_advs([dto])
    # No updates should be sent
    assert adapter.updated_payloads == []


@pytest.mark.asyncio
async def test_new_bid_equals_current_skip(monkeypatch):
    # Set min and max to clamp new bid to current
    adapter = DummyPromotionAdapter(min_map={1: 50}, curr_map={1: 50})
    mgr = UpdateCPMManager("shop1", promotion_adapter=adapter)

    import app.modules.wb_adv_updater.data_manager as dm
    monkeypatch.setattr(dm, "get_best_keyword", lambda keywords: keywords[0] if keywords else None)

    import app.modules.wb_keywords_parser as parser_mod

    async def _add_wb_positions(text, nmids, delay=0.1):
        return None

    monkeypatch.setattr(parser_mod.parser, "add_wb_positions", _add_wb_positions)

    import app.utils.redis_manager as rdm

    async def _get_keyword_position(text, nmid):
        return SimpleNamespace(position=1)

    monkeypatch.setattr(rdm, "get_keyword_position", _get_keyword_position)

    dto = UpdateBidsInSearchAdvDTO(SimpleNamespace(search_adv_id=1, nmids=[1], max_cpm=50, bidder_step=2, max_place=5),
                                   kw_coro_factory())

    await mgr.update_cpms_in_search_advs([dto])
    assert adapter.updated_payloads == []


@pytest.mark.asyncio
async def test_orchestrator_batches_chunks_120(monkeypatch):
    class DummyUpdater:
        def __init__(self):
            self.calls = []

        async def update_bids(self, shop_id, *, adv_id, nm_bids):
            self.calls.append((shop_id, adv_id, list(nm_bids)))

    updater = DummyUpdater()
    orch = BidUpdateOrchestrator("shop1", updater, max_batch_size=50)

    # Build batch with 120 tasks resolved to incremental bids
    batch = UpdateBidsSearchAdvInShopBatch("shop1")
    tasks = []
    for i in range(120):
        async def coro_factory(val=i):
            return val + 1

        fut = asyncio.ensure_future(coro_factory())
        tasks.append(UpdateBidForNmidTask(adv_id=1, nmid=1000 + i, new_bid_coro=fut))
        batch.add_task(tasks[-1])

    await orch.process_updates(batch)
    # Expect 3 calls: 50, 50, 20
    sizes = [len(call[2]) for call in updater.calls]
    assert sizes == [50, 50, 20]


@pytest.mark.asyncio
async def test_validation_error_min_gt_max(monkeypatch):
    # min > max should raise
    adapter = DummyPromotionAdapter(min_map={1: 100}, curr_map={1: 50})
    mgr = UpdateCPMManager("shop1", promotion_adapter=adapter)

    import app.modules.wb_adv_updater.data_manager as dm
    monkeypatch.setattr(dm, "get_best_keyword", lambda keywords: keywords[0] if keywords else None)

    import app.modules.wb_keywords_parser as parser_mod

    async def _add_wb_positions(text, nmids, delay=0.1):
        return None

    monkeypatch.setattr(parser_mod.parser, "add_wb_positions", _add_wb_positions)

    import app.utils.redis_manager as rdm

    async def _get_keyword_position(text, nmid):
        return SimpleNamespace(position=10)

    monkeypatch.setattr(rdm, "get_keyword_position", _get_keyword_position)

    dto = UpdateBidsInSearchAdvDTO(SimpleNamespace(search_adv_id=1, nmids=[1], max_cpm=60, bidder_step=2, max_place=5),
                                   kw_coro_factory())

    with pytest.raises(ExceptionGroup):
        await mgr.update_cpms_in_search_advs([dto])
