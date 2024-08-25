import clickhouse_connect
from app.settings import settings
from multiprocessing import Value, Lock
import logging

# Настройка логгера
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Глобальные переменные для счётчика и блокировки
connection_count = Value('i', 0)  # Счётчик открытых соединений
connection_lock = Lock()  # Блокировка для синхронизации доступа к счётчику

host = settings.clickhouse_host
username = settings.clickhouse_user
password = settings.clickhouse_password
database = 'default_db'
max_connections = settings.CH_MAX_THREAD

class get_clickhouse_client:
    def __init__(self):
        self.client = None

    async def __aenter__(self):
        global connection_count
        global connection_lock

        with connection_lock:
            connection_count.value += 1
            logger.debug(f"Open connections count: {connection_count.value}")

        self.client = await clickhouse_connect.create_async_client(
            host=host,
            username=username,
            password=password,
            database=database
        )
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        global connection_count
        global connection_lock

        if self.client:
            self.client.close()

        with connection_lock:
            connection_count.value -= 1
            logger.debug(f"Open connections count: {connection_count.value}")