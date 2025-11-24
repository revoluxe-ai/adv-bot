"""Модуль для работы с Neo4j через DI."""

__all__ = ("Neo4jLifecycle", "create_neo4j_driver")

from dependency_injector import resources
from neo4j import AsyncDriver, AsyncGraphDatabase

from app.configs.infrastructure_config.neo4j_config import Neo4jConfig


def create_neo4j_driver(neo4j_config: Neo4jConfig) -> AsyncDriver:
    """Синхронное создание AsyncDriver. Возвращает готовый объект драйвера.
    Жизненный цикл (verify_connectivity / close) обрабатывается отдельно
    в Neo4jLifecycle, чтобы инъекции всегда получали готовый объект,
    а ресурсы инициализировались асинхронно через контейнер.
    """
    driver = AsyncGraphDatabase.driver(
        f"{neo4j_config.uri}:{neo4j_config.port}",
        auth=(
            neo4j_config.name,
            neo4j_config.password,
        ),
    )
    return driver


class Neo4jLifecycle(resources.AsyncResource[None]):
    """AsyncResource только для управления жизненным циклом уже созданного драйвера.
    Позволяет оставлять инъекции синхронными (Singleton driver),
    а проверку подключения и закрытие выполнять при init_resources/shutdown_resources.
    """

    async def init(self, driver: AsyncDriver) -> None:
        """Инициализирует ресурс.
        TODO: LEGACY: проверка подключения к Neo4j отключена, так как раннеры без Neo4j падали.
        Вернуть verify_connectivity() или сделать проверку условной по флагу конфигурации.
        """
        # Провайдер передаёт driver как аргумент
        # await driver.verify_connectivity()

    async def shutdown(
        self, driver: AsyncDriver | None = None
    ) -> None:  # pyright: ignore
        """Завершает работу ресурса, закрывая подключение к Neo4j."""
        if driver:
            await driver.close()
