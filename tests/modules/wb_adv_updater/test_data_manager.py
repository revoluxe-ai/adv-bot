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


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_global_super_wb_user_cabinet_basic(mock_sm):
    mock_session = MagicMock()
    mock_sm.return_value.__aenter__.return_value = mock_session

    # Создаем фиктивные токены без spec, чтобы SQLAlchemy мог добавлять свои атрибуты
    token1 = MagicMock(api_key="token1_key", user_id=1, shop_id="shop1")
    token2 = MagicMock(api_key="token2_key", user_id=1, shop_id="shop1")
    token3 = MagicMock(api_key="token3_key", user_id=2, shop_id="shop2")

    # Создаем фиктивных пользователей без spec
    user1 = MagicMock(id=1, wb_tokens=[token1, token2])
    user2 = MagicMock(id=2, wb_tokens=[token3])

    # Мокируем result.unique().scalars().all() для пользователей
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [user1, user2]
    mock_unique.scalars.return_value = mock_scalars
    mock_result.unique.return_value = mock_unique
    mock_session.execute = AsyncMock(return_value=mock_result)

    cabinet = await get_global_super_wb_user_cabinet()

    assert isinstance(cabinet, WBUserCabinet)
    assert isinstance(cabinet.user, User)
    assert isinstance(cabinet.wb_cabinet, WBCabinet)
    assert len(cabinet.user.wb_tokens) == 3  # Все токены всех пользователей
    assert cabinet.user.wb_tokens[0] == token1
    assert cabinet.user.wb_tokens[1] == token2
    assert cabinet.user.wb_tokens[2] == token3

    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_global_super_wb_user_cabinet_no_users(mock_sm):
    mock_session = MagicMock()
    mock_sm.return_value.__aenter__.return_value = mock_session

    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_unique.scalars.return_value = mock_scalars
    mock_result.unique.return_value = mock_unique
    mock_session.execute = AsyncMock(return_value=mock_result)

    cabinet = await get_global_super_wb_user_cabinet()

    assert isinstance(cabinet, WBUserCabinet)
    assert isinstance(cabinet.user, User)
    assert isinstance(cabinet.wb_cabinet, WBCabinet)
    assert len(cabinet.user.wb_tokens) == 0

    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_global_super_wb_user_cabinet_users_no_tokens(mock_sm):
    mock_session = MagicMock()
    mock_sm.return_value.__aenter__.return_value = mock_session

    user1 = MagicMock(spec=User, id=1, wb_tokens=[])
    user2 = MagicMock(spec=User, id=2, wb_tokens=[])

    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [user1, user2]
    mock_unique.scalars.return_value = mock_scalars
    mock_result.unique.return_value = mock_unique
    mock_session.execute = AsyncMock(return_value=mock_result)

    cabinet = await get_global_super_wb_user_cabinet()

    assert isinstance(cabinet, WBUserCabinet)
    assert isinstance(cabinet.user, User)
    assert isinstance(cabinet.wb_cabinet, WBCabinet)
    assert len(cabinet.user.wb_tokens) == 0

    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_set_positions_basic(mock_redis_manager):
    # Создаем фиктивные данные
    kw1 = CalculatedKeyword(text="keyword1", views=100, clicks=10, spend=10.0)
    kw2 = CalculatedKeyword(text="keyword2", views=200, clicks=20, spend=20.0)
    keyword_stats = [kw1, kw2]

    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[1])

    # Мокируем позиции из Redis
    position1 = MagicMock(spec=WBItemPosition, keyword_text="keyword1", position=5)
    position2 = MagicMock(spec=WBItemPosition, keyword_text="keyword2", position=10)
    mock_redis_manager.get_keywords_positions = AsyncMock(return_value=[position1, position2])

    # Мокируем кластеры и пресеты
    mock_redis_manager.get_cluster_and_preset = AsyncMock(return_value=("cluster1", "preset1"))

    result = await set_positions(keyword_stats, adv_setting)

    assert len(result) == 2
    assert result[0].position == 5
    assert result[0].cluster_name == "cluster1"
    assert result[0].preset == "preset1"
    assert result[1].position == 10
    assert result[1].cluster_name == "cluster1"
    assert result[1].preset == "preset1"

    mock_redis_manager.get_keywords_positions.assert_called_once_with(adv_setting, ["keyword1", "keyword2"])
    assert mock_redis_manager.get_cluster_and_preset.call_count == 2


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_set_positions_redis_error(mock_redis_manager):
    kw1 = CalculatedKeyword(text="keyword1", views=100, clicks=10, spend=10.0)
    keyword_stats = [kw1]

    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[1])

    # Мокируем ошибку при получении позиций
    mock_redis_manager.get_keywords_positions = AsyncMock(side_effect=Exception("Redis error"))

    result = await set_positions(keyword_stats, adv_setting)

    # Функция должна вернуть исходный список без изменений
    assert len(result) == 1
    assert result[0] == kw1
    assert not hasattr(result[0], 'position') or result[0].position is None

    mock_redis_manager.get_keywords_positions.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_set_positions_cluster_error(mock_redis_manager):
    kw1 = CalculatedKeyword(text="keyword1", views=100, clicks=10, spend=10.0)
    kw2 = CalculatedKeyword(text="keyword2", views=200, clicks=20, spend=20.0)
    keyword_stats = [kw1, kw2]

    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[1])

    position1 = MagicMock(spec=WBItemPosition, keyword_text="keyword1", position=5)
    position2 = MagicMock(spec=WBItemPosition, keyword_text="keyword2", position=10)
    mock_redis_manager.get_keywords_positions = AsyncMock(return_value=[position1, position2])

    # Мокируем ошибку при получении кластера для первого keyword, успех для второго
    mock_redis_manager.get_cluster_and_preset = AsyncMock(
        side_effect=[Exception("Cluster error"), ("cluster2", "preset2")]
    )

    result = await set_positions(keyword_stats, adv_setting)

    assert len(result) == 2
    # Первый keyword пропущен из-за ошибки (continue), поэтому ни позиция, ни кластер не установлены
    assert not hasattr(result[0], 'position') or result[0].position is None
    assert not hasattr(result[0], 'cluster_name') or result[0].cluster_name is None
    # Второй keyword должен иметь и позицию, и кластер
    assert result[1].position == 10
    assert result[1].cluster_name == "cluster2"
    assert result[1].preset == "preset2"


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_set_positions_with_child_keywords(mock_redis_manager):
    # Создаем keyword с дочерними ключевыми словами
    child_kw1 = CalculatedKeyword(text="child1", views=50, clicks=5, spend=5.0)
    child_kw2 = CalculatedKeyword(text="child2", views=60, clicks=6, spend=6.0)
    
    parent_kw = CalculatedKeyword(text="parent", views=110, clicks=11, spend=11.0)
    parent_kw.childs_keywords = [child_kw1, child_kw2]
    
    keyword_stats = [parent_kw]

    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[1])

    # Мокируем: нет позиции для родительского keyword
    mock_redis_manager.get_keywords_positions = AsyncMock(side_effect=[
        [],  # Первый вызов: нет позиций для "parent"
        [  # Второй вызов: есть позиции для дочерних keywords
            MagicMock(spec=WBItemPosition, keyword_text="child1", position=15, timestamp=datetime(2023, 1, 1)),
            MagicMock(spec=WBItemPosition, keyword_text="child2", position=20, timestamp=datetime(2023, 1, 2)),
        ]
    ])

    mock_redis_manager.get_cluster_and_preset = AsyncMock(return_value=("cluster_parent", "preset_parent"))

    result = await set_positions(keyword_stats, adv_setting)

    assert len(result) == 1
    # Должна быть установлена позиция из дочернего keyword с максимальным timestamp
    assert result[0].position == 20  # child2 имеет более поздний timestamp
    assert result[0].cluster_name == "cluster_parent"
    assert result[0].preset == "preset_parent"

    assert mock_redis_manager.get_keywords_positions.call_count == 2


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_set_position_basic(mock_redis_manager):
    kw = CalculatedKeyword(text="keyword1", views=100, clicks=10, spend=10.0)
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[12345])

    # Мокируем позицию из Redis
    position = MagicMock(spec=WBItemPosition, keyword_text="keyword1", position=25)
    mock_redis_manager.get_keyword_position = AsyncMock(return_value=position)

    result = await set_position(kw, adv_setting)

    assert result.position == 25
    mock_redis_manager.get_keyword_position.assert_called_once_with("keyword1", 12345)


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_set_position_no_position_found(mock_redis_manager):
    kw = CalculatedKeyword(text="keyword1", views=100, clicks=10, spend=10.0)
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[12345])

    # Мокируем: нет позиции
    mock_redis_manager.get_keyword_position = AsyncMock(return_value=None)

    result = await set_position(kw, adv_setting)

    # Позиция не должна быть установлена
    assert not hasattr(result, 'position') or result.position is None
    mock_redis_manager.get_keyword_position.assert_called_once_with("keyword1", 12345)


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_set_position_with_child_keywords(mock_redis_manager):
    child_kw1 = CalculatedKeyword(text="child1", views=50, clicks=5, spend=5.0)
    child_kw2 = CalculatedKeyword(text="child2", views=60, clicks=6, spend=6.0)
    
    parent_kw = CalculatedKeyword(text="parent", views=110, clicks=11, spend=11.0)
    parent_kw.childs_keywords = [child_kw1, child_kw2]
    
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[12345])

    # Мокируем: нет позиции для родительского keyword
    mock_redis_manager.get_keyword_position = AsyncMock(return_value=None)
    
    # Мокируем: есть позиции для дочерних keywords
    mock_redis_manager.get_keywords_positions = AsyncMock(return_value=[
        MagicMock(spec=WBItemPosition, keyword_text="child1", position=30, timestamp=datetime(2023, 1, 1)),
        MagicMock(spec=WBItemPosition, keyword_text="child2", position=35, timestamp=datetime(2023, 1, 2)),
    ])

    result = await set_position(parent_kw, adv_setting)

    assert result.position == 35  # child2 имеет более поздний timestamp
    mock_redis_manager.get_keyword_position.assert_called_once_with("parent", 12345)
    mock_redis_manager.get_keywords_positions.assert_called_once_with(adv_setting, ["child1", "child2"])


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_set_position_no_child_positions(mock_redis_manager):
    child_kw1 = CalculatedKeyword(text="child1", views=50, clicks=5, spend=5.0)
    
    parent_kw = CalculatedKeyword(text="parent", views=110, clicks=11, spend=11.0)
    parent_kw.childs_keywords = [child_kw1]
    
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[12345])

    # Мокируем: нет позиции для родительского keyword и нет позиций для дочерних
    mock_redis_manager.get_keyword_position = AsyncMock(return_value=None)
    mock_redis_manager.get_keywords_positions = AsyncMock(return_value=[])

    result = await set_position(parent_kw, adv_setting)

    # Позиция не должна быть установлена
    assert not hasattr(result, 'position') or result.position is None
    mock_redis_manager.get_keyword_position.assert_called_once_with("parent", 12345)
    mock_redis_manager.get_keywords_positions.assert_called_once_with(adv_setting, ["child1"])


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_get_keywords_positions_basic(mock_redis_manager):
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[12345])
    texts = ["keyword1", "keyword2", "keyword3"]

    # Мокируем позиции из Redis
    positions = [
        MagicMock(spec=WBItemPosition, keyword_text="keyword1", position=10),
        MagicMock(spec=WBItemPosition, keyword_text="keyword2", position=20),
        MagicMock(spec=WBItemPosition, keyword_text="keyword3", position=30),
    ]
    mock_redis_manager.get_keywords_positions = AsyncMock(return_value=positions)

    result = await get_keywords_positions(adv_setting, texts)

    assert len(result) == 3
    assert result[0].position == 10
    assert result[1].position == 20
    assert result[2].position == 30
    mock_redis_manager.get_keywords_positions.assert_called_once_with(adv_setting, texts)


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_get_keywords_positions_empty_list(mock_redis_manager):
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[12345])
    texts = []

    mock_redis_manager.get_keywords_positions = AsyncMock(return_value=[])

    result = await get_keywords_positions(adv_setting, texts)

    assert len(result) == 0
    mock_redis_manager.get_keywords_positions.assert_called_once_with(adv_setting, texts)


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_get_keywords_positions_no_results(mock_redis_manager):
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[12345])
    texts = ["keyword1", "keyword2"]

    # Мокируем: Redis не нашел позиций
    mock_redis_manager.get_keywords_positions = AsyncMock(return_value=[])

    result = await get_keywords_positions(adv_setting, texts)

    assert len(result) == 0
    mock_redis_manager.get_keywords_positions.assert_called_once_with(adv_setting, texts)


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_keywords_query")
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_convert_keyword_stats_in_clusters_basic(mock_redis_manager):
    kw1 = CalculatedKeyword(text="k1", clicks=10, views=100, spend=10.0)
    kw2 = CalculatedKeyword(text="k2", clicks=20, views=200, spend=20.0)
    kw3 = CalculatedKeyword(text="k3", clicks=5, views=50, spend=5.0)
    keyword_stats = [kw1, kw2, kw3]

    # Мокируем: k1 и k2 в одном кластере, k3 в другом
    mock_redis_manager.get_clusters_and_presets = AsyncMock(return_value={
        "k1": ("Cluster A", 1),
        "k2": ("Cluster A", 1),
        "k3": ("Cluster B", 2),
    })

    result = await convert_keyword_stats_in_clusters(keyword_stats)

    assert len(result) == 2  # Два кластера
    # Проверяем, что кластеры правильно агрегированы
    cluster_a = next((c for c in result if c.text == "Cluster A"), None)
    cluster_b = next((c for c in result if c.text == "Cluster B"), None)
    
    assert cluster_a is not None
    assert cluster_a.clicks == 30  # 10 + 20
    assert cluster_a.views == 300  # 100 + 200
    
    assert cluster_b is not None
    assert cluster_b.clicks == 5
    assert cluster_b.views == 50

    mock_redis_manager.get_clusters_and_presets.assert_called_once_with(["k1", "k2", "k3"])


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_keywords_query")
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_convert_keyword_stats_in_clusters_no_cluster_info(mock_redis_manager):
    kw1 = CalculatedKeyword(text="k1", clicks=10, views=100, spend=10.0)
    kw2 = CalculatedKeyword(text="k2", clicks=20, views=200, spend=20.0)
    keyword_stats = [kw1, kw2]

    # Мокируем: нет информации о кластерах
    mock_redis_manager.get_clusters_and_presets = AsyncMock(return_value={})

    result = await convert_keyword_stats_in_clusters(keyword_stats)

    # Каждое ключевое слово становится своим собственным кластером
    assert len(result) == 2
    assert result[0].text == "k1"
    assert result[0].clicks == 10
    assert result[1].text == "k2"
    assert result[1].clicks == 20


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_convert_keyword_stats_in_clusters_redis_error(mock_redis_manager):
    kw1 = CalculatedKeyword(text="k1", clicks=10, views=100, spend=10.0)
    keyword_stats = [kw1]

    # Мокируем ошибку Redis
    mock_redis_manager.get_clusters_and_presets = AsyncMock(side_effect=Exception("Redis error"))

    result = await convert_keyword_stats_in_clusters(keyword_stats)

    # При ошибке возвращается исходный список
    assert len(result) == 1
    assert result[0] == kw1
    mock_redis_manager.get_clusters_and_presets.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_keywords_query")
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
async def test_convert_keyword_stats_in_clusters_mixed(mock_redis_manager):
    kw1 = CalculatedKeyword(text="k1", clicks=10, views=100, spend=10.0)
    kw2 = CalculatedKeyword(text="k2", clicks=20, views=200, spend=20.0)
    kw3 = CalculatedKeyword(text="k3", clicks=5, views=50, spend=5.0)
    keyword_stats = [kw1, kw2, kw3]

    # Мокируем: только k1 имеет кластер, остальные нет
    mock_redis_manager.get_clusters_and_presets = AsyncMock(return_value={
        "k1": ("Cluster A", 1),
    })

    result = await convert_keyword_stats_in_clusters(keyword_stats)

    # Один кластер "Cluster A" и два отдельных ключевых слова k2, k3
    assert len(result) == 3
    
    cluster_texts = {c.text for c in result}
    assert "Cluster A" in cluster_texts
    assert "k2" in cluster_texts
    assert "k3" in cluster_texts


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
@patch('app.modules.wb_adv_updater.data_manager.FullAdvStat')
async def test_get_full_adv_stat_for_adv_id_from_redis_basic(mock_full_adv_stat_cls, mock_redis_manager):
    adv_id = 123
    full_stat_json = '{"field1": "value1", "field2": 123}'
    mock_redis_manager.get_full_stat_adv = AsyncMock(return_value=full_stat_json)

    mock_full_adv_stat_instance = MagicMock(spec=FullAdvStat)
    mock_full_adv_stat_cls.model_validate.return_value = mock_full_adv_stat_instance

    result = await get_full_adv_stat_for_adv_id_from_redis(adv_id)

    assert result == mock_full_adv_stat_instance
    mock_redis_manager.get_full_stat_adv.assert_called_once_with(adv_id)
    mock_full_adv_stat_cls.model_validate.assert_called_once_with(json.loads(full_stat_json))


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.redis_manager')
@patch('app.modules.wb_adv_updater.data_manager.FullAdvStat')
async def test_get_full_adv_stat_for_adv_id_from_redis_not_found(mock_full_adv_stat_cls, mock_redis_manager):
    adv_id = 123
    mock_redis_manager.get_full_stat_adv = AsyncMock(side_effect=DataNotFoundError)

    result = await get_full_adv_stat_for_adv_id_from_redis(adv_id)

    assert result is None
    mock_redis_manager.get_full_stat_adv.assert_called_once_with(adv_id)
    mock_full_adv_stat_cls.model_validate.assert_not_called()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.get_good_bad_phrases_for_min_ctr')
