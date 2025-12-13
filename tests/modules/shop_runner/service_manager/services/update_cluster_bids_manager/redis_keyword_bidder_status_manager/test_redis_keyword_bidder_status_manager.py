import pytest
from unittest.mock import MagicMock

from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager import RedisKeywordBidderStatusManager

from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import UpdateBidsCommand
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_command import \
    RedisCommand
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus


@pytest.fixture
def redis_client_wrapper(fake_redis: FakeRedis) -> RedisClient:
    """Фикстура для создания RedisClient wrapper над FakeRedis."""
    return RedisClient(redis_client=fake_redis)


@pytest.fixture
def redis_keyword_bidder_status_manager(redis_client_wrapper: RedisClient) -> RedisKeywordBidderStatusManager:
    """Фикстура для создания экземпляра RedisKKeywordBidderStatusManager."""
    return RedisKeywordBidderStatusManager(redis_client=redis_client_wrapper)


@pytest.fixture
def mock_redis_command() -> RedisCommand:
    """Мок для RedisCommand."""
    return RedisCommand(adv_id=1, text="test_keyword", bidder_keyword_status=BidderKeywordStatus.GOOD)


@pytest.fixture
def mock_update_bids_command() -> UpdateBidsCommand:
    """Мок для UpdateBidsCommand."""
    mock_new_bid = MagicMock()
    mock_new_bid.adv_id = 1
    mock_new_bid.nmid = 100
    mock_new_bid.cluster = "test_keyword"
    mock_new_bid.bidder_keyword_status = KeywordStatus.GOOD # Используем KeywordStatus, т.к. NewBid использует его

    mock_new_bid_bad = MagicMock()
    mock_new_bid_bad.adv_id = 1
    mock_new_bid_bad.nmid = 101
    mock_new_bid_bad.cluster = "bad_keyword"
    mock_new_bid_bad.bidder_keyword_status = KeywordStatus.BAD # Используем KeywordStatus

    mock_new_bid_none = MagicMock()
    mock_new_bid_none.adv_id = 1
    mock_new_bid_none.nmid = 102
    mock_new_bid_none.cluster = "none_keyword"
    mock_new_bid_none.bidder_keyword_status = None # Для проверки None

    return UpdateBidsCommand(new_bids=[mock_new_bid, mock_new_bid_bad, mock_new_bid_none])


@pytest.fixture
def mock_complex_adv() -> ComplexAdv:
    """Мок для ComplexAdv."""
    mock_adv_setting = MagicMock()
    mock_adv_setting.adv_id = 1
    mock_adv_setting.nmids = [100, 101]
    mock_complex_adv_obj = MagicMock(spec=ComplexAdv)
    mock_complex_adv_obj.adv_setting = mock_adv_setting
    mock_complex_adv_obj.adv_id = 1
    mock_complex_adv_obj.nmids = [100, 101] # Добавляем nmids
    return mock_complex_adv_obj


@pytest.fixture
def mock_calculated_keywords() -> list[CalculatedKeyword]:
    """Мок для списка CalculatedKeyword."""
    mock_kw1 = MagicMock(spec=CalculatedKeyword)
    mock_kw1.text = "test_keyword"

    mock_kw2 = MagicMock(spec=CalculatedKeyword)
    mock_kw2.text = "another_keyword"
    return [mock_kw1, mock_kw2]


