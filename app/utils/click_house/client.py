import clickhouse_connect
from app.settings import settings
from multiprocessing import Value, Lock, Manager
import logging
import inspect
from urllib3 import PoolManager
import platform


system_name = platform.system()




pool_mgr = PoolManager(num_pools=10, maxsize=20)  # Пример настройки пула соединений


logger = logging.getLogger(__name__)


if system_name == 'Linux':

    # Используем Manager для создания разделяемых между процессами словарей
    manager = Manager()
    function_connection_count = manager.dict()  # Словарь для отслеживания соединений по функциям
    caller_function_connection_count = manager.dict()  # Словарь для отслеживания соединений по вызывающим функциям
    grand_caller_function_connection_count = manager.dict()  # Словарь для отслеживания соединений по функциям 3-го уровня

    # Глобальные переменные для счётчика и блокировок
    connection_count = Value('i', 0)  # Счётчик открытых соединений
    connection_lock = Lock()  # Блокировка для синхронизации доступа к общему счётчику
    function_count_lock = Lock()  # Блокировка для синхронизации доступа к словарям

host = settings.clickhouse_host
username = settings.clickhouse_user
password = settings.clickhouse_password
database = 'default_db'
max_connections = settings.CH_MAX_THREAD


class get_clickhouse_client:
    def __init__(self):
        self.client = None
        self.func_name = None
        self.caller_func_name = None
        self.grand_caller_func_name = None

    async def __aenter__(self):
        global connection_count
        global connection_lock
        global function_connection_count
        global caller_function_connection_count
        global grand_caller_function_connection_count
        global function_count_lock
        if system_name == 'Linux':
            # Извлекаем имя текущей функции, её вызывающей функции и функции, которая вызвала вызывающую функцию из стека вызовов
            stack = inspect.stack()
            self.func_name = stack[1].function  # Имя текущей функции
            self.caller_func_name = stack[2].function if len(stack) > 2 else None  # Имя вызывающей функции
            self.grand_caller_func_name = stack[3].function if len(stack) > 3 else None  # Имя функции 3-го уровня

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
                        f"Function '{self.func_name}' open connections count: {function_connection_count[self.func_name]}")

                # Вызывающая функция
                if self.caller_func_name:
                    if self.caller_func_name not in caller_function_connection_count:
                        caller_function_connection_count[self.caller_func_name] = 0
                    caller_function_connection_count[self.caller_func_name] += 1
                    logger.debug(
                        f"Caller function '{self.caller_func_name}' open connections count: {caller_function_connection_count[self.caller_func_name]}")

                # Функция 3-го уровня
                if self.grand_caller_func_name:
                    if self.grand_caller_func_name not in grand_caller_function_connection_count:
                        grand_caller_function_connection_count[self.grand_caller_func_name] = 0
                    grand_caller_function_connection_count[self.grand_caller_func_name] += 1
                    logger.debug(
                        f"Grand caller function '{self.grand_caller_func_name}' open connections count: {grand_caller_function_connection_count[self.grand_caller_func_name]}")

        self.client = await clickhouse_connect.create_async_client(
            host=host,
            username=username,
            password=password,
            database=database,
            pool_mgr=pool_mgr,
            port=settings.CLICKHOUSE_PORT,

        )
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if system_name == 'Linux':
            global connection_count
            global connection_lock
            global function_connection_count
            global caller_function_connection_count
            global grand_caller_function_connection_count
            global function_count_lock

        if self.client is not None:
            self.client.close()

        if system_name == 'Linux':
            with connection_lock:
                connection_count.value -= 1
                logger.debug(f"Total open connections count: {connection_count.value}")

            # Уменьшаем количество соединений для текущей и вызывающих функций
            with function_count_lock:
                # Текущая функция
                if self.func_name in function_connection_count:
                    function_connection_count[self.func_name] -= 1
                    logger.debug(
                        f"Function '{self.func_name}' open connections count: {function_connection_count[self.func_name]}")

                # Вызывающая функция
                if self.caller_func_name in caller_function_connection_count:
                    caller_function_connection_count[self.caller_func_name] -= 1
                    logger.debug(
                        f"Caller function '{self.caller_func_name}' open connections count: {caller_function_connection_count[self.caller_func_name]}")

                # Функция 3-го уровня
                if self.grand_caller_func_name in grand_caller_function_connection_count:
                    grand_caller_function_connection_count[self.grand_caller_func_name] -= 1
                    logger.debug(
                        f"Grand caller function '{self.grand_caller_func_name}' open connections count: {grand_caller_function_connection_count[self.grand_caller_func_name]}")


def track_connections(func):
    async def wrapper(*args, **kwargs):
        async with get_clickhouse_client() as client:
            return await func(client, *args, **kwargs)

    return wrapper


# Пример использования декоратора
@track_connections
async def query_data(client, query):
    result = await client.query(query)
    return result