@patch('app.modules.wb_adv_updater.data_manager.RedisCalculatedKeywordsCacheManager')
async def test_get_good_bad_phrases_basic(mock_redis_cache_manager_cls, mock_get_good_bad_phrases_for_min_ctr):
    """Тест базового функционала get_good_bad_phrases"""
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, max_cpc=100, exponent_predict_ctr=0.5)

    # Мокируем ключевые слова, возвращаемые get_good_bad_phrases_for_min_ctr
    # Используем настоящие CalculatedKeyword объекты
    # rating_by_predict_ctr = predict_ctr**predict_ctr_exponent * views
    # Функция get_good_bad_phrases устанавливает predict_ctr_exponent=0.5 для всех keywords
    # Поэтому используем predict_ctr_exponent=0.5 изначально
    # Для kw1: 0.1**0.5 * 100 ≈ 31.6
    kw1 = CalculatedKeyword(text="kw1", views=100, clicks=10, spend=10.0, predict_ctr=0.1, predict_ctr_exponent=0.5)
    # Для kw2: predict_ctr=None дает rating 0.0
    kw2 = CalculatedKeyword(text="kw2", views=50, clicks=5, spend=5.0, predict_ctr=None, predict_ctr_exponent=None)
    # Для kw3: 0.2**0.5 * 100 ≈ 44.7 (больше чем kw1)
    kw3 = CalculatedKeyword(text="kw3", views=100, clicks=20, spend=20.0, predict_ctr=0.2, predict_ctr_exponent=0.5)
    mock_get_good_bad_phrases_for_min_ctr.return_value = [
        kw1, kw2, kw3
    ]

    # Мокируем RedisCalculatedKeywordsCacheManager
    mock_redis_cache_manager_instance = AsyncMock()
    mock_redis_cache_manager_cls.return_value = mock_redis_cache_manager_instance

    result = await get_good_bad_phrases(adv_setting)

    # Проверяем, что predict_ctr_exponent установлен для всех ключевых слов
    assert result[0].predict_ctr_exponent == 0.5
    assert result[1].predict_ctr_exponent == 0.5
    assert result[2].predict_ctr_exponent == 0.5

    # Проверяем сортировку: сначала с рейтингом (по убыванию), потом без рейтинга
    # kw3 (rating 44.7) -> kw1 (rating 31.6) -> kw2 (rating 0.0)
    assert result[0].text == "kw3"
    assert result[1].text == "kw1"
    assert result[2].text == "kw2"
    
    mock_get_good_bad_phrases_for_min_ctr.assert_called_once_with(adv_setting, adv_setting.max_cpc)
    mock_redis_cache_manager_cls.assert_called_once()
    mock_redis_cache_manager_instance.set_calculated_keywords.assert_called_once()
    
    # Проверяем аргументы, переданные в set_calculated_keywords
    call_args, call_kwargs = mock_redis_cache_manager_instance.set_calculated_keywords.call_args
    assert call_kwargs == {}
    
    actual_keywords_passed = call_args[0]
    actual_adv_id_passed = call_args[1]
    
    assert actual_adv_id_passed == adv_setting.adv_id
    assert len(actual_keywords_passed) == 3
    
    # Проверяем атрибуты каждого ключевого слова в переданном списке
    # ВАЖНО: set_calculated_keywords вызывается ДО сортировки,
    # поэтому порядок здесь должен быть [kw1, kw2, kw3] (исходный порядок из mock)
    assert actual_keywords_passed[0].text == "kw1"
    assert actual_keywords_passed[0].predict_ctr_exponent == 0.5

    assert actual_keywords_passed[1].text == "kw2"
    assert actual_keywords_passed[1].predict_ctr_exponent == 0.5

    assert actual_keywords_passed[2].text == "kw3"
    assert actual_keywords_passed[2].predict_ctr_exponent == 0.5


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.get_good_bad_phrases_for_min_ctr')
@patch('app.modules.wb_adv_updater.data_manager.RedisCalculatedKeywordsCacheManager')
async def test_get_good_bad_phrases_no_keywords(mock_redis_cache_manager_cls, mock_get_good_bad_phrases_for_min_ctr):
    """Тест get_good_bad_phrases с пустым списком ключевых слов"""
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, max_cpc=100, exponent_predict_ctr=0.5)

    mock_get_good_bad_phrases_for_min_ctr.return_value = []

    mock_redis_cache_manager_instance = AsyncMock()
    mock_redis_cache_manager_cls.return_value = mock_redis_cache_manager_instance

    result = await get_good_bad_phrases(adv_setting)

    assert len(result) == 0
    mock_get_good_bad_phrases_for_min_ctr.assert_called_once_with(adv_setting, adv_setting.max_cpc)
    mock_redis_cache_manager_cls.assert_called_once()
    mock_redis_cache_manager_instance.set_calculated_keywords.assert_called_once_with([], adv_setting.adv_id)

  
  # Получаем функцию __set_predict_ctr через getattr
