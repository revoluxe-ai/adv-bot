import csv
from datetime import datetime
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.utils import build_cpm_date_map, get_csv_file
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus


class DummyCalculatedKeyword:
    def __init__(
        self,
        *,
        text: str,
        clicks: int,
        views: int,
        total_views: int,
        query: str,
        predict_ctr: float,
        ctr: float,
        reason: str,
        hard_status: int,
        status: KeywordStatus,
        position: float,
        rating_by_orders: float,
        total_orders: int,
        orders_per_1000_rub: float | None = None,
    ) -> None:
        self.text = text
        self.clicks = clicks
        self.views = views
        self.total_views = total_views
        self.query = query
        self.predict_ctr = predict_ctr
        self.ctr = ctr
        self.reason = reason
        self.hard_status = hard_status
        self.status = status
        self.position = position
        self.rating_by_orders = rating_by_orders
        self.orders_per_1000_rub = (
            orders_per_1000_rub if orders_per_1000_rub is not None else rating_by_orders * 10
        )
        self.total_orders = total_orders


@pytest.mark.asyncio
async def test_get_csv_file_generates_sorted_rows(monkeypatch: pytest.MonkeyPatch):
    """Убедиться, что CSV содержит заголовок и строки упорядочены по заказам."""
    adv_setting = MagicMock(spec=AdvSetting)
    adv_setting.parsing_active = True
    low_orders_keyword = DummyCalculatedKeyword(
        text="low_order_keyword",
        clicks=5,
        views=50,
        total_views=80,
        query="5",
        predict_ctr=0.24,
        ctr=0.1,
        reason="max_cpc",
        hard_status=1,
        status=KeywordStatus.GOOD,
        position=0.0,
        rating_by_orders=0.0,
        total_orders=5,
    )
    high_orders_keyword = DummyCalculatedKeyword(
        text="high_order_keyword",
        clicks=10,
        views=100,
        total_views=200,
        query="10",
        predict_ctr=0.6,
        ctr=0.2,
        reason="max_position",
        hard_status=1,
        status=KeywordStatus.GOOD,
        position=1.0,
        rating_by_orders=0.1,
        total_orders=10,
    )
    monkeypatch.setattr(
        "app.client_bot.utils.get_keywords_for_keyboard",
        AsyncMock(return_value=[low_orders_keyword, high_orders_keyword]),
    )

    csv_content = await get_csv_file(adv_setting)
    parsed = list(csv.reader(StringIO(csv_content), delimiter=";", quotechar='"'))

    assert parsed[0][0] == "Запрос(вхождение)"
    data_rows = parsed[1:]
    assert data_rows[0][0] == high_orders_keyword.text
    assert data_rows[1][0] == low_orders_keyword.text
    assert data_rows[0][8] == "ЦП"  # Статус (hard_status) теперь на индексе 8
    assert data_rows[1][8] == "МС"
    assert data_rows[0][-1] == str(high_orders_keyword.total_orders)
    assert data_rows[1][-1] == str(low_orders_keyword.total_orders)


