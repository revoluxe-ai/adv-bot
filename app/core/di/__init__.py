"""DI-контейнеры приложения."""

__all__ = [
    "AppContainer",
    "inject",
    "Provide",
    'DIManager',
]

from dependency_injector.wiring import inject, Provide

from .app_container import AppContainer
from .di_manager import DIManager