__set_predict_ctr = getattr(data_manager, '_DataManager__set_predict_ctr', None) or getattr(data_manager, '__set_predict_ctr', None)
if __set_predict_ctr is None:
    # Попробуем получить через dir
    for name in dir(data_manager):
        if 'set_predict_ctr' in name:
            __set_predict_ctr = getattr(data_manager, name)
            break


def test_set_predict_ctr_basic():
    """Тест базового функционала __set_predict_ctr"""
    adv_setting = MagicMock(spec=AdvSetting, exponent_predict_ctr=0.5)
    
    kw1 = CalculatedKeyword(text="keyword1", views=100, clicks=10, spend=10.0)
    kw1.original_predict_ctr = 0.1
    keyword_stats = [kw1]
    
    result = __set_predict_ctr(keyword_stats, min_ctr=0.01, adv_setting=adv_setting)
    
    assert len(result) == 1
    assert result[0].predict_ctr_exponent == 0.5
    assert result[0].enough_views == 100  # int(1 / 0.01)
    assert result[0].baes_ctr is not None
    assert result[0].predict_ctr is not None


def test_set_predict_ctr_zero_min_ctr():
    """Тест __set_predict_ctr с min_ctr=0"""
    adv_setting = MagicMock(spec=AdvSetting, exponent_predict_ctr=1.0)
    
    kw1 = CalculatedKeyword(text="keyword1", views=100, clicks=10, spend=10.0)
    keyword_stats = [kw1]
    
    result = __set_predict_ctr(keyword_stats, min_ctr=0, adv_setting=adv_setting)
    
    assert len(result) == 1
    assert result[0].enough_views == 100  # Когда min_ctr=0


