"""DI-контейнеры приложения."""

__all__ = [
    "AppContainer",
    "DIManager",
    "inject",
    "Provide",
]

from .app_container import AppContainer
from .di_manager import DIManager
from dependency_injector.wiring import inject, Provide
