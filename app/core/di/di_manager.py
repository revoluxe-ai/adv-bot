import logging
from contextlib import AbstractAsyncContextManager
from typing import TypeVar, Generic, Any, Never
from collections.abc import Awaitable

from dependency_injector import providers, containers

T = TypeVar("T")

logger = logging.getLogger(__name__)


class DIManager(AbstractAsyncContextManager[T], Generic[T]):
    """
    Контекстный менеджер для DI-контейнера.
    Инкапсулирует bootstrap, wire всех модульных контейнеров и корректный shutdown.
    Запрещает прямую инициализацию через __init__.

    Предполагается структура:
      AppContainer -> module_resources (DeclarativeContainer) -> <module> (providers.Container(...))

    Инфраструктурные провайдеры (Singleton, Dependency, Resource) внутри module_resources игнорируются.
    """

    _container: T
    _wired: bool

    def __init__(self, *args: Any, **kwargs: Any) -> Never:
        raise RuntimeError("Используйте DIManager.create() для инициализации")

    @classmethod
    async def create(
        cls, container_cls: type[T], *args: Any, **kwargs: Any
    ) -> "DIManager[T]":
        self = object.__new__(cls)
        self._container = container_cls(*args, **kwargs)
        self._wired = False
        await self._bootstrap()
        return self

    async def _bootstrap(self) -> None:
        container = self._container
        # Инициализация ресурсов глобального контейнера
        init_result = getattr(container, "init_resources", lambda: None)()
        if isinstance(init_result, Awaitable):
            await init_result
        # Wiring root (если задан wiring_config на самом AppContainer)
        try:
            if isinstance(container, containers.DeclarativeContainer) and getattr(
                container, "wiring_config", None
            ):
                container.wire()  # безопасно вызывать повторно
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось выполнить wiring корневого контейнера")
        # Wiring модулей
        self._wire_module_containers()

    def _wire_module_containers(self) -> None:
        if self._wired:
            return
        container = self._container
        if not hasattr(container, "module_resources"):
            logger.debug(
                "module_resources не обнаружен в контейнере — пропуск модульного wiring"
            )
            self._wired = True
            return
        try:
            module_resources = container.module_resources() # pyright: ignore
        except Exception as e:  # noqa: BLE001
            logger.error(f"Не удалось получить module_resources: {e}")
            self._wired = True
            return
        # Перебор только providers.Container
        wired = []
        skipped = []
        for name, provider in getattr(module_resources, "providers", {}).items(): # pyright: ignore
            if isinstance(provider, providers.Container):
                try:
                    sub_container = provider()  # экземпляр DeclarativeContainer модуля # pyright: ignore
                    if hasattr(sub_container, "wiring_config") and getattr( # pyright: ignore
                        sub_container, "wiring_config" # pyright: ignore
                    ):
                        sub_container.wire() # pyright: ignore
                        wired.append(name) # pyright: ignore
                    else:
                        skipped.append(name) # pyright: ignore
                except Exception:  # noqa: BLE001
                    logger.exception(
                        f"Не удалось выполнить wiring под-контейнера '{name}'"
                    )
            else:
                # Инфраструктурный или dependency провайдер — пропускаем
                skipped.append(name) # pyright: ignore
        logger.debug(
            "Wiring модульных контейнеров завершён: wired=%s skipped=%s", wired, skipped # pyright: ignore
        )
        self._wired = True

    async def __aenter__(self) -> T:  # pragma: no cover
        return self._container

    async def __aexit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:  # pragma: no cover
        container = self._container
        shutdown_result = getattr(container, "shutdown_resources", lambda: None)()
        if isinstance(shutdown_result, Awaitable):
            await shutdown_result
