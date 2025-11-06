from __future__ import annotations

from contextlib import asynccontextmanager

from dependency_injector import containers, providers

from app.core.redis_manager_v2.redis_client import RedisClient
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

    aiohttp_client = providers.Resource(
        init_aiohttp_client,
    )

    parser_service = providers.Singleton(
        ParserService,
        rate_limit_manager=rate_limit_manager,
    )




__all__ = ["WBKeywordsParserContainer"]



