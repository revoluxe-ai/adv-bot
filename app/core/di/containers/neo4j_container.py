"""Neo4j DI container module."""

__all__ = ["Neo4jContainer"]

from dependency_injector import containers, providers
from dependency_injector.providers import Dependency
from typing import Any

from ..databases import create_neo4j_driver, Neo4jLifecycle # type: ignore[attr-defined]


class Neo4jContainer(containers.DeclarativeContainer):
    """Контейнер для Neo4j зависимостей."""

    # Конфигурация приложения
    settings: Dependency[Any] = providers.Dependency()

    # Neo4j driver
    neo4j_driver = providers.Singleton(
        create_neo4j_driver,
        neo4j_config=settings.provided.infrastructure.neo4j,
    )

    # Neo4j lifecycle management
    _neo4j_lifecycle = providers.Resource(
        Neo4jLifecycle,
        driver=neo4j_driver,
    )