class _Kw:
    """Minimal keyword-like object for build_cpm_date_map tests."""

    def __init__(self, text: str, cpm: float = 0.0, timestamp: datetime | None = None):
        self.text = text
        self.cpm = cpm
        self.timestamp = timestamp or datetime(2025, 2, 17, 12, 0, 0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_cpm_date_map_priority_set_bid() -> None:
    """Priority 1: when set_bid Redis has value, it is used."""
    adv = MagicMock()
    adv.adv_id = 1
    adv.search_adv_id = 10
    adv.nmids = [100]
    keywords = [_Kw("q1", cpm=50.0), _Kw("q2", cpm=60.0)]
    redis_client = MagicMock()

    bid_log_map: dict = {}
    cache_map: dict = {}

    async def fake_get_bids(keys):
        from app.modules.cluster_bids_redis import ClusterBidKey
        out: dict = {}
        for k in keys:
            if k.cluster == "q1":
                out[k] = 111
        return out

    async def fake_ts_get(_adv):
        return datetime(2025, 2, 17, 10, 0, 0)

    with patch(
        "app.modules.cluster_bids_redis.RedisClusterBidsManager",
    ) as m_mgr:
        with patch(
            "app.modules.cluster_bids_redis.RedisClusterBidsTimestampManager",
        ) as m_ts:
            with patch(
                "app.modules.keyword_bid_from_log.get_latest_keyword_bids",
                new_callable=AsyncMock,
                return_value=bid_log_map,
            ):
                with patch(
                    "app.modules.calculated_keywords_redis_cache_manager.redis_manager.RedisCalculatedKeywordsCacheManager",
                ) as m_cache:
                    m_mgr.return_value.get_bids = AsyncMock(side_effect=fake_get_bids)
                    m_ts.return_value.get = AsyncMock(side_effect=fake_ts_get)
                    m_cache.return_value.get_calculated_keywords_map = AsyncMock(
                        return_value=cache_map
                    )
                    result = await build_cpm_date_map(adv, keywords, redis_client)

    assert result["q1"][0] == 111.0
    assert result["q1"][1] == datetime(2025, 2, 17, 10, 0, 0)
    assert result["q2"][0] == 60.0
    assert result["q2"][1] == keywords[1].timestamp


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_cpm_date_map_priority_bid_log() -> None:
    """Priority 2: when set_bid missing, bid_log value is used."""
    adv = MagicMock()
    adv.adv_id = 1
    adv.search_adv_id = 10
    adv.nmids = [100]
    keywords = [_Kw("q1", cpm=50.0)]
    redis_client = MagicMock()
    dt_log = datetime(2025, 2, 17, 11, 0, 0)
    bid_log_map = {"q1": (222.0, dt_log)}

    with patch(
        "app.modules.cluster_bids_redis.RedisClusterBidsManager",
    ) as m_mgr:
        with patch(
            "app.modules.cluster_bids_redis.RedisClusterBidsTimestampManager",
        ) as m_ts:
            with patch(
                "app.modules.keyword_bid_from_log.get_latest_keyword_bids",
                new_callable=AsyncMock,
                return_value=bid_log_map,
            ):
                with patch(
                    "app.modules.calculated_keywords_redis_cache_manager.redis_manager.RedisCalculatedKeywordsCacheManager",
                ) as m_cache:
                    m_mgr.return_value.get_bids = AsyncMock(return_value={})
                    m_ts.return_value.get = AsyncMock(return_value=None)
                    m_cache.return_value.get_calculated_keywords_map = AsyncMock(
                        return_value={}
                    )
                    result = await build_cpm_date_map(adv, keywords, redis_client)

    assert result["q1"] == (222.0, dt_log)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_cpm_date_map_priority_keyword_fallback() -> None:
    """Priority 4: when no Redis/bid_log/cache, keyword.cpm and timestamp are used."""
    adv = MagicMock()
    adv.adv_id = 1
    adv.search_adv_id = None
    adv.nmids = []
    keywords = [_Kw("q1", cpm=99.0, timestamp=datetime(2025, 2, 16, 9, 0, 0))]
    redis_client = MagicMock()

    with patch(
        "app.modules.keyword_bid_from_log.get_latest_keyword_bids",
        new_callable=AsyncMock,
        return_value={},
    ):
        with patch(
            "app.modules.calculated_keywords_redis_cache_manager.redis_manager.RedisCalculatedKeywordsCacheManager",
        ) as m_cache:
            m_cache.return_value.get_calculated_keywords_map = AsyncMock(
                return_value={}
            )
            result = await build_cpm_date_map(adv, keywords, redis_client)

    assert result["q1"][0] == 99.0
    assert result["q1"][1] == datetime(2025, 2, 16, 9, 0, 0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_cpm_date_map_empty_keywords() -> None:
    """Empty keywords list yields empty map."""
    adv = MagicMock()
    adv.adv_id = 1
    adv.search_adv_id = 10
    adv.nmids = [100]
    redis_client = MagicMock()

    result = await build_cpm_date_map(adv, [], redis_client)
    assert result == {}

