from __future__ import annotations

import logging
from datetime import datetime
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager.services.stats_freshness_cache_manager import (
    RedisStatsFreshnessStateCacheManager,
)
from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessState,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager


def _build_manager(fake_redis) -> CoroutinesManager:
    wb_api = MagicMock()
    wb_api.wb_cabinet = SimpleNamespace(shop_id="test_shop")
    wb_api.access = MagicMock()
    wb_api.session = MagicMock()
    wb_api.shop_id = "test_shop"
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    wb_manager_hub = MagicMock()
    wb_manager_hub.wb_data_manager = MagicMock()
    wb_manager_hub.wb_manager = MagicMock()
    return CoroutinesManager(
        wb_api=wb_api,
        redis_client_wrapper=redis_client_wrapper,
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=MagicMock(),
        wb_manager_hub=wb_manager_hub,
    )


@dataclass
class _Keyword:
    hard_status: int
    rating: float
    keyword_setting_original_id: int
    text: str


@pytest.mark.asyncio
async def test_split_advs_by_stats_freshness_filters_correctly(fake_redis) -> None:
    manager = _build_manager(fake_redis)
    adv_fresh = SimpleNamespace(adv_id=1)
    adv_stale = SimpleNamespace(adv_id=2)
    adv_emergency = SimpleNamespace(adv_id=3)

    cache = RedisStatsFreshnessStateCacheManager(RedisClient(redis_client=fake_redis))
    await cache.mset_states(
        manager.shop_id,
        [
            (1, StatsFreshnessState(is_fresh=True, is_stale_over_6h=False)),
            (2, StatsFreshnessState(is_fresh=False, is_stale_over_6h=False)),
            (3, StatsFreshnessState(is_fresh=False, is_stale_over_6h=True)),
        ],
    )
    fresh, stale_over_6h = await manager._split_advs_by_stats_freshness(
        [adv_fresh, adv_stale, adv_emergency], operation_name="test_op"
    )

    assert fresh == [adv_fresh]
    assert stale_over_6h == [adv_emergency]


