__all__ = ["ConfigContainer"]


from dependency_injector import containers, providers

from app.configs import AppConfig


class ConfigContainer(containers.DeclarativeContainer):
    """Общий конфиг-контейнер для всех зависимостей.
    Содержит singleton AppSettings.
    """

    wiring_config = containers.WiringConfiguration(packages=["."])

    # Единый источник истины для всей конфигурации
    settings = providers.Singleton(AppConfig)