class TestRedisKKeywordBidderStatusManager:
    @pytest.mark.asyncio
    async def test_get_key(self, redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager, mock_redis_command: RedisCommand):
        """Тест для метода _get_key - проверяет корректность генерации ключа."""
        expected_key = f"{redis_keyword_bidder_status_manager.prefix}-{mock_redis_command.adv_id}-{mock_redis_command.text}"
        key = redis_keyword_bidder_status_manager._get_key(mock_redis_command)
        assert key == expected_key

    @pytest.mark.asyncio
    async def test_get_key_different_values(self, redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager):
        """Тест для метода _get_key с различными входными значениями."""
        redis_command = RedisCommand(adv_id=999, text="another_key", bidder_keyword_status=BidderKeywordStatus.BAD)
        expected_key = f"{redis_keyword_bidder_status_manager.prefix}-{redis_command.adv_id}-{redis_command.text}"
        key = redis_keyword_bidder_status_manager._get_key(redis_command)
        assert key == expected_key

    @pytest.mark.asyncio
    async def test_update_statuses(self,
                                   redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager,
                                   mock_update_bids_command: UpdateBidsCommand,
                                   fake_redis: FakeRedis,
                                   monkeypatch):
        """Тест для метода update_statuses - проверяет успешное обновление статусов."""
        mock_convertor = MagicMock()
        mock_redis_commands = [
            RedisCommand(adv_id=1, text="test_keyword", bidder_keyword_status=BidderKeywordStatus.GOOD),
            RedisCommand(adv_id=1, text="bad_keyword", bidder_keyword_status=BidderKeywordStatus.BAD),
            RedisCommand(adv_id=1, text="none_keyword", bidder_keyword_status=None)
        ]
        mock_convertor.update_bids_command_to_redis_command.return_value = mock_redis_commands
        monkeypatch.setattr("app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_keyword_bidder_status_manager.convertor", mock_convertor)

        await redis_keyword_bidder_status_manager.update_statuses(mock_update_bids_command)

        assert await fake_redis.get(redis_keyword_bidder_status_manager._get_key(mock_redis_commands[0])) == BidderKeywordStatus.GOOD.value
        assert await fake_redis.get(redis_keyword_bidder_status_manager._get_key(mock_redis_commands[1])) == BidderKeywordStatus.BAD.value
        assert await fake_redis.get(redis_keyword_bidder_status_manager._get_key(mock_redis_commands[2])) is None # None статус не должен быть записан

    @pytest.mark.asyncio
    async def test_update_statuses_empty_commands(self,
                                                  redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager,
                                                  fake_redis: FakeRedis,
                                                  monkeypatch):
        """Тест для метода update_statuses с пустым списком команд."""
        mock_convertor = MagicMock()
        mock_convertor.update_bids_command_to_redis_command.return_value = []
        monkeypatch.setattr("app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_keyword_bidder_status_manager.convertor", mock_convertor)

        await redis_keyword_bidder_status_manager.update_statuses(MagicMock())

        assert await fake_redis.dbsize() == 0  # Redis должен быть пуст

    @pytest.mark.asyncio
    async def test_get_statuses(self,
                                redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager,
                                mock_complex_adv: ComplexAdv,
                                mock_calculated_keywords: list[CalculatedKeyword],
                                fake_redis: FakeRedis,
                                monkeypatch):
        """Тест для метода get_statuses - проверяет получение статусов и маппинг."""
        # Подготавливаем данные в Redis
        key1 = redis_keyword_bidder_status_manager._get_key(RedisCommand(adv_id=1, text="test_keyword", bidder_keyword_status=None))
        key2 = redis_keyword_bidder_status_manager._get_key(RedisCommand(adv_id=1, text="another_keyword", bidder_keyword_status=None))
        await fake_redis.set(key1, BidderKeywordStatus.GOOD.value)
        await fake_redis.set(key2, BidderKeywordStatus.BAD.value)

        mock_convertor = MagicMock()
        mock_redis_commands = [
            RedisCommand(adv_id=1, text="test_keyword", bidder_keyword_status=None),
            RedisCommand(adv_id=1, text="another_keyword", bidder_keyword_status=None)
        ]
        mock_convertor.dto_to_redis_commands.return_value = mock_redis_commands
        monkeypatch.setattr("app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_keyword_bidder_status_manager.convertor", mock_convertor)

        texts = [kw.text for kw in mock_calculated_keywords]
        statuses_map = await redis_keyword_bidder_status_manager.get_statuses(mock_complex_adv, texts)

        assert statuses_map["test_keyword"] == BidderKeywordStatus.GOOD
        assert statuses_map["another_keyword"] == BidderKeywordStatus.BAD

    @pytest.mark.asyncio
    async def test_get_statuses_empty_results(self,
                                              redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager,
                                              mock_complex_adv: ComplexAdv,
                                              mock_calculated_keywords: list[CalculatedKeyword],
                                              fake_redis: FakeRedis,
                                              monkeypatch):
        """Тест для метода get_statuses с отсутствующими ключами в Redis - должен возвращать GOOD."""
        mock_convertor = MagicMock()
        mock_redis_commands = [
            RedisCommand(adv_id=1, text="non_existent_keyword", bidder_keyword_status=None)
        ]
        mock_convertor.dto_to_redis_commands.return_value = mock_redis_commands
        monkeypatch.setattr("app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_keyword_bidder_status_manager.convertor", mock_convertor)

        # Убедимся, что Redis пуст
        await fake_redis.flushall()

        # Мокаем calculated_keywords, чтобы он соответствовал non_existent_keyword
        mock_kw = MagicMock(spec=CalculatedKeyword)
        mock_kw.text = "non_existent_keyword"
        mock_calculated_keywords = [mock_kw]

        texts = [kw.text for kw in mock_calculated_keywords]
        statuses_map = await redis_keyword_bidder_status_manager.get_statuses(mock_complex_adv, texts)

        assert statuses_map["non_existent_keyword"] == BidderKeywordStatus.GOOD

    @pytest.mark.asyncio
    async def test_get_statuses_with_mixed_results(self,
                                                   redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager,
                                                   mock_complex_adv: ComplexAdv,
                                                   fake_redis: FakeRedis,
                                                   monkeypatch):
        """Тест для get_statuses со смешанными результатами (существующие и отсутствующие ключи)."""
        key_existing = redis_keyword_bidder_status_manager._get_key(RedisCommand(adv_id=1, text="existing_keyword", bidder_keyword_status=None))
        key_non_existing = redis_keyword_bidder_status_manager._get_key(RedisCommand(adv_id=1, text="non_existing_keyword", bidder_keyword_status=None))

        await fake_redis.set(key_existing, BidderKeywordStatus.BAD.value)

        mock_convertor = MagicMock()
        mock_redis_commands = [
            RedisCommand(adv_id=1, text="existing_keyword", bidder_keyword_status=None),
            RedisCommand(adv_id=1, text="non_existing_keyword", bidder_keyword_status=None)
        ]
        mock_convertor.dto_to_redis_commands.return_value = mock_redis_commands
        monkeypatch.setattr("app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_keyword_bidder_status_manager.convertor", mock_convertor)

        mock_kw_existing = MagicMock(spec=CalculatedKeyword)
        mock_kw_existing.text = "existing_keyword"
        mock_kw_non_existing = MagicMock(spec=CalculatedKeyword)
        mock_kw_non_existing.text = "non_existing_keyword"
        mock_calculated_keywords = [mock_kw_existing, mock_kw_non_existing]

        texts = [kw.text for kw in mock_calculated_keywords]
        statuses_map = await redis_keyword_bidder_status_manager.get_statuses(mock_complex_adv, texts)

        assert statuses_map["existing_keyword"] == BidderKeywordStatus.BAD
        assert statuses_map["non_existing_keyword"] == BidderKeywordStatus.GOOD

    @pytest.mark.asyncio
    async def test_full_cycle_update_and_get(self,
                                             redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager,
                                             mock_update_bids_command: UpdateBidsCommand,
                                             mock_complex_adv: ComplexAdv,
                                             mock_calculated_keywords: list[CalculatedKeyword],
                                             fake_redis: FakeRedis,
                                             monkeypatch):
        """Интеграционный тест: полный цикл обновления и получения статусов."""

        # Mock конвертеры
        mock_convertor = MagicMock()
        mock_redis_commands_for_update = [
            RedisCommand(adv_id=1, text="test_keyword", bidder_keyword_status=BidderKeywordStatus.GOOD),
            RedisCommand(adv_id=1, text="bad_keyword", bidder_keyword_status=BidderKeywordStatus.BAD),
            RedisCommand(adv_id=1, text="none_keyword", bidder_keyword_status=None)
        ]
        mock_convertor.update_bids_command_to_redis_command.return_value = mock_redis_commands_for_update
        mock_convertor.dto_to_redis_commands.return_value = [
            RedisCommand(adv_id=1, text="test_keyword", bidder_keyword_status=None),
            RedisCommand(adv_id=1, text="bad_keyword", bidder_keyword_status=None),
            RedisCommand(adv_id=1, text="none_keyword", bidder_keyword_status=None)
        ]
        monkeypatch.setattr("app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_keyword_bidder_status_manager.convertor", mock_convertor)

        # Обновляем статусы
        await redis_keyword_bidder_status_manager.update_statuses(mock_update_bids_command)

        # Проверяем, что статусы записаны корректно
        assert await fake_redis.get(redis_keyword_bidder_status_manager._get_key(mock_redis_commands_for_update[0])) == BidderKeywordStatus.GOOD.value
        assert await fake_redis.get(redis_keyword_bidder_status_manager._get_key(mock_redis_commands_for_update[1])) == BidderKeywordStatus.BAD.value
        assert await fake_redis.get(redis_keyword_bidder_status_manager._get_key(mock_redis_commands_for_update[2])) is None

        # Теперь получаем статусы
        # Подготавливаем mock_calculated_keywords, чтобы они соответствовали ожидаемым ключам
        mock_kw1 = MagicMock(spec=CalculatedKeyword)
        mock_kw1.text = "test_keyword"
        mock_kw2 = MagicMock(spec=CalculatedKeyword)
        mock_kw2.text = "bad_keyword"
        mock_kw3 = MagicMock(spec=CalculatedKeyword)
        mock_kw3.text = "none_keyword"
        mock_calculated_keywords_for_get = [mock_kw1, mock_kw2, mock_kw3]

        texts_for_get = [kw.text for kw in mock_calculated_keywords_for_get]
        statuses_map = await redis_keyword_bidder_status_manager.get_statuses(mock_complex_adv, texts_for_get)

        assert statuses_map["test_keyword"] == BidderKeywordStatus.GOOD
        assert statuses_map["bad_keyword"] == BidderKeywordStatus.BAD
        assert statuses_map["none_keyword"] == BidderKeywordStatus.GOOD # None в Redis означает дефолтное GOOD

    @pytest.mark.asyncio
    async def test_update_statuses_with_ttl(self,
                                            redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager,
                                            fake_redis: FakeRedis,
                                            monkeypatch):
        """Тест для update_statuses - проверка установки TTL."""
        # Временная установка очень маленького TTL для проверки
        redis_keyword_bidder_status_manager.default_ttl = 1
        
        mock_convertor = MagicMock()
        mock_redis_command = RedisCommand(adv_id=1, text="ttl_keyword", bidder_keyword_status=BidderKeywordStatus.GOOD)
        mock_convertor.update_bids_command_to_redis_command.return_value = [mock_redis_command]
        monkeypatch.setattr("app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_keyword_bidder_status_manager.convertor", mock_convertor)

        await redis_keyword_bidder_status_manager.update_statuses(MagicMock())

        key = redis_keyword_bidder_status_manager._get_key(mock_redis_command)
        # Проверяем, что ключ был установлен
        assert await fake_redis.get(key) == BidderKeywordStatus.GOOD.value
        # Проверяем, что TTL установлен и находится в ожидаемом диапазоне (например, <= 10 секунд)
        assert 0 < await fake_redis.ttl(key) <= redis_keyword_bidder_status_manager.default_ttl

        # Восстанавливаем оригинальный TTL
        redis_keyword_bidder_status_manager.default_ttl = 60 * 60 * 12

    @pytest.mark.asyncio
    async def test_get_statuses_invalid_enum_value(self,
                                                   redis_keyword_bidder_status_manager: RedisKeywordBidderStatusManager,
                                                   mock_complex_adv: ComplexAdv,
                                                   fake_redis: FakeRedis,
                                                   monkeypatch):
        """Тест для get_statuses с некорректным значением enum в Redis - должен возвращать GOOD."""
        key = redis_keyword_bidder_status_manager._get_key(RedisCommand(adv_id=1, text="invalid_enum", bidder_keyword_status=None))
        await fake_redis.set(key, "INVALID_STATUS") # Устанавливаем некорректное значение

        mock_convertor = MagicMock()
        mock_redis_commands = [
            RedisCommand(adv_id=1, text="invalid_enum", bidder_keyword_status=None)
        ]
        mock_convertor.dto_to_redis_commands.return_value = mock_redis_commands
        monkeypatch.setattr("app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_keyword_bidder_status_manager.convertor", mock_convertor)

        mock_kw = MagicMock(spec=CalculatedKeyword)
        mock_kw.text = "invalid_enum"
        mock_calculated_keywords = [mock_kw]

        texts = [kw.text for kw in mock_calculated_keywords]
        statuses_map = await redis_keyword_bidder_status_manager.get_statuses(mock_complex_adv, texts)
        assert statuses_map["invalid_enum"] == BidderKeywordStatus.GOOD # Ожидаем дефолтное GOOD при некорректном значении
