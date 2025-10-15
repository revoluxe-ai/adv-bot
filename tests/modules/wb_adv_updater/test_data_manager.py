# Path: tests/modules/wb_adv_updater/test_data_manager.py

import io
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import WBItemPosition, AdvSetting, KeywordSetting
from app.modules.wb_adv_updater.data_manager import (
    __sort_by_update_keyword,
    get_best_keyword,
    _build_clickhouse_query,
    __calculate_clusters,
    get_keyword_statistic_clickhouse,
    get_keywords_statistic_clickhouse,
    _get_keyword_settings,
)


@pytest.fixture
def mock_keywords_query():
    with patch('app.modules.keywords_query.keywords_query.get_queries_of_keyword') as mock_get_queries:
        mock_get_queries.side_effect = lambda text: int(text.replace("k", "")) * 10 if text.startswith("k") else 0
        yield


def test_sort_by_update_keyword_with_timestamp():
    now = datetime.now()
    position = WBItemPosition(timestamp=now)
    assert __sort_by_update_keyword(position) == now


def test_sort_by_update_keyword_without_timestamp():
    position = WBItemPosition(timestamp=None)
    # Проверяем, что дата возвращается в пределах последних 1000 дней
    assert datetime.now() - timedelta(days=1000) <= __sort_by_update_keyword(position) <= datetime.now()


def test_get_best_keyword_empty_list():
    keywords = []
    assert get_best_keyword(keywords) is None


def test_get_best_keyword_single_keyword():
    keyword = CalculatedKeyword(text="test", views=100, clicks=10, spend=10, rating_by_predict_ctr=5)
    keywords = [keyword]
    assert get_best_keyword(keywords) == keyword


def test_get_best_keyword_multiple_keywords():
    kw1 = CalculatedKeyword(text="test1", views=100, clicks=10, spend=10, rating_by_predict_ctr=10, position=1)
    kw2 = CalculatedKeyword(text="test2", views=200, clicks=20, spend=20, rating_by_predict_ctr=15, position=0)
    kw3 = CalculatedKeyword(text="test3", views=50, clicks=5, spend=5, rating_by_predict_ctr=5, position=2)
    keywords = [kw1, kw2, kw3]
    best_keyword = get_best_keyword(keywords)
    assert best_keyword == kw1


def test_get_best_keyword_multiple_keywords_with_zero_positions():
    kw1 = CalculatedKeyword(text="test1", views=100, clicks=10, spend=10, rating_by_predict_ctr=10, position=0)
    kw2 = CalculatedKeyword(text="test2", views=200, clicks=20, spend=20, rating_by_predict_ctr=15, position=0)
    kw3 = CalculatedKeyword(text="test3", views=50, clicks=5, spend=5, rating_by_predict_ctr=5, position=0)
    keywords = [kw1, kw2, kw3]
    assert get_best_keyword(keywords) is None


def test_build_clickhouse_query_base():
    adv_ids = {1, 2, 3}
    query = _build_clickhouse_query(adv_ids, None, None)
    expected_query_part = "adv_id IN (1, 2, 3)"
    assert expected_query_part in query
    assert "AND date >= " not in query
    assert "WITH" not in query


def test_build_clickhouse_query_with_pass_time():
    adv_ids = {1}
    pass_time = timedelta(days=7)
    query = _build_clickhouse_query(adv_ids, pass_time, None)
    expected_date = (datetime.now().date() - pass_time).strftime('%Y-%m-%d')
    assert f"AND date >= '{expected_date}'" in query
    assert "WITH" not in query


def test_build_clickhouse_query_with_last_views():
    adv_ids = {1, 2}
    last_views = 1000
    query = _build_clickhouse_query(adv_ids, None, last_views)
    assert "WITH" in query
    assert "cumulative_views" in query
    assert "cumulative_total_views <= 1000" in query
    assert "AND date >= " not in query


