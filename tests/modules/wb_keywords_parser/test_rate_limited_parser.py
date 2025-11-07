
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dependency_injector import providers

from app.core.di import AppContainer
from app.modules.wb_keywords_parser.wb_parser.parser import ParserService
from app.modules.wb_keywords_parser.wb_parser.excs import TooManyRequestsInParserError


# ---------- FIXTURES ----------

@pytest.fixture
def mock_rate_limit_manager():
    manager = MagicMock()
    manager.is_ip_blocked = AsyncMock(return_value=(False, 0.0))
    manager.block_ip = AsyncMock()
    manager.delete_block = AsyncMock()
    manager.refresh_block = AsyncMock()
    return manager





@pytest.fixture
def parser_with_rate_limit(mock_rate_limit_manager):
    return ParserService(rate_limit_manager=mock_rate_limit_manager)


@pytest.fixture
def parser_without_rate_limit():
    return ParserService(rate_limit_manager=None)

TEST_IP = "203.0.113.1"

@pytest.fixture
def aiohttp_mock_client(front_too_many_requests_str):
    aiohttp_client = AsyncMock()
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=front_too_many_requests_str)
    aiohttp_client.__aenter__.return_value = session_mock
    return aiohttp_client





@pytest.mark.asyncio
async def test_parser_blocks_ip_on_too_many_requests(
    di_container,
    parser_with_rate_limit,
    mock_rate_limit_manager,
    aiohttp_mock_client,
):
    """Проверяем, что при TooManyRequests парсер блокирует IP."""

    # подменяем только то, что нужно конкретно в этом тесте
    di_container.module_resources.wb_keywords_parser.aiohttp_client.override(
        providers.Object(aiohttp_mock_client)
    )

    di_container.wire(modules=['app.modules.wb_keywords_parser.wb_parser.parser'])
    try:
        with patch("app.utils.net.get_public_ip", new_callable=AsyncMock, return_value=TEST_IP):
            parser_with_rate_limit._parse_keywords_from_wb_impl = AsyncMock(
                side_effect=TooManyRequestsInParserError("429 Too Many Requests")
            )

            total_pages = MagicMock(total_pages=60)

            # исключение должно пробиться из декоратора и parse_keywords_from_wb
            with pytest.raises(TooManyRequestsInParserError):
                await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

            # декоратор rate_limited_request должен вызвать block_ip
            mock_rate_limit_manager.block_ip.assert_called_once()
            ip, ttl = mock_rate_limit_manager.block_ip.call_args[0]
            assert ip == TEST_IP
            assert ttl >= 0.1
    finally:
        # сброс именно этого локального override
        di_container.module_resources.wb_keywords_parser.aiohttp_client.reset_override()

@pytest.mark.asyncio
@patch("app.utils.net.get_public_ip", new_callable=AsyncMock, return_value=TEST_IP)
async def test_parser_decreases_ttl_on_success(
    mock_get_ip, parser_with_rate_limit, mock_rate_limit_manager
):
    """Если запрос успешный при активной блокировке — TTL должен уменьшаться или удаляться."""
    mock_rate_limit_manager.is_ip_blocked.return_value = (True, 2.0)

    with patch.object(
        parser_with_rate_limit,
        "_parse_with_rate_limit",
        new_callable=AsyncMock,
        return_value=([], "cluster", 123, 0),
    ):
        total_pages = MagicMock(total_pages=60)
        await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

        assert (
            mock_rate_limit_manager.refresh_block.called
            or mock_rate_limit_manager.delete_block.called
        )


@pytest.mark.asyncio
@patch("app.utils.net.get_public_ip", new_callable=AsyncMock, return_value=TEST_IP)
async def test_parser_waits_when_ip_blocked(
    mock_get_ip, parser_with_rate_limit, mock_rate_limit_manager
):
    """Если IP заблокирован — парсер должен подождать и попробовать снова."""
    call_count = 0

    async def side_effect(*args):
        nonlocal call_count
        call_count += 1
        return (True, 0.1) if call_count == 1 else (False, 0.0)

    mock_rate_limit_manager.is_ip_blocked.side_effect = side_effect

    with patch.object(
        parser_with_rate_limit,
        "_parse_with_rate_limit",
        new_callable=AsyncMock,
        return_value=([], "cluster", 123, 0),
    ):
        total_pages = MagicMock(total_pages=60)
        await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

        assert mock_rate_limit_manager.is_ip_blocked.call_count >= 2


@pytest.mark.asyncio
async def test_parser_works_without_rate_limit_manager(parser_without_rate_limit):
    """Парсер должен корректно работать без rate_limit_manager."""
    with patch.object(
        parser_without_rate_limit,
        "_parse_keywords_from_wb_impl",
        new_callable=AsyncMock,
        return_value=([], "cluster", 123, 0),
    ):
        total_pages = MagicMock(total_pages=60)
        result = await parser_without_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)
        assert result == []


@pytest.mark.asyncio
@patch("app.utils.net.get_public_ip", new_callable=lambda: AsyncMock, return_value=TEST_IP)
async def test_exponential_backoff_on_repeated_errors(
    mock_get_ip, parser_with_rate_limit, mock_rate_limit_manager
):
    """TTL должен увеличиваться при повторных ошибках (экспоненциальный бэкофф)."""
    mock_rate_limit_manager.is_ip_blocked.side_effect = [(False, 0.0)] * 2

    with patch.object(
        parser_with_rate_limit,
        "_parse_with_rate_limit",
        new_callable=AsyncMock,
        side_effect=TooManyRequestsInParserError("429"),
    ):
        total_pages = MagicMock(total_pages=60)

        # Первая ошибка
        with pytest.raises(TooManyRequestsInParserError):
            await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

        first_ttl = mock_rate_limit_manager.block_ip.call_args_list[0][0][1]

        # Вторая ошибка (TTL должен вырасти)
        with pytest.raises(TooManyRequestsInParserError):
            await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

        second_ttl = mock_rate_limit_manager.block_ip.call_args_list[1][0][1]

        assert second_ttl > first_ttl
