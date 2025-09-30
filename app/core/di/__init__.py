"""DI-контейнеры приложения."""

from .app_container import AppContainer
from .inject_preserve.inject import inject, Provide

__all__ = ("AppContainer", "inject", "Provide")