def test_build_clickhouse_query_with_pass_time_and_last_views():
    adv_ids = {1}
    pass_time = timedelta(days=7)
    last_views = 500
    query = _build_clickhouse_query(adv_ids, pass_time, last_views)
    expected_date = (datetime.now().date() - pass_time).strftime('%Y-%m-%d')
    assert f"AND date >= '{expected_date}'" in query
    assert "WITH" in query
    assert "cumulative_total_views <= 500" in query


@pytest.mark.usefixtures("mock_keywords_query")
def test_calculate_clusters_basic():
    kw1 = CalculatedKeyword(text="k1", clicks=10, views=100, spend=10.0)
    kw2 = CalculatedKeyword(text="k2", clicks=20, views=200, spend=20.0)
    preset_to_keywords = {1: [kw1, kw2]}
    preset_to_cluster_name = {1: "cluster1"}

    clusters = __calculate_clusters(preset_to_keywords, preset_to_cluster_name)

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.text == "cluster1"
    assert cluster.clicks == 30
    assert cluster.views == 300
    assert cluster.spend == 30.0
    assert cluster.query == "30"
    assert cluster.childs_keywords == [kw1, kw2]


@pytest.mark.usefixtures("mock_keywords_query")
def test_calculate_clusters_multiple_presets():
    kw1 = CalculatedKeyword(text="k1", clicks=5, views=50, spend=5.0)
    kw2 = CalculatedKeyword(text="k2", clicks=15, views=150, spend=15.0)
    kw3 = CalculatedKeyword(text="k3", clicks=2, views=20, spend=2.0)

    preset_to_keywords = {1: [kw1, kw2], 2: [kw3]}
    preset_to_cluster_name = {1: "clusterA", 2: "clusterB"}

    clusters = __calculate_clusters(preset_to_keywords, preset_to_cluster_name)

    assert len(clusters) == 2

    clusterA = next(c for c in clusters if c.text == "clusterA")
    assert clusterA.clicks == 20
    assert clusterA.views == 200
    assert clusterA.spend == 20.0
    assert clusterA.query == "30"
    assert clusterA.childs_keywords == [kw1, kw2]

    clusterB = next(c for c in clusters if c.text == "clusterB")
    assert clusterB.clicks == 2
    assert clusterB.views == 20
    assert clusterB.spend == 2.0
    assert clusterB.query == "30"
    assert clusterB.childs_keywords == [kw3]


@pytest.mark.usefixtures("mock_keywords_query")
def test_calculate_clusters_no_query():
    kw1 = CalculatedKeyword(text="k1", clicks=10, views=100, spend=10.0)
    preset_to_keywords = {1: [kw1]}
    preset_to_cluster_name = {1: "cluster1"}

    clusters = __calculate_clusters(preset_to_keywords, preset_to_cluster_name)
    assert clusters[0].query == "10"


def test_calculate_clusters_empty_input():
    clusters = __calculate_clusters({}, {})
    assert len(clusters) == 0


@pytest.mark.asyncio
@patch('app.utils.click_house.client.get_clickhouse_client')
async def test_get_keyword_statistic_clickhouse_basic_case(mock_get_clickhouse_client):
    mock_client = AsyncMock()
    mock_client.query.return_value.result_rows = [[100, 200, 50.0]]  # clicks, views, spend
    mock_get_clickhouse_client.return_value.__aenter__.return_value = mock_client

    adv_ids = {123}
    text = "keyword_test"

    clicks, views, spend = await get_keyword_statistic_clickhouse(mock_client, text, adv_ids)

    assert clicks == 100
    assert views == 200
    assert spend == 50.0
    mock_client.query.assert_called_once()


@pytest.mark.asyncio
@patch('app.utils.click_house.client.get_clickhouse_client')
async def test_get_keyword_statistic_clickhouse_no_results(mock_get_clickhouse_client):
    mock_client = AsyncMock()
    mock_client.query.return_value.result_rows = []
    mock_get_clickhouse_client.return_value.__aenter__.return_value = mock_client

    adv_ids = {123}
    text = "non_existent_keyword"

    clicks, views, spend = await get_keyword_statistic_clickhouse(mock_client, text, adv_ids)

    assert clicks == 0
    assert views == 0
    assert spend == 0.0
    mock_client.query.assert_called_once()


