"""Контейнер для DI-зависимостей приложения."""

__all__ = ("AppContainer",)
from dependency_injector import containers, providers
from neo4j import AsyncDriver

from ...configs import AppConfig
from . import databases


class AppContainer(containers.DeclarativeContainer):
    """Главный DI-контейнер приложения. Содержит все основные сервисы и конфигурации."""

    settings = providers.Singleton(AppConfig.create)

    # Синхронный провайдер драйвера, чтобы инъекции получали готовый объект
    neo4j_driver: providers.Singleton[AsyncDriver] = providers.Singleton(
        databases.create_neo4j_driver,
        neo4j_config=settings.provided.infrastructure.neo4j,
    )

    # Асинхронный ресурс для управления жизненным циклом драйвера
    _neo4j_lifecycle = providers.Resource(
        databases.Neo4jLifecycle,
        driver=neo4j_driver,
    )
    # Redis: синхронный клиент + приватный lifecycle-ресурс
    redis_client = providers.Singleton(
        databases.create_redis_client,
        redis_config=settings.provided.infrastructure.redis,
    )
    _redis_lifecycle = providers.Resource(
        databases._RedisLifecycle,
        client=redis_client,
    )
