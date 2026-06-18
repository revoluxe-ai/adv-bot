import json

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.cluster_bids_redis import (
    ClusterBidKey,
    RedisApiClusterBidsManager,
    RedisClusterBidsManager,
)
from app.modules.cluster_bids_redis.redis_cluster_bids_manager import ClusterBidEntry


@pytest.fixture
def redis_client_wrapper(fake_redis: FakeRedis) -> RedisClient:
    return RedisClient(redis_client=fake_redis)


@pytest.fixture
def redis_api_cluster_bids_manager(
    redis_client_wrapper: RedisClient,
) -> RedisApiClusterBidsManager:
    return RedisApiClusterBidsManager(redis_client=redis_client_wrapper)


@pytest.mark.asyncio
async def test_replace_from_api_persists_and_get_bids(
    redis_api_cluster_bids_manager: RedisApiClusterBidsManager,
    fake_redis: FakeRedis,
) -> None:
    bids = [
        NormqueryBidDTO(advert_id=1, nm_id=100, norm_query="q1", bid=42),
        NormqueryBidDTO(advert_id=2, nm_id=200, norm_query="q2", bid=99),
    ]
    written = await redis_api_cluster_bids_manager.replace_from_api(bids)
    assert written == len(bids)

    for dto in bids:
        key = redis_api_cluster_bids_manager._get_key(
            dto.advert_id, dto.nm_id, dto.norm_query
        )
        raw = await fake_redis.get(key)
        assert raw is not None
        s = raw.decode() if isinstance(raw, bytes) else raw
        assert json.loads(s) == {"bid": dto.bid}

    keys = [
        ClusterBidKey(search_adv_id=1, nmid=100, cluster="q1"),
        ClusterBidKey(search_adv_id=2, nmid=200, cluster="q2"),
    ]
    got = await redis_api_cluster_bids_manager.get_bids(keys)
    assert got[keys[0]] == 42
    assert got[keys[1]] == 99


@pytest.mark.asyncio
async def test_api_keys_do_not_overlap_cluster_bid_state(
    redis_api_cluster_bids_manager: RedisApiClusterBidsManager,
    redis_client_wrapper: RedisClient,
    fake_redis: FakeRedis,
) -> None:
    """API cache uses a different prefix than RedisClusterBidsManager."""
    state_mgr = RedisClusterBidsManager(redis_client=redis_client_wrapper)
    await state_mgr.remember_bids(
        [
            ClusterBidEntry(
                search_adv_id=1,
                nmid=50,
                cluster="c",
                new_bid=7,
                step=2,
                direct="UP",
            )
        ]
    )
    await redis_api_cluster_bids_manager.replace_from_api(
        [NormqueryBidDTO(advert_id=1, nm_id=50, norm_query="c", bid=500)]
    )

    state_key = state_mgr._get_key(1, 50, "c")
    api_key = redis_api_cluster_bids_manager._get_key(1, 50, "c")
    assert state_key != api_key

    state_raw = await fake_redis.get(state_key)
    api_raw = await fake_redis.get(api_key)
    assert state_raw is not None and api_raw is not None
    state_payload = json.loads(
        state_raw.decode() if isinstance(state_raw, bytes) else state_raw
    )
    api_payload = json.loads(api_raw.decode() if isinstance(api_raw, bytes) else api_raw)
    assert state_payload["step"] == 2
    assert state_payload["new_bid"] == 7
    assert api_payload == {"bid": 500}


@pytest.mark.asyncio
async def test_replace_from_api_empty_noop(
    redis_api_cluster_bids_manager: RedisApiClusterBidsManager,
) -> None:
    written = await redis_api_cluster_bids_manager.replace_from_api([])
    assert written == 0


@pytest.mark.asyncio
async def test_get_bids_empty_input(
    redis_api_cluster_bids_manager: RedisApiClusterBidsManager,
) -> None:
    assert await redis_api_cluster_bids_manager.get_bids([]) == {}
