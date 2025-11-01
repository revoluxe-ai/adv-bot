from __future__ import annotations

from dependency_injector import containers, providers

from app.core.redis_manager_v2.redis_client import RedisClient
from .wb_parser.rate_limit_manager import ParserRateLimitRedisManager


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


__all__ = ["WBKeywordsParserContainer"]


