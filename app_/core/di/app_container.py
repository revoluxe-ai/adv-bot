"""Контейнер для DI-зависимостей приложения."""

__all__ = ("AppContainer",)


import httpx
from dependency_injector import containers, providers
from neo4j import AsyncDriver

from . import databases
from .http_sessions.wb_api_httpx_session import (
    create_httpx_session,
    ApiHttpxSessionLifecycle,
)
from ...configs import AppConfig


class AppContainer(containers.DeclarativeContainer):
    """Главный DI-контейнер приложения. Содержит все основные сервисы и конфигурации."""

    settings = providers.Singleton(AppConfig.create)

    # Neo4j
    neo4j_driver: providers.Singleton[AsyncDriver] = providers.Singleton(
        databases.create_neo4j_driver,
        neo4j_config=settings.provided.infrastructure.neo4j,
    )

    _neo4j_lifecycle = providers.Resource(
        databases.Neo4jLifecycle,
        driver=neo4j_driver,
    )

    # Redis
    redis_client = providers.Singleton(
        databases.create_redis_client,
        redis_config=settings.provided.infrastructure.redis,
    )
    _redis_lifecycle = providers.Resource(
        databases._RedisLifecycle,
        client=redis_client,
    )

    # WB API HTTP Session
    wb_api_httpx_session: providers.Singleton[httpx.AsyncClient] = providers.Singleton(
        create_httpx_session
    )

    _wb_api_httpx_session_lifecycle = providers.Resource(
        ApiHttpxSessionLifecycle,
        session=wb_api_httpx_session,
    )
