from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock

import pytest
from dependency_injector import providers

from app.modules.wb_keywords_parser.wb_parser.excs import TooManyRequestsInParserError
from app.modules.wb_keywords_parser.wb_parser.parser import ParserService
from app.modules.wb_keywords_parser.wb_parser.proxy_manager import (
    ParserProxy,
    ProxyProxyManager,
)


class RateLimitManagerStub:
    def __init__(self) -> None:
        self.blocks: dict[str, float] = {}
        self.error_counts: defaultdict[str, int] = defaultdict(int)
        self.success_counts: defaultdict[str, int] = defaultdict(int)
        self.last_error_ts: defaultdict[str, float] = defaultdict(float)
        self.block_calls: list[tuple[str, float]] = []
        self.refresh_calls: list[tuple[str, float]] = []
        self.delete_calls: list[str] = []
        self._is_blocked_override: AsyncMock | None = None

    def set_is_blocked_override(self, func: AsyncMock | None) -> None:
        self._is_blocked_override = func

    async def is_ip_blocked(self, identity: str) -> tuple[bool, float]:
        if self._is_blocked_override is not None:
            return await self._is_blocked_override(identity)

        ttl = self.blocks.get(identity)
        if ttl is None:
            return False, 0.0
        if ttl <= 0:
            self.blocks.pop(identity, None)
            return False, 0.0

        # emulate TTL consumption on each check
        self.blocks[identity] = 0.0
        return True, ttl

    async def block_ip(self, identity: str, ttl: float) -> None:
        self.blocks[identity] = ttl
        self.block_calls.append((identity, ttl))

    async def delete_block(self, identity: str) -> None:
        self.blocks.pop(identity, None)
        self.delete_calls.append(identity)

    async def refresh_block(self, identity: str, ttl: float) -> None:
        self.blocks[identity] = ttl
        self.refresh_calls.append((identity, ttl))

    async def increment_error_counter(self, identity: str) -> int:
        self.error_counts[identity] += 1
        return self.error_counts[identity]

    async def increment_success_counter(self, identity: str) -> int:
        self.success_counts[identity] += 1
        return self.success_counts[identity]

    async def set_last_error_ts(self, identity: str) -> None:
        self.last_error_ts[identity] = 0.0

    async def get_last_error_ts(self, identity: str) -> float:
        return self.last_error_ts.get(identity, 0.0)


@pytest.fixture
def mock_rate_limit_manager() -> RateLimitManagerStub:
    return RateLimitManagerStub()


@pytest.fixture
def proxy_manager() -> ProxyProxyManager:
    return ProxyProxyManager(
        [
            ParserProxy(name="proxy-1", rate_limit_key="proxy-1"),
            ParserProxy(name="proxy-2", rate_limit_key="proxy-2"),
        ]
    )


@pytest.fixture
def parser_with_rate_limit(
    mock_rate_limit_manager: RateLimitManagerStub,
    proxy_manager: ProxyProxyManager,
) -> ParserService:
    return ParserService(
        rate_limit_manager=mock_rate_limit_manager,
        proxy_manager=proxy_manager,
        delay=0.01,
    )


@pytest.fixture
def parser_without_rate_limit() -> ParserService:
    return ParserService(rate_limit_manager=None)


@pytest.fixture
def aiohttp_mock_client(front_too_many_requests_str):
    aiohttp_client = AsyncMock()
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=front_too_many_requests_str)
    aiohttp_client.__aenter__.return_value = session_mock
    return aiohttp_client


@pytest.mark.asyncio
async def test_parser_blocks_identity_on_too_many_requests(
    di_container,
    parser_with_rate_limit: ParserService,
    mock_rate_limit_manager: RateLimitManagerStub,
    proxy_manager: ProxyProxyManager,
    aiohttp_mock_client,
):
    """Проверяем, что при TooManyRequests парсер блокирует идентификатор прокси."""

    di_container.module_resources.wb_keywords_parser.aiohttp_client.override(
        providers.Object(aiohttp_mock_client)
    )

    di_container.wire(modules=['app.modules.wb_keywords_parser.wb_parser.parser'])
    try:
        parser_with_rate_limit._parse_keywords_from_wb_impl = AsyncMock(
            side_effect=TooManyRequestsInParserError("429 Too Many Requests")
        )

        total_pages = MagicMock(total_pages=60)

        with pytest.raises(TooManyRequestsInParserError):
            await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

        assert len(mock_rate_limit_manager.block_calls) == 1
        identity, ttl = mock_rate_limit_manager.block_calls[0]
        assert identity == proxy_manager.proxies[0].rate_limit_key
        assert ttl > 0
        assert proxy_manager.proxies[0].cooldown_until > 0
    finally:
        di_container.module_resources.wb_keywords_parser.aiohttp_client.reset_override()


