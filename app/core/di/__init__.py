"""DI-контейнеры приложения."""

__all__ = [
    "DIManager",
    "inject",
    "Provide",
]

from dependency_injector.wiring import inject, Provide
from .di_manager import DIManager