@pytest.mark.asyncio
async def test_split_advs_by_stats_freshness_bypass_when_guard_disabled(
    fake_redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STATS_FRESHNESS_GUARD_ENABLED", "false")
    manager = _build_manager(fake_redis)
    adv_fresh = SimpleNamespace(adv_id=1)
    adv_stale = SimpleNamespace(adv_id=2)
    adv_emergency = SimpleNamespace(adv_id=3)
    advs = [adv_fresh, adv_stale, adv_emergency]

    cache = RedisStatsFreshnessStateCacheManager(RedisClient(redis_client=fake_redis))
    await cache.mset_states(
        manager.shop_id,
        [
            (1, StatsFreshnessState(is_fresh=True, is_stale_over_6h=False)),
            (2, StatsFreshnessState(is_fresh=False, is_stale_over_6h=False)),
            (3, StatsFreshnessState(is_fresh=False, is_stale_over_6h=True)),
        ],
    )

    with patch.object(
        manager._redis_stats_freshness_cache,
        "mget_entries",
        new=AsyncMock(),
    ) as mget_mock:
        fresh, stale_over_6h = await manager._split_advs_by_stats_freshness(
            advs, operation_name="test_op"
        )

    assert fresh == advs
    assert stale_over_6h == []
    mget_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_split_advs_by_stats_freshness_fail_open_on_cache_miss(
    fake_redis, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.ERROR)
    manager = _build_manager(fake_redis)
    adv = SimpleNamespace(adv_id=99)
    fresh, stale_over_6h = await manager._split_advs_by_stats_freshness(
        [adv], operation_name="test_op"
    )
    assert fresh == [adv]
    assert stale_over_6h == []
    assert any(
        "stats_freshness_cache fail-open" in r.message and r.levelno == logging.ERROR
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_split_advs_by_stats_freshness_fail_open_on_invalid_payload(
    fake_redis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)
    manager = _build_manager(fake_redis)
    adv = SimpleNamespace(adv_id=42)
    key = RedisStatsFreshnessStateCacheManager.key(manager.shop_id, 42)
    await fake_redis.set(key, "not-json")
    fresh, stale_over_6h = await manager._split_advs_by_stats_freshness(
        [adv], operation_name="test_op"
    )
    assert fresh == [adv]
    assert stale_over_6h == []
    assert any(
        "stats_freshness_cache fail-open" in r.message and r.levelno == logging.ERROR
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_refresh_stats_freshness_cache_writes_redis(fake_redis) -> None:
    manager = _build_manager(fake_redis)
    adv_ok = SimpleNamespace(adv_id=10)
    adv_bad = SimpleNamespace(adv_id=20)

    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[adv_ok, adv_bad]
    )

    async def _evaluate(adv: SimpleNamespace) -> StatsFreshnessState:
        if adv.adv_id == 20:
            raise RuntimeError("ch boom")
        return StatsFreshnessState(is_fresh=True, is_stale_over_6h=False)

    with patch(
        "app.modules.shop_runner.service_manager.manager.StatsFreshnessManager"
    ) as mgr_cls:
        mgr_cls.return_value.evaluate = AsyncMock(side_effect=_evaluate)
        await manager.refresh_stats_freshness_cache.__wrapped__(manager)

    cache = RedisStatsFreshnessStateCacheManager(RedisClient(redis_client=fake_redis))
    loaded = await cache.mget_entries(manager.shop_id, [10, 20])
    assert len(loaded) == 2
    assert loaded[0][0] == 10
    assert loaded[0][1] == StatsFreshnessState(
        is_fresh=True, is_stale_over_6h=False
    )
    assert loaded[0][2] == "hit"
    assert loaded[0][3] is not None
    datetime.fromisoformat(loaded[0][3])
    assert loaded[1][0] == 20
    assert loaded[1][1] is None
    assert loaded[1][2] == "miss"
    assert loaded[1][3] is None


@pytest.mark.asyncio
async def test_apply_stats_stale_emergency_keeps_top_keyword(fake_redis) -> None:
    manager = _build_manager(fake_redis)
    manager._set_min_search_bid_for_keyword = AsyncMock()  # type: ignore[method-assign]

    keywords = [
        _Keyword(hard_status=1, rating=10.0, keyword_setting_original_id=11, text="k1"),
        _Keyword(hard_status=2, rating=55.0, keyword_setting_original_id=22, text="best"),
        _Keyword(hard_status=1, rating=20.0, keyword_setting_original_id=33, text="k3"),
    ]
    complex_adv = SimpleNamespace(
        adv_id=777,
        auto_add_only_relevant_phrase=False,
        bot_active=False,
        get_keywords=AsyncMock(return_value=keywords),
    )

    class _FakeSession:
        def __init__(self) -> None:
            self.statements = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, stmt):
            self.statements.append(stmt)
            return None

        async def commit(self):
            return None

    fake_session = _FakeSession()

    with patch(
        "app.modules.shop_runner.service_manager.manager.sm",
        new=lambda read_only=False: fake_session,
    ):
        await manager._apply_stats_stale_emergency(complex_adv)  # type: ignore[arg-type]

    assert len(fake_session.statements) == 2
    first_values = list(fake_session.statements[0]._values.values())  # pyright: ignore[reportAttributeAccessIssue]
    second_values = list(fake_session.statements[1]._values.values())  # pyright: ignore[reportAttributeAccessIssue]
    assert first_values[0].value == 1
    assert second_values[0].value == 2
    manager._set_min_search_bid_for_keyword.assert_awaited_once_with(complex_adv, "best")


@pytest.mark.asyncio
async def test_set_min_search_bid_for_keyword_uses_min_bids(fake_redis) -> None:
    manager = _build_manager(fake_redis)
    complex_adv = SimpleNamespace(auction_adv_id=555, nmids=[101, 202])

    min_bids = SimpleNamespace(search={101: 150, 202: 200})
    wb_manager_hub = SimpleNamespace(
        wb_manager=SimpleNamespace(
            get_min_bids_cache_only=AsyncMock(return_value=min_bids),
        ),
        wb_modifier=SimpleNamespace(set_cluster_bids_for_adv=AsyncMock()),
    )

    manager._wb_manager_hub = wb_manager_hub
    with patch(
        "app.modules.shop_runner.service_manager.manager.WBManagerHubFactory.get_wb_manager_from_context",
        side_effect=RuntimeError("should not be called"),
    ):
        await manager._set_min_search_bid_for_keyword(complex_adv, "top_phrase")  # type: ignore[arg-type]

    wb_manager_hub.wb_modifier.set_cluster_bids_for_adv.assert_awaited_once()
    call_args = wb_manager_hub.wb_modifier.set_cluster_bids_for_adv.await_args.args
    command = call_args[0]
    assert len(command.new_bids) == 2
    assert {bid.nmid for bid in command.new_bids} == {101, 202}
    assert {bid.new_bid for bid in command.new_bids} == {150, 200}
    assert {bid.cluster for bid in command.new_bids} == {"top_phrase"}


@pytest.mark.asyncio
async def test_set_min_search_bid_skips_when_wb_min_bids_fallback_fails(
    fake_redis,
) -> None:
    """Live WB fallback must not leave silent use of emergency default after API error."""
    manager = _build_manager(fake_redis)
    complex_adv = SimpleNamespace(adv_id=9001, auction_adv_id=555, nmids=[101, 202])

    min_bids = SimpleNamespace(search={101: 150})
    get_min_bids_live = AsyncMock(side_effect=RuntimeError("WB API unavailable"))
    wb_manager_hub = SimpleNamespace(
        wb_manager=SimpleNamespace(
            get_min_bids_cache_only=AsyncMock(return_value=min_bids),
            get_min_bids=get_min_bids_live,
        ),
        wb_modifier=SimpleNamespace(set_cluster_bids_for_adv=AsyncMock()),
    )

    manager._wb_manager_hub = wb_manager_hub
    await manager._set_min_search_bid_for_keyword(complex_adv, "top_phrase")  # type: ignore[arg-type]

    get_min_bids_live.assert_awaited_once()
    wb_manager_hub.wb_modifier.set_cluster_bids_for_adv.assert_not_awaited()