def test_set_predict_ctr_zero_clicks():
    """Тест __set_predict_ctr с clicks=0"""
    adv_setting = MagicMock(spec=AdvSetting, exponent_predict_ctr=0.5)
    
    kw1 = CalculatedKeyword(text="keyword1", views=100, clicks=0, spend=10.0)
    keyword_stats = [kw1]
    
    result = __set_predict_ctr(keyword_stats, min_ctr=0.01, adv_setting=adv_setting)
    
    assert len(result) == 1
    # clicks += 1, views += enough_views_calc (100)
    # Но т.к. original_predict_ctr=None, predicted clicks/views не добавляются
    assert result[0].calculated_clicks == 1  # 0 + 1
    assert result[0].calculated_views == 200  # 100 + 100


def test_set_predict_ctr_with_added_clicks():
    """Тест __set_predict_ctr с added_clicks"""
    adv_setting = MagicMock(spec=AdvSetting, exponent_predict_ctr=0.5)
    
    kw1 = CalculatedKeyword(text="keyword1", views=100, clicks=10, spend=10.0)
    kw1.added_clicks = 5
    keyword_stats = [kw1]
    
    result = __set_predict_ctr(keyword_stats, min_ctr=0.01, adv_setting=adv_setting)
    
    assert len(result) == 1
    # clicks должен увеличиться на added_clicks
    assert result[0].calculated_clicks >= 15  # 10 + 5


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_wb_category_basic(mock_sm):
    """Тест get_wb_category с успешным получением категории"""
    adv_setting = MagicMock(spec=AdvSetting, nmids=[123])
    
    mock_wb_category = MagicMock(spec=WBCategory, wb_category_name="TestCategory")
    mock_wb_card = MagicMock(spec=WBCard, nmid=123, wb_category=mock_wb_category)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_wb_card
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_wb_category(adv_setting)
    
    assert result == mock_wb_category
    mock_sm.assert_called_once()
    mock_session.execute.assert_called_once()
    mock_result.scalar_one_or_none.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_wb_category_no_nmids(mock_sm):
    """Тест get_wb_category с пустым списком nmids (вызывает исключение NotItemsInAdvSetting)"""
    adv_setting = MagicMock(spec=AdvSetting, nmids=[])
    
    with pytest.raises(NotItemsInAdvSetting, match="У кампании в базе нет товаров"):
        await get_wb_category(adv_setting)
    
    mock_sm.assert_not_called()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_wb_category_card_not_found(mock_sm):
    """Тест get_wb_category, когда карточка товара не найдена (вызывает исключение CardNotFoundInDB)"""
    adv_setting = MagicMock(spec=AdvSetting, nmids=[123])
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    with pytest.raises(CardNotFoundInDB, match="В базе не найдена карточка товара: 123"):
        await get_wb_category(adv_setting)

    mock_sm.assert_called_once()
    mock_session.execute.assert_called_once()
    mock_result.scalar_one_or_none.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_main_photos_basic(mock_sm):
    """Тест get_main_photos с успешным получением фотографий"""
    nmids = [1, 2]
    
    mock_wb_card1 = MagicMock(spec=WBCard, photos=["url1_1", "url1_2"])
    mock_wb_card2 = MagicMock(spec=WBCard, photos=["url2_1", "url2_2"])
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = [mock_wb_card1, mock_wb_card2]
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_main_photos(nmids)
    
    assert result == ["url1_1", "url2_1"]
    mock_sm.assert_called_once()
    mock_session.execute.assert_called_once()
    mock_result.unique.assert_called_once()
    mock_unique.scalars.assert_called_once()
    mock_scalars.all.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_main_photos_no_nmids(mock_sm):
    """Тест get_main_photos с пустым списком nmids"""
    nmids = []
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = []
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_main_photos(nmids)
    
    assert result == []
    mock_sm.assert_called_once()
    mock_session.execute.assert_called_once_with(ANY)
    mock_result.unique.assert_called_once()
    mock_unique.scalars.assert_called_once()
    mock_scalars.all.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_main_photos_no_cards_found(mock_sm):
    """Тест get_main_photos, когда карточки не найдены"""
    nmids = [1, 2]
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = []
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_main_photos(nmids)
    
    assert result == []
    mock_sm.assert_called_once()
    mock_session.execute.assert_called_once()
    mock_result.unique.assert_called_once()
    mock_unique.scalars.assert_called_once()
    mock_scalars.all.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_adv_keyword_text_in_black_list_basic(mock_sm):
    """Тест get_adv_keyword_text_in_black_list с базовыми данными"""
    mock_adv_setting1 = MagicMock(spec=AdvSetting, id=1, adv_id=101)
    mock_adv_setting2 = MagicMock(spec=AdvSetting, id=2, adv_id=102)
    
    mock_keyword_setting1 = MagicMock(spec=KeywordSetting, text="black_kw1", hard_status=0, adv_setting=mock_adv_setting1)
    mock_keyword_setting2 = MagicMock(spec=KeywordSetting, text="black_kw2", hard_status=0, adv_setting=mock_adv_setting2)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = [mock_keyword_setting1, mock_keyword_setting2]
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_adv_keyword_text_in_black_list()
    
    assert len(result) == 2
    assert (101, "black_kw1") in result
    assert (102, "black_kw2") in result
    
    mock_sm.assert_called_once()
    mock_session.execute.assert_called_once()
    mock_result.unique.assert_called_once()
    mock_unique.scalars.assert_called_once()
    mock_scalars.all.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_adv_keyword_text_in_black_list_no_results(mock_sm):
    """Тест get_adv_keyword_text_in_black_list без результатов"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = []
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_adv_keyword_text_in_black_list()
    
    assert len(result) == 0
    assert result == []
    
    mock_sm.assert_called_once()
    mock_session.execute.assert_called_once()
    mock_result.unique.assert_called_once()
    mock_unique.scalars.assert_called_once()
    mock_scalars.all.assert_called_once()


# Тесты для get_all_shops_for_user
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_all_shops_for_user_basic(mock_sm):
    """Тест get_all_shops_for_user с базовыми данными"""
    from app.modules.wb_adv_updater.data_manager import get_all_shops_for_user
    
    user = MagicMock(id=1)
    
    # Создаем моки без spec для избежания проблем с hybrid properties
    mock_wb_user_cabinet1 = MagicMock()
    mock_wb_user_cabinet2 = MagicMock()
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    # Имитируем result.scalar() который возвращает объект с методом all()
    mock_scalar_result = MagicMock()
    mock_scalar_result.all.return_value = [mock_wb_user_cabinet1, mock_wb_user_cabinet2]
    mock_result.scalar.return_value = mock_scalar_result
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_all_shops_for_user(user)
    
    assert len(result) == 2
    assert result[0] == mock_wb_user_cabinet1
    assert result[1] == mock_wb_user_cabinet2
    
    mock_sm.assert_called_once()
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_all_shops_for_user_no_shops(mock_sm):
    """Тест get_all_shops_for_user когда у пользователя нет магазинов"""
    from app.modules.wb_adv_updater.data_manager import get_all_shops_for_user
    
    user = MagicMock(id=1)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    # Когда нет магазинов, scalar() возвращает None
    mock_result.scalar.return_value = None
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_all_shops_for_user(user)
    
    assert len(result) == 0
    mock_sm.assert_called_once()


# Тесты для get_mean_ctr и get_min_ctr
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
@patch('app.modules.wb_adv_updater.data_manager.get_good_bad_phrases')
async def test_get_mean_ctr_basic(mock_get_good_bad_phrases, mock_sm):
    """Тест get_mean_ctr с базовыми данными"""
    from app.modules.wb_adv_updater.data_manager import get_mean_ctr
    
    adv_setting = MagicMock(id=1, adv_id=101, nmids=[123])
    
    # Мокируем ключевые слова
    kw1 = CalculatedKeyword(text="good_kw1", status="good", views=100, clicks=10, spend=10)
    kw2 = CalculatedKeyword(text="good_kw2", status="good", views=200, clicks=20, spend=20)
    mock_get_good_bad_phrases.return_value = [kw1, kw2]
    
    # Мокируем сессию БД
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 0.05
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_mean_ctr(adv_setting)
    
    assert result == 0.05
    mock_get_good_bad_phrases.assert_called_once_with(adv_setting)


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.MinCtrManager')
async def test_get_min_ctr_basic(mock_min_ctr_manager_cls):
    """Тест get_min_ctr с базовыми данными"""
    from app.modules.wb_adv_updater.data_manager import get_min_ctr
    
    adv_setting = MagicMock(spec=AdvSetting, adv_id=101, nmids=[123], user_min_ctr=None)
    
    mock_min_ctr_manager = AsyncMock()
    mock_min_ctr_manager.get_min_ctr.return_value = 0.03
    mock_min_ctr_manager_cls.return_value = mock_min_ctr_manager
    
    result = await get_min_ctr(adv_setting)
    
    assert result == 0.03
    mock_min_ctr_manager_cls.assert_called_once()
    mock_min_ctr_manager.get_min_ctr.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.MinCtrManager')
async def test_get_min_ctr_with_user_min_ctr(mock_min_ctr_manager_cls):
    """Тест get_min_ctr с базовой логикой через MinCtrManager"""
    from app.modules.wb_adv_updater.data_manager import get_min_ctr
    
    adv_setting = MagicMock(adv_id=101, nmids=[123])
    
    # Мокируем MinCtrManager
    mock_min_ctr_manager = MagicMock()
    mock_min_ctr_manager.get_min_ctr = AsyncMock(return_value=0.07)
    mock_min_ctr_manager_cls.return_value = mock_min_ctr_manager
    
    result = await get_min_ctr(adv_setting)
    
    assert result == 0.07
    mock_min_ctr_manager_cls.assert_called_once_with(adv_setting)
    mock_min_ctr_manager.get_min_ctr.assert_called_once()


# Тесты для get_active_search_advs
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_active_search_advs_basic(mock_sm):
    """Тест get_active_search_advs с базовыми данными"""
    from app.modules.wb_adv_updater.data_manager import get_active_search_advs
    
    mock_adv1 = MagicMock(id=1, adv_id=101)
    mock_adv2 = MagicMock(id=2, adv_id=102)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = [mock_adv1, mock_adv2]
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_active_search_advs()
    
    assert len(result) == 2
    assert result[0] == mock_adv1
    assert result[1] == mock_adv2
    mock_sm.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_active_search_advs_no_advs(mock_sm):
    """Тест get_active_search_advs когда нет активных кампаний"""
    from app.modules.wb_adv_updater.data_manager import get_active_search_advs
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = []
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_active_search_advs()
    
    assert len(result) == 0
    mock_sm.assert_called_once()


# Тесты для add_white_phrases
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_add_white_phrases_basic(mock_sm):
    """Тест add_white_phrases с базовыми данными"""
    from app.modules.wb_adv_updater.data_manager import add_white_phrases
    
    keywords = ["keyword1", "keyword2"]
    adv_setting_id = 100
    
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    await add_white_phrases(keywords, adv_setting_id)
    
    # Проверяем, что execute был вызван для каждого ключевого слова
    assert mock_session.execute.call_count >= len(keywords)
    mock_session.commit.assert_called_once()
    mock_sm.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_add_white_phrases_empty_list(mock_sm):
    """Тест add_white_phrases с пустым списком"""
    from app.modules.wb_adv_updater.data_manager import add_white_phrases
    
    keywords = []
    adv_setting_id = 100
    
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    await add_white_phrases(keywords, adv_setting_id)
    
    # Не должно быть вызовов execute для пустого списка
    mock_session.execute.assert_not_called()
    mock_session.commit.assert_called_once()


# Тесты для update_black_phrases
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_update_black_phrases_basic(mock_sm):
    """Тест update_black_phrases с базовыми данными"""
    from app.modules.wb_adv_updater.data_manager import update_black_phrases
    
    keywords = ["bad_keyword1", "bad_keyword2"]
    adv_setting_id = 100
    
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    await update_black_phrases(adv_setting_id, keywords)
    
    # Проверяем, что execute был вызван для каждого ключевого слова
    assert mock_session.execute.call_count >= len(keywords)
    mock_session.commit.assert_called_once()
    mock_sm.assert_called_once()


# Тесты для is_adv_in_favorites
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_is_adv_in_favorites_true(mock_sm):
    """Тест is_adv_in_favorites когда кампания в избранном"""
    from app.modules.wb_adv_updater.data_manager import is_adv_in_favorites
    
    adv_setting_id = 100
    user = MagicMock(id=1)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1  # Есть связь
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await is_adv_in_favorites(adv_setting_id, user)
    
    assert result is True
    mock_sm.assert_called_once()
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_is_adv_in_favorites_false(mock_sm):
    """Тест is_adv_in_favorites когда кампании нет в избранном"""
    from app.modules.wb_adv_updater.data_manager import is_adv_in_favorites
    
    adv_setting_id = 100
    user = MagicMock(id=1)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0  # Нет связи
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await is_adv_in_favorites(adv_setting_id, user)
    
    assert result is False
    mock_sm.assert_called_once()


# Тесты для get_expired_cabinets
@pytest.mark.asyncio
async def test_get_expired_cabinets_basic():
    """Тест get_expired_cabinets с базовыми данными"""
    from app.modules.wb_adv_updater.data_manager import get_expired_cabinets
    
    mock_session = AsyncMock()
    
    expired_cabinet = MagicMock(shop_id="expired_shop")
    
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [expired_cabinet]
    mock_result.scalars.return_value = mock_scalars
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    result = await get_expired_cabinets(mock_session)
    
    assert len(result) == 1
    assert result[0] == expired_cabinet
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_expired_cabinets_no_expired():
    """Тест get_expired_cabinets когда нет просроченных кабинетов"""
    from app.modules.wb_adv_updater.data_manager import get_expired_cabinets
    
    mock_session = AsyncMock()
    
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    result = await get_expired_cabinets(mock_session)
    
    assert len(result) == 0
    mock_session.execute.assert_called_once()


# ==================== ТЕСТЫ ДЛЯ КРИТИЧНЫХ ФУНКЦИЙ ====================

# Тесты для clear_keywords (23 использования, НЕ ТЕСТИРОВАНА)
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_clear_keywords_basic(mock_sm):
    """Тест clear_keywords с базовыми данными"""
    from app.modules.wb_adv_updater.data_manager import clear_keywords
    
    need_keywords = ["keep_kw1", "keep_kw2"]
    
    # Мокируем удаляемые ключевые слова
    mock_kw_to_delete1 = MagicMock(text="delete_kw1")
    mock_kw_to_delete2 = MagicMock(text="delete_kw2")
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = [mock_kw_to_delete1, mock_kw_to_delete2]
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    await clear_keywords(need_keywords)
    
    # Проверяем, что execute был вызван с правильными аргументами
    mock_session.execute.assert_called_once()
    # Проверяем, что delete был вызван для каждого удаляемого keyword
    assert mock_session.delete.call_count == 2
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_clear_keywords_empty_to_delete(mock_sm):
    """Тест clear_keywords когда нет ключевых слов для удаления"""
    from app.modules.wb_adv_updater.data_manager import clear_keywords
    
    need_keywords = ["kw1", "kw2", "kw3"]
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = []  # Ничего не удаляем
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    await clear_keywords(need_keywords)
    
    mock_session.delete.assert_not_called()
    mock_session.commit.assert_called_once()


# Тесты для get_last_full_stat_update (4 использования, НЕ ТЕСТИРОВАНА)
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_last_full_stat_update_basic(mock_sm):
    """Тест get_last_full_stat_update с существующей датой"""
    from app.modules.wb_adv_updater.data_manager import get_last_full_stat_update
    
    adv_id = 123
    last_update = datetime(2023, 10, 15, 12, 30, 0)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = last_update
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_last_full_stat_update(adv_id)
    
    assert result == last_update
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_last_full_stat_update_not_found(mock_sm):
    """Тест get_last_full_stat_update когда нет записи"""
    from app.modules.wb_adv_updater.data_manager import get_last_full_stat_update
    
    adv_id = 999
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = None
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_last_full_stat_update(adv_id)
    
    assert result is None
    mock_session.execute.assert_called_once()


# Тесты для set_last_full_stat_update (2 использования, НЕ ТЕСТИРОВАНА)
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_set_last_full_stat_update_basic(mock_sm):
    """Тест set_last_full_stat_update установка последнего обновления"""
    from app.modules.wb_adv_updater.data_manager import set_last_full_stat_update
    
    adv_id = 123
    current_time = datetime.now()
    
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    await set_last_full_stat_update(adv_id, current_time)
    
    # Проверяем, что execute был вызван
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()


# Тесты для get_keywords_statistic (4 использования, НЕ ТЕСТИРОВАНА)
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager.get_good_bad_phrases_for_min_ctr')
async def test_get_keywords_statistic_basic(mock_get_good_bad):
    """Тест get_keywords_statistic с базовыми данными"""
    from app.modules.wb_adv_updater.data_manager import get_keywords_statistic
    
    adv_setting = MagicMock(id=1, adv_id=101)
    
    kw1 = CalculatedKeyword(text="kw1", views=100, clicks=10, spend=10)
    kw2 = CalculatedKeyword(text="kw2", views=200, clicks=20, spend=20)
    mock_get_good_bad.return_value = [kw1, kw2]
    
    result = await get_keywords_statistic(adv_setting)
    
    assert len(result) == 2
    assert result[0].text == "kw1"
    assert result[1].text == "kw2"
    mock_get_good_bad.assert_called_once_with(adv_setting, None)


# Тесты для clear_cards (3 использования, НЕ ТЕСТИРОВАНА)
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_clear_cards_basic(mock_sm):
    """Тест clear_cards удаление карточек из базы"""
    from app.modules.wb_adv_updater.data_manager import clear_cards
    
    need_nmids = [1, 2, 3]
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_card1 = MagicMock(nmid=4)
    mock_card2 = MagicMock(nmid=5)
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = [mock_card1, mock_card2]
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    await clear_cards(need_nmids)
    
    # Проверяем, что delete был вызван для каждой карточки
    assert mock_session.delete.call_count == 2
    # commit должен быть вызван после каждой карточки
    assert mock_session.commit.call_count == 2


# Тесты для get_cpm (4 использования, НЕ ТЕСТИРОВАНА)
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_cpm_basic(mock_sm):
    """Тест get_cpm получение CPM для кампании"""
    from app.modules.wb_adv_updater.data_manager import get_cpm
    
    auto_adv = MagicMock(id=1, adv_id=101)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 15.5
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_cpm(auto_adv)
    
    assert result == 15.5
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_cpm_no_data(mock_sm):
    """Тест get_cpm когда нет данных"""
    from app.modules.wb_adv_updater.data_manager import get_cpm
    
    auto_adv = MagicMock(id=1, adv_id=101)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = None
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_cpm(auto_adv)
    
    assert result is None
    mock_session.execute.assert_called_once()


# Тесты для get_all_shop_ids (2 использования, НЕ ТЕСТИРОВАНА)
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_all_shop_ids_basic(mock_sm):
    """Тест get_all_shop_ids получение всех ID магазинов"""
    from app.modules.wb_adv_updater.data_manager import get_all_shop_ids
    
    mock_cabinet1 = MagicMock(shop_id="shop_1")
    mock_cabinet2 = MagicMock(shop_id="shop_2")
    mock_cabinet3 = MagicMock(shop_id="shop_3")
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_scalars
    mock_scalars.scalars.return_value.all.return_value = ["shop_1", "shop_2", "shop_3"]
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_all_shop_ids()
    
    assert len(result) == 3
    mock_session.execute.assert_called_once()


# Тесты для get_all_active_shop_ids_with_active_advs (2 использования, НЕ ТЕСТИРОВАНА)
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_all_active_shop_ids_with_active_advs_basic(mock_sm):
    """Тест get_all_active_shop_ids_with_active_advs"""
    from app.modules.wb_adv_updater.data_manager import get_all_active_shop_ids_with_active_advs
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_unique
    mock_unique.scalars.return_value = mock_scalars
    mock_scalars.all.return_value = ["shop_1", "shop_2"]
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_all_active_shop_ids_with_active_advs()
    
    assert len(result) == 2
    mock_session.execute.assert_called_once()


# Тесты для get_active_adv_ids_for_shop (1 использование)
@pytest.mark.asyncio
@patch('app.modules.wb_adv_updater.data_manager._sm')
async def test_get_active_adv_ids_for_shop_basic(mock_sm):
    """Тест get_active_adv_ids_for_shop получение активных ID кампаний"""
    from app.modules.wb_adv_updater.data_manager import get_active_adv_ids_for_shop
    
    shop_id = "shop_123"
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    
    mock_result.unique.return_value = mock_scalars
    mock_scalars.scalars.return_value.all.return_value = [101, 102, 103]
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_sm.return_value = mock_session
    
    result = await get_active_adv_ids_for_shop(shop_id)
    
    assert len(result) == 3
    mock_session.execute.assert_called_once()