from __future__ import annotations

import datetime as dt
from contextlib import asynccontextmanager

from dependency_injector import containers, providers

from app.core.redis_manager_v2.redis_client import RedisClient
from app.settings import settings
from .proxy_manager import ParserProxyManager, ParserProxyRepository
from .wb_parser.rate_limit_manager import ParserRateLimitRedisManager
from .wb_parser.parser import ParserService
import aiohttp

@asynccontextmanager
async def init_aiohttp_client():
    session = aiohttp.ClientSession()
    try:
        yield session
    finally:
        await session.close()


def create_parser_proxy_manager(
    repository: ParserProxyRepository | None,
) -> ParserProxyManager | None:
    if repository is None:
        return None

    return ParserProxyManager(
        repository=repository,
        failure_cooldown=dt.timedelta(
            seconds=settings.WB_PARSER_PROXY_FAILURE_COOLDOWN_SEC
        ),
        rate_limit_cooldown=dt.timedelta(
            seconds=settings.WB_PARSER_PROXY_RATE_LIMIT_COOLDOWN_SEC
        ),
    )


class WBKeywordsParserContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.modules.wb_keywords_parser.wb_parser.parser",
        ]
    )

    redis_client_wrapper = providers.Dependency(instance_of=RedisClient)

    rate_limit_manager = providers.Singleton(
        ParserRateLimitRedisManager,
        redis_client=redis_client_wrapper,
    )

    parser_proxy_repository: providers.Provider[ParserProxyRepository | None] = (
        providers.Object(None)
    )

    parser_proxy_manager = providers.Singleton(
        create_parser_proxy_manager,
        repository=parser_proxy_repository,
    )

    aiohttp_client = providers.Resource(
        init_aiohttp_client,
    )

    parser_service = providers.Singleton(
        ParserService,
        rate_limit_manager=rate_limit_manager,
        proxy_manager=parser_proxy_manager,
    )




__all__ = ["WBKeywordsParserContainer"]



