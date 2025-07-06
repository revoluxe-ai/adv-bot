import inspect
import logging
import platform
from multiprocessing import Lock, Manager
from multiprocessing.synchronize import Lock as LockType
from typing import Optional, Any, cast, Callable, Protocol, TypeVar

import clickhouse_connect
from clickhouse_connect.driver.asyncclient import AsyncClient
from urllib3 import PoolManager

from app.settings import settings

system_name = platform.system()

pool_mgr = PoolManager(num_pools=10, maxsize=100)  # Пример настройки пула соединений

logger = logging.getLogger(__name__)


# Для типизации Value
class ValueProtocol(Protocol):
    value: int


# Объявляем глобальные переменные
manager = None
# Использование Any для обхода ошибки "Missing type parameters for generic type"
function_connection_count: Any = {}
caller_function_connection_count: Any = {}
grand_caller_function_connection_count: Any = {}
connection_count: Optional[ValueProtocol] = None
connection_lock: Optional[LockType] = None
function_count_lock: Optional[LockType] = None

if system_name == "Linux":
    # Используем Manager для создания разделяемых между процессами словарей
    manager = Manager()
    function_connection_count = (
        manager.dict()
    )  # Словарь для отслеживания соединений по функциям
    caller_function_connection_count = (
        manager.dict()
    )  # Словарь для отслеживания соединений по вызывающим функциям
    grand_caller_function_connection_count = (
        manager.dict()
    )  # Словарь для отслеживания соединений
    # по функциям 3-го уровня

    # Глобальные переменные для счётчика и блокировок
    connection_count = cast(
        ValueProtocol, manager.Value("i", 0)
    )  # Счётчик открытых соединений
    connection_lock = Lock()  # Блокировка для синхронизации доступа к общему счётчику
    function_count_lock = Lock()  # Блокировка для синхронизации доступа к словарям

host = settings.clickhouse_host
username = settings.clickhouse_user
password = settings.clickhouse_password
database = "default_db"
max_connections = settings.CH_MAX_THREAD


class get_clickhouse_client:
    def __init__(self) -> None:
        self.client: Optional[AsyncClient] = None
        self.func_name: Optional[str] = None
        self.caller_func_name: Optional[str] = None
        self.grand_caller_func_name: Optional[str] = None

    async def __aenter__(self) -> AsyncClient:
        global connection_count
        global connection_lock
        global function_connection_count
        global caller_function_connection_count
        global grand_caller_function_connection_count
        global function_count_lock

        if (
            system_name == "Linux"
            and connection_lock is not None
            and connection_count is not None
            and function_count_lock is not None
        ):
            # Извлекаем имя текущей функции, её вызывающей функции и функции,
            # которая вызвала вызывающую функцию из стека вызовов
            stack = inspect.stack()
            assert stack is not None
            self.func_name = stack[1].function  # Имя текущей функции
            self.caller_func_name = (
                stack[2].function if len(stack) > 2 else None
            )  # Имя вызывающей функции
            self.grand_caller_func_name = (
                stack[3].function if len(stack) > 3 else None
            )  # Имя функции 3-го уровня

            with connection_lock:
                connection_count.value += 1
                logger.debug(f"Total open connections count: {connection_count.value}")

            # Логгируем и обновляем счетчики для текущей и вызывающих функций
            with function_count_lock:
                # Текущая функция
                if self.func_name:
                    if self.func_name not in function_connection_count:
                        function_connection_count[self.func_name] = 0
                    function_connection_count[self.func_name] += 1
                    logger.debug(
                        f"Function '{self.func_name}' open connections count:"
                        f" {function_connection_count[self.func_name]}"
                    )

                # Вызывающая функция
                if self.caller_func_name:
                    if self.caller_func_name not in caller_function_connection_count:
                        caller_function_connection_count[self.caller_func_name] = 0
                    caller_function_connection_count[self.caller_func_name] += 1
                    logger.debug(
                        f"Caller function '{self.caller_func_name}' open connections "
                        f"count: {caller_function_connection_count[self.caller_func_name]}"
                    )

                # Функция 3-го уровня
                if self.grand_caller_func_name:
                    if (
                        self.grand_caller_func_name
                        not in grand_caller_function_connection_count
                    ):
                        grand_caller_function_connection_count[
                            self.grand_caller_func_name
                        ] = 0
                    grand_caller_function_connection_count[
                        self.grand_caller_func_name
                    ] += 1
                    logger.debug(
                        f"Grand caller function '{self.grand_caller_func_name}' open connections count:"
                        f" {grand_caller_function_connection_count[self.grand_caller_func_name]}"
                    )

        # Тип игнорируется, так как библиотека может не иметь типов
        self.client = await clickhouse_connect.create_async_client(  # type: ignore
            host=str(host or ""),
            username=str(username or ""),
            password=str(password or ""),
            database=database,
            pool_mgr=pool_mgr,
            port=settings.CLICKHOUSE_PORT,
        )
        return self.client

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        global connection_count
        global connection_lock
        global function_connection_count
        global caller_function_connection_count
        global grand_caller_function_connection_count
        global function_count_lock
        client: AsyncClient | None = self.client
        if client is not None:
            client.close()  # type: ignore

        if (
            system_name == "Linux"
            and connection_lock is not None
            and connection_count is not None
            and function_count_lock is not None
        ):
            with connection_lock:
                connection_count.value -= 1
                logger.debug(f"Total open connections count: {connection_count.value}")

            # Уменьшаем количество соединений для текущей и вызывающих функций
            with function_count_lock:
                # Текущая функция
                func_name = self.func_name
                if func_name is not None and func_name in function_connection_count:
                    function_connection_count[func_name] -= 1
                    logger.debug(
                        f"Function '{func_name}' open connections count: {function_connection_count[func_name]}"
                    )

                # Вызывающая функция
                caller_func_name = self.caller_func_name
                if (
                    caller_func_name is not None
                    and caller_func_name in caller_function_connection_count
                ):
                    caller_function_connection_count[caller_func_name] -= 1
                    logger.debug(
                        f"Caller function '{caller_func_name}'"
                        f" open connections count: {caller_function_connection_count[caller_func_name]}"
                    )

                # Функция 3-го уровня
                grand_caller_func_name = self.grand_caller_func_name
                if (
                    grand_caller_func_name is not None
                    and grand_caller_func_name in grand_caller_function_connection_count
                ):
                    grand_caller_function_connection_count[grand_caller_func_name] -= 1
                    logger.debug(
                        f"Grand caller function '{grand_caller_func_name}' "
                        f"open connections count: {grand_caller_function_connection_count[grand_caller_func_name]}"
                    )


F = TypeVar("F", bound=Callable[..., Any])


def track_connections(func: F) -> F:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with get_clickhouse_client() as client:
            return await func(client, *args, **kwargs)

    return cast(F, wrapper)


# Пример использования декоратора
@track_connections
async def query_data(client: AsyncClient, query: str) -> Any:
    result = await client.query(query)
    return result
