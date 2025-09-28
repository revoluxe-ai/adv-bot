"""DI-контейнеры приложения."""

__all__ = [
    "AppContainer",
    "inject",
    "Provide",
]

from .app_container import AppContainer
from dependency_injector.wiring import inject, Provide

__all__ = ("AppContainer", "inject", "Provide")