@pytest.mark.asyncio
async def test_parser_decreases_ttl_on_success(
    parser_with_rate_limit: ParserService,
    mock_rate_limit_manager: RateLimitManagerStub,
    proxy_manager: ProxyProxyManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """Если запрос успешный при активной блокировке — TTL должен уменьшаться или удаляться."""

    identity = proxy_manager.proxies[0].rate_limit_key
    mock_rate_limit_manager.blocks[identity] = 2.0

    sleep_mock = AsyncMock()
    monkeypatch.setattr("app.utils.rate_limit.asyncio.sleep", sleep_mock)

    parser_with_rate_limit._parse_keywords_from_wb_impl = AsyncMock(
        return_value=([], "cluster", 123, 0)
    )

    total_pages = MagicMock(total_pages=60)
    await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

    assert mock_rate_limit_manager.refresh_calls or mock_rate_limit_manager.delete_calls
    assert proxy_manager.proxies[0].consecutive_successes == 1


@pytest.mark.asyncio
async def test_parser_waits_when_identity_blocked(
    parser_with_rate_limit: ParserService,
    mock_rate_limit_manager: RateLimitManagerStub,
    monkeypatch: pytest.MonkeyPatch,
):
    """Если идентификатор в блоке — парсер ждёт и повторяет попытку."""

    call_count = 0

    async def side_effect(identity: str) -> tuple[bool, float]:
        nonlocal call_count
        call_count += 1
        return (True, 0.05) if call_count == 1 else (False, 0.0)

    mock_rate_limit_manager.set_is_blocked_override(AsyncMock(side_effect=side_effect))

    sleep_mock = AsyncMock()
    monkeypatch.setattr("app.utils.rate_limit.asyncio.sleep", sleep_mock)

    parser_with_rate_limit._parse_keywords_from_wb_impl = AsyncMock(
        return_value=([], "cluster", 123, 0)
    )

    total_pages = MagicMock(total_pages=60)
    await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

    assert call_count >= 2
    assert sleep_mock.await_count >= 1


@pytest.mark.asyncio
async def test_parser_works_without_rate_limit_manager(parser_without_rate_limit: ParserService):
    """Парсер должен корректно работать без rate_limit_manager."""

    parser_without_rate_limit._parse_keywords_from_wb_impl = AsyncMock(
        return_value=([], "cluster", 123, 0)
    )

    total_pages = MagicMock(total_pages=60)
    result = await parser_without_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)
    assert result == []


@pytest.mark.asyncio
async def test_exponential_backoff_on_repeated_errors(
    parser_with_rate_limit: ParserService,
    mock_rate_limit_manager: RateLimitManagerStub,
    monkeypatch: pytest.MonkeyPatch,
):
    """TTL должен увеличиваться при повторных ошибках (экспоненциальный бэкофф)."""

    async def side_effect(identity: str) -> tuple[bool, float]:
        ttl = mock_rate_limit_manager.blocks.get(identity)
        if ttl:
            mock_rate_limit_manager.blocks[identity] = 0.0
            return True, ttl
        return False, 0.0

    mock_rate_limit_manager.set_is_blocked_override(AsyncMock(side_effect=side_effect))

    sleep_mock = AsyncMock()
    monkeypatch.setattr("app.utils.rate_limit.asyncio.sleep", sleep_mock)

    parser_with_rate_limit._parse_keywords_from_wb_impl = AsyncMock(
        side_effect=TooManyRequestsInParserError("429")
    )

    total_pages = MagicMock(total_pages=60)

    with pytest.raises(TooManyRequestsInParserError):
        await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

    with pytest.raises(TooManyRequestsInParserError):
        await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

    assert len(mock_rate_limit_manager.block_calls) >= 2
    first_ttl = mock_rate_limit_manager.block_calls[0][1]
    second_ttl = mock_rate_limit_manager.block_calls[1][1]
    assert second_ttl > first_ttl


@pytest.mark.asyncio
async def test_parser_rotates_proxy_after_rate_limit(
    parser_with_rate_limit: ParserService,
    mock_rate_limit_manager: RateLimitManagerStub,
    proxy_manager: ProxyProxyManager,
    monkeypatch: pytest.MonkeyPatch,
):
    """При rate limit текущий прокси уходит в кулдаун, и выбирается следующий."""

    identity_order: list[str] = []

    async def is_blocked(identity: str) -> tuple[bool, float]:
        ttl = mock_rate_limit_manager.blocks.get(identity)
        if ttl:
            mock_rate_limit_manager.blocks[identity] = 0.0
            return True, ttl
        return False, 0.0

    mock_rate_limit_manager.set_is_blocked_override(AsyncMock(side_effect=is_blocked))

    sleep_mock = AsyncMock()
    monkeypatch.setattr("app.utils.rate_limit.asyncio.sleep", sleep_mock)

    async def side_effect(text: str, page: int, *, proxy: ParserProxy | None = None):
        assert proxy is not None
        identity_order.append(proxy.rate_limit_key)
        if len(identity_order) == 1:
            raise TooManyRequestsInParserError("429")
        return ([], "cluster", 123, 0)

    parser_with_rate_limit._parse_keywords_from_wb_impl = AsyncMock(side_effect=side_effect)

    total_pages = MagicMock(total_pages=60)

    with pytest.raises(TooManyRequestsInParserError):
        await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

    await parser_with_rate_limit.parse_keywords_from_wb("тест", 1, total_pages)

    assert identity_order[0] == proxy_manager.proxies[0].rate_limit_key
    assert identity_order[1] == proxy_manager.proxies[1].rate_limit_key
    assert proxy_manager.proxies[0].consecutive_failures >= 1
    assert proxy_manager.proxies[1].consecutive_successes == 1
