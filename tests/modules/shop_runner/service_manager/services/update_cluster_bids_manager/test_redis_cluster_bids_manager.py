import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.cluster_bids_redis import (
    ClusterBidKey,
    RedisClusterBidsManager,
)
from app.modules.cluster_bids_redis.redis_cluster_bids_manager import ClusterBidEntry
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    NewBid,
)
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import (
    BidderKeywordStatus,
)


@pytest.fixture
def redis_client_wrapper(fake_redis: FakeRedis) -> RedisClient:
    return RedisClient(redis_client=fake_redis)


@pytest.fixture
def redis_cluster_bids_manager(
    redis_client_wrapper: RedisClient,
) -> RedisClusterBidsManager:
    return RedisClusterBidsManager(redis_client=redis_client_wrapper)


@pytest.fixture
def redis_cluster_bids_manager_short_ttl(
    redis_client_wrapper: RedisClient,
) -> RedisClusterBidsManager:
    return RedisClusterBidsManager(redis_client=redis_client_wrapper, ttl=5)


def _make_bid(
    adv_id: int,
    nmid: int,
    cluster: str,
    new_bid: int = 10,
) -> NewBid:
    return NewBid(
        new_bid=new_bid,
        adv_id=adv_id,
        nmid=nmid,
        cluster=cluster,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )


def _to_entries(bids: list[NewBid]) -> list[ClusterBidEntry]:
    return [
        ClusterBidEntry(adv_id=b.adv_id, nmid=b.nmid, cluster=b.cluster, new_bid=b.new_bid)
        for b in bids
    ]


@pytest.mark.asyncio
async def test_remember_bids_persists_values(
    redis_cluster_bids_manager: RedisClusterBidsManager,
    fake_redis: FakeRedis,
) -> None:
    bids = [
        _make_bid(adv_id=1, nmid=123, cluster="cluster-a", new_bid=5),
        _make_bid(adv_id=2, nmid=456, cluster="cluster-b", new_bid=9),
    ]
    entries = _to_entries(bids)

    await redis_cluster_bids_manager.remember_bids(entries)

    for bid in bids:
        key = redis_cluster_bids_manager._get_key(bid.adv_id, bid.nmid, bid.cluster)
        stored_value = await fake_redis.get(key)
        assert stored_value is not None
        assert int(stored_value) == bid.new_bid


@pytest.mark.asyncio
async def test_remember_bids_sets_ttl(
    redis_cluster_bids_manager_short_ttl: RedisClusterBidsManager,
    fake_redis: FakeRedis,
) -> None:
    bid = _make_bid(adv_id=5, nmid=777, cluster="ttl-cluster", new_bid=11)
    entries = _to_entries([bid])

    await redis_cluster_bids_manager_short_ttl.remember_bids(entries)

    key = redis_cluster_bids_manager_short_ttl._get_key(
        bid.adv_id,
        bid.nmid,
        bid.cluster,
    )
    ttl_value = await fake_redis.ttl(key)
    expected_ttl = redis_cluster_bids_manager_short_ttl._resolve_ttl()

    assert 0 < ttl_value <= expected_ttl  # TTL должен быть установлен
    assert int(await fake_redis.get(key)) == bid.new_bid


@pytest.mark.asyncio
async def test_remember_bids_empty_list(
    redis_cluster_bids_manager: RedisClusterBidsManager,
    fake_redis: FakeRedis,
) -> None:
    await redis_cluster_bids_manager.remember_bids([])

    assert await fake_redis.dbsize() == 0


@pytest.mark.asyncio
async def test_get_bids_returns_values(
    redis_cluster_bids_manager: RedisClusterBidsManager,
    fake_redis: FakeRedis,
) -> None:
    keys = [
        ClusterBidKey(adv_id=10, nmid=1001, cluster="alpha"),
        ClusterBidKey(adv_id=11, nmid=1002, cluster="beta"),
    ]
    stored_values = {keys[0]: 14, keys[1]: 27}

    for key, value in stored_values.items():
        redis_key = redis_cluster_bids_manager._get_key(key.adv_id, key.nmid, key.cluster)
        await fake_redis.set(redis_key, value)

    bids = await redis_cluster_bids_manager.get_bids(keys)

    assert bids == stored_values


@pytest.mark.asyncio
async def test_get_bids_skips_missing_and_invalid(
    redis_cluster_bids_manager: RedisClusterBidsManager,
    fake_redis: FakeRedis,
) -> None:
    valid_key = ClusterBidKey(adv_id=20, nmid=2001, cluster="valid")
    invalid_key = ClusterBidKey(adv_id=21, nmid=2002, cluster="invalid")
    missing_key = ClusterBidKey(adv_id=22, nmid=2003, cluster="missing")

    await fake_redis.set(
        redis_cluster_bids_manager._get_key(valid_key.adv_id, valid_key.nmid, valid_key.cluster),
        30,
    )
    await fake_redis.set(
        redis_cluster_bids_manager._get_key(invalid_key.adv_id, invalid_key.nmid, invalid_key.cluster),
        "not-int",
    )

    bids = await redis_cluster_bids_manager.get_bids([valid_key, invalid_key, missing_key])

    assert bids == {valid_key: 30}


@pytest.mark.asyncio
async def test_get_bids_empty_input(
    redis_cluster_bids_manager: RedisClusterBidsManager,
) -> None:
    bids = await redis_cluster_bids_manager.get_bids([])

    assert bids == {}



