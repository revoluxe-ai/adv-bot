import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.shop_runner.bidder.bidder_func import run_bidder_process_for_adv
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.api import AdvertApi
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.shop_runner.bidder.excs import CpmNotFoundError
import asyncio
import json

@pytest.fixture
async def mock_db_session():
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    mock_session.get = AsyncMock()
    mock_session.commit = AsyncMock()
    with patch('app.modules.shop_runner.bidder.bidder_func.sm', return_value=mock_session):
        yield mock_session

@pytest.fixture
def mock_adv_setting():
    mock = MagicMock()
    return mock

@pytest.fixture
def mock_wb_api():
    mock = MagicMock(spec=AdvertApi)
    mock.update_cpm = AsyncMock()
    mock.set_search_cpm = AsyncMock()
    mock.wb_cabinet = MagicMock()
    mock.wb_cabinet.id = 1
    mock.get_advs = AsyncMock(return_value=[MagicMock(cpm=200)])
    return mock

@pytest.fixture
def mock_calculated_keyword():
    mock = MagicMock(spec=CalculatedKeyword)
    mock.text = "test_keyword"
    mock.keyword_setting = MagicMock()
    mock.keyword_setting.hard_status = 2
    mock.real_position = 3
    return mock

@pytest.fixture
def mock_clickhouse():
    return AsyncMock()

@pytest.fixture
def mock_redis_clients():
    mock_replica = AsyncMock()
    mock_master = AsyncMock()
    return mock_replica, mock_master

@pytest.mark.asyncio
async def test_successful_bidder_process(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=200)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(return_value=MagicMock(promo_position=3))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_called_once_with(12345, 190)  # 200 - 10

@pytest.mark.asyncio
async def test_cpm_not_found(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=None)

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       wb_db_manager=mock_wb_db_manager):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_not_called()

@pytest.mark.asyncio
async def test_no_white_keywords(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[])

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       wb_db_manager=mock_wb_db_manager):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_not_called()

@pytest.mark.asyncio
async def test_position_above_max(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=200)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(return_value=MagicMock(promo_position=7))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_called_once_with(12345, 210)  # 200 + 10

@pytest.mark.asyncio
async def test_cpm_reaches_max(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=995)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(return_value=MagicMock(promo_position=7))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    # Mock get_cpms_from_wb
    mock_get_cpms = AsyncMock(return_value={995})

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager,
                       get_cpms_from_wb=mock_get_cpms):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_called_once_with(12345, 1000)  # 995 + 10 = 1005, ограничено до 1000
        mock_wb_api.set_search_cpm.assert_called_once_with("test_search_adv_id", 1000)  # Для поиска используется та же ставка, что и для авто

@pytest.mark.asyncio
async def test_cpm_below_minimum(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=120)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(return_value=MagicMock(promo_position=3))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    # Mock get_cpms_from_wb
    mock_get_cpms = AsyncMock(return_value={120})

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager,
                       get_cpms_from_wb=mock_get_cpms):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_called_once_with(12345, 125)  # 120 - 10 = 110, ограничено до 125
        mock_wb_api.set_search_cpm.assert_called_once_with("test_search_adv_id", 150)  # Для поиска минимум 150

@pytest.mark.asyncio
async def test_position_equals_max(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    """Test that when position equals max_place, we decrease the bid by bidder_step to optimize costs
    while maintaining the position. This helps find the optimal balance between position and cost."""
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=200)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(return_value=MagicMock(promo_position=5))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_called_once_with(12345, 190)  # 200 - 10 to optimize cost while maintaining position

@pytest.mark.asyncio
async def test_no_search_adv_id(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = None

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=200)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(return_value=MagicMock(promo_position=3))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_called_once_with(12345, 190)  # 200 - 10

@pytest.mark.asyncio
async def test_parser_error(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    """Test that when a parser error occurs, we handle it gracefully and don't update CPM."""
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=200)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(side_effect=Exception("Parser error"))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager):
        # Execute and verify that no exception is raised
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify that update_cpm was not called
        mock_wb_api.update_cpm.assert_not_called() 

@pytest.mark.asyncio
async def test_cpm_between_minimums(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    """Тест, когда CPM находится между минимальными значениями (125-150)"""
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=130)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(return_value=MagicMock(promo_position=3))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    # Mock get_cpms_from_wb
    mock_get_cpms = AsyncMock(return_value={130})

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager,
                       get_cpms_from_wb=mock_get_cpms):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_called_once_with(12345, 125)  # 130 - 10 = 120, ограничено до 125
        mock_wb_api.set_search_cpm.assert_called_once_with("test_search_adv_id", 150)  # 120 < 150, устанавливаем минимум

@pytest.mark.asyncio
async def test_cpm_near_maximum(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    """Тест, когда CPM близок к максимальному значению"""
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=990)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(return_value=MagicMock(promo_position=7))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    # Mock get_cpms_from_wb
    mock_get_cpms = AsyncMock(return_value={990})

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager,
                       get_cpms_from_wb=mock_get_cpms):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_called_once_with(12345, 1000)  # 990 + 10 = 1000, ограничено до 1000
        mock_wb_api.set_search_cpm.assert_called_once_with("test_search_adv_id", 1000)  # 1000 > 150, оставляем 1000

@pytest.mark.asyncio
async def test_cpm_at_minimums(mock_adv_setting, mock_wb_api, mock_calculated_keyword, mock_clickhouse, mock_redis_clients, mock_db_session):
    """Тест, когда CPM равен минимальным значениям"""
    # Setup
    shop_id = "test_shop"
    mock_adv_setting.adv_id = 12345
    mock_adv_setting.nmids = [123456]
    mock_adv_setting.bidder_step = 10
    mock_adv_setting.max_place = 5
    mock_adv_setting.reset_place = False
    mock_adv_setting.bidder_for_auto = True
    mock_adv_setting.search_adv_id = "test_search_adv_id"

    # Mock data_manager responses
    mock_data_manager = MagicMock()
    mock_data_manager.get_max_adv_bid = AsyncMock(return_value=1000)
    mock_data_manager.get_good_bad_phrases = AsyncMock(return_value=[mock_calculated_keyword])
    mock_data_manager.get_best_keyword = MagicMock(return_value=mock_calculated_keyword)
    mock_data_manager.get_cpm = AsyncMock(return_value=125)

    # Mock redis_manager responses
    mock_redis = MagicMock()
    mock_redis.get_keyword_position = AsyncMock(return_value=MagicMock(promo_position=3))
    mock_redis.set_last_adv_bid = AsyncMock()

    # Mock parser
    mock_parser = MagicMock()
    mock_parser.add_wb_positions = AsyncMock()

    # Mock wb_db_manager
    mock_wb_db_manager = MagicMock()
    mock_wb_db_manager.update_advs_in_db = AsyncMock()

    # Mock get_cpms_from_wb
    mock_get_cpms = AsyncMock(return_value={125})

    with patch.multiple('app.modules.shop_runner.bidder.bidder_func',
                       data_manager=mock_data_manager,
                       redis_manager=mock_redis,
                       parser=mock_parser,
                       wb_db_manager=mock_wb_db_manager,
                       get_cpms_from_wb=mock_get_cpms):
        # Execute
        await run_bidder_process_for_adv(mock_adv_setting, mock_wb_api, shop_id)

        # Verify
        mock_wb_api.update_cpm.assert_called_once_with(12345, 125)  # 125 - 10 = 115, ограничено до 125
        mock_wb_api.set_search_cpm.assert_called_once_with("test_search_adv_id", 150)  # 125 < 150, устанавливаем минимум 