@pytest.mark.asyncio
@patch('app.utils.click_house.client.get_clickhouse_client')
async def test_get_keyword_statistic_clickhouse_clicks_greater_than_views(mock_get_clickhouse_client):
    mock_client = AsyncMock()
    mock_client.query.return_value.result_rows = [[300, 100, 75.0]]  # clicks > views
    mock_get_clickhouse_client.return_value.__aenter__.return_value = mock_client

    adv_ids = {123}
    text = "keyword_high_clicks"

    clicks, views, spend = await get_keyword_statistic_clickhouse(mock_client, text, adv_ids)

    assert clicks == 300
    assert views == 300  # views должны быть равны clicks
    assert spend == 75.0
    mock_client.query.assert_called_once()


@pytest.mark.asyncio
@patch('app.utils.click_house.client.get_clickhouse_client')
async def test_get_keyword_statistic_clickhouse_with_pass_days(mock_get_clickhouse_client):
    mock_client = AsyncMock()
    mock_client.query.return_value.result_rows = [[50, 100, 25.0]]
    mock_get_clickhouse_client.return_value.__aenter__.return_value = mock_client

    adv_ids = {123}
    text = "keyword_pass_days"
    pass_days = 1

    clicks, views, spend = await get_keyword_statistic_clickhouse(mock_client, text, adv_ids, pass_days)

    assert clicks == 50
    assert views == 100
    assert spend == 25.0

    # Проверяем, что запрос содержит условие 'AND date >= '
    called_query = mock_client.query.call_args[0][0]
    expected_date = (datetime.now().date() - timedelta(days=pass_days)).strftime('%Y-%m-%d')
    assert f"AND date >= '{expected_date}'" in called_query
    mock_client.query.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.get_clickhouse_client')
@patch('app.utils.redis_manager.set_predict_ctrs')
async def test_get_keywords_statistic_clickhouse_basic(
    mock_set_predict_ctrs, mock_get_clickhouse_client
):
    mock_ch_client = AsyncMock()
    mock_ch_client.query.return_value.result_rows = [
        ["kw1", 10, 100, 1.0],
        ["kw2", 20, 200, 2.0],
    ]
    mock_get_clickhouse_client.return_value.__aenter__.return_value = mock_ch_client

    mock_set_predict_ctrs.side_effect = lambda adv_id, keywords: keywords  # Просто возвращаем переданные ключевые слова

    adv_setting = MagicMock(id=1, adv_id=101, nmids=[1], search_adv_id=None, clusters_mode=False)

    keywords = await get_keywords_statistic_clickhouse(adv_setting)

    assert len(keywords) == 2
    assert keywords[0].text == "kw1"
    assert keywords[0].clicks == 10
    assert keywords[0].views == 100
    assert keywords[0].spend == 1.0

    assert keywords[1].text == "kw2"
    assert keywords[1].clicks == 20
    assert keywords[1].views == 200
    assert keywords[1].spend == 2.0

    mock_get_clickhouse_client.assert_called_once()
    mock_ch_client.query.assert_called_once()
    mock_set_predict_ctrs.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.get_clickhouse_client')
