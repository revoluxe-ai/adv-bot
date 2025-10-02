"""DI-контейнеры приложения."""

__all__ = [
    "AppContainer",
    "inject",
    "Provide",
]

from dependency_injector.wiring import Provide

from .app_container import AppContainer
from .inject_preserve import inject