@patch('app.utils.redis_manager.set_predict_ctrs')
async def test_get_keywords_statistic_clickhouse_no_search_adv_id(
    mock_set_predict_ctrs, mock_get_clickhouse_client
):
    mock_ch_client = AsyncMock()
    mock_ch_client.query.return_value.result_rows = [["kw1", 10, 100, 1.0]]
    mock_get_clickhouse_client.return_value.__aenter__.return_value = mock_ch_client
    mock_set_predict_ctrs.side_effect = lambda adv_id, keywords: keywords

    adv_setting = MagicMock(id=1, adv_id=101, nmids=[1], search_adv_id=None, clusters_mode=False)
    await get_keywords_statistic_clickhouse(adv_setting)

    called_query_args = mock_ch_client.query.call_args[0]
    assert "adv_id IN (101)" in called_query_args[0]


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.get_clickhouse_client')
@patch('app.utils.redis_manager.set_predict_ctrs')
async def test_get_keywords_statistic_clickhouse_with_search_adv_id(
    mock_set_predict_ctrs, mock_get_clickhouse_client
):
    mock_ch_client = AsyncMock()
    mock_ch_client.query.return_value.result_rows = [["kw1", 10, 100, 1.0]]
    mock_get_clickhouse_client.return_value.__aenter__.return_value = mock_ch_client
    mock_set_predict_ctrs.side_effect = lambda adv_id, keywords: keywords

    adv_setting = MagicMock(id=1, adv_id=101, nmids=[1], search_adv_id=102, clusters_mode=False)
    await get_keywords_statistic_clickhouse(adv_setting)

    called_query_args = mock_ch_client.query.call_args[0]
    assert "adv_id IN (101, 102)" in called_query_args[0]


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.get_clickhouse_client')
@patch('app.utils.redis_manager.set_predict_ctrs')
async def test_get_keywords_statistic_clickhouse_clicks_greater_than_views(
    mock_set_predict_ctrs, mock_get_clickhouse_client
):
    mock_ch_client = AsyncMock()
    mock_ch_client.query.return_value.result_rows = [
        ["kw1", 150, 100, 1.0],  # clicks > views
    ]
    mock_get_clickhouse_client.return_value.__aenter__.return_value = mock_ch_client
    mock_set_predict_ctrs.side_effect = lambda adv_id, keywords: keywords

    adv_setting = MagicMock(id=1, adv_id=101, nmids=[1], search_adv_id=None, clusters_mode=False)
    keywords = await get_keywords_statistic_clickhouse(adv_setting)

    assert len(keywords) == 1
    assert keywords[0].text == "kw1"
    assert keywords[0].clicks == 150
    assert keywords[0].views == 150  # views должны быть равны clicks
    assert keywords[0].spend == 1.0


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm') # Мокируем get_async_session_maker
async def test_get_keyword_settings_basic(mock_sm):
    mock_session = AsyncMock()
    mock_sm.return_value.__aenter__.return_value = mock_session

    # Создаем фиктивные объекты KeywordSetting
    kw_setting1 = KeywordSetting(id=1, text="keyword1", adv_setting_id=100, hard_status=1)
    kw_setting2 = KeywordSetting(id=2, text="keyword2", adv_setting_id=100, hard_status=2)

    # Мокируем result.scalars().all()
    mock_result = MagicMock()  # Это результат await session.execute(stmt)
    mock_scalars = MagicMock()  # Это результат result.scalars()
    mock_scalars.all.return_value = [kw_setting1, kw_setting2]  # .all() возвращает список
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    adv_setting_id = 100
    result = await _get_keyword_settings(adv_setting_id, None)

    assert len(result) == 2
    assert result[0].text == "keyword1"
    assert result[1].text == "keyword2"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_keyword_settings_with_hard_statuses_filter(mock_sm):
    mock_session = AsyncMock()
    mock_sm.return_value.__aenter__.return_value = mock_session

    kw_setting1 = KeywordSetting(id=1, text="keyword1", adv_setting_id=100, hard_status=1)
    kw_setting2 = KeywordSetting(id=2, text="keyword2", adv_setting_id=100, hard_status=2)
    kw_setting3 = KeywordSetting(id=3, text="keyword3", adv_setting_id=100, hard_status=0)

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [kw_setting1, kw_setting2, kw_setting3]
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    adv_setting_id = 100
    hard_statuses = [1, 2]
    result = await _get_keyword_settings(adv_setting_id, hard_statuses)

    assert len(result) == 3
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_keyword_settings_no_matching_settings(mock_sm):
    mock_session = AsyncMock()
    mock_sm.return_value.__aenter__.return_value = mock_session

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    adv_setting_id = 999
    result = await _get_keyword_settings(adv_setting_id, None)

    assert len(result) == 0
    mock_session.execute.assert_called_once()
