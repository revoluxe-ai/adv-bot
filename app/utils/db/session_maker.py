import logging
import threading
import asyncio
import traceback
from contextlib import asynccontextmanager
from time import time
import ssl
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.settings import settings
from python_modules import path_setting_funcs

logger = logging.getLogger(__name__)

lock_counter = threading.Lock()
conn_counter = 0

pool_size = 50
max_overflow = 100

#
# ssl_context = ssl.create_default_context(cafile=RDS_CERT_PATH)
# ssl_context.verify_mode = ssl.CERT_REQUIRED





class AnalyticAsyncSession(AsyncSession):
    async def execute(self, statement, *args, **kwargs):
        query_start = time()
        try:
            # Определяем тип операции
            operation_type = type(statement).__name__

            # Анализ стека для поиска вызывающего кода
            stack = traceback.extract_stack()
            caller = next((frame for frame in reversed(stack[:-1])
                           if 'sqlalchemy' not in frame.filename), None)

            result = await super().execute(statement, *args, **kwargs)
            duration = time() - query_start

            if duration > 1.0:
                logger.warning(
                    f"Slow query ({duration:.2f}s)\n"
                    f"Type: {operation_type}\n"
                    f"Location: {caller.filename}:{caller.lineno}\n"
                    f"Statement: {statement}"
                )
            return result
        except Exception as e:
            logger.error(f"Query error: {e}")
            raise



count_sem = settings.COUNT_SEMAPHORE_TO_POSTGRES
global_semaphore = asyncio.Semaphore(count_sem)

# def log_checkout(dbapi_con, con_record, con_proxy):
#     logger.debug("Соединение взято из пула")
#     global conn_counter
#     with lock_counter:
#         conn_counter += 1
#     logger.debug(f"Количество соединений: {conn_counter}")
#
# def log_checkin(dbapi_con, con_record):
#     logger.debug("Соединение возвращено в пул")
#     global conn_counter
#     with lock_counter:
#         conn_counter -= 1
#     logger.debug(f"Количество соединений: {conn_counter}")


def get_alchemy_row(read_only):
    port = settings.postgres_port
    file_path = path_setting_funcs.get_setting_path()
    postgres_dbname = settings.postgres_dbname
    # postgres_host = path_setting_funcs.get_document_by_key_name(file_path, 'postgres-host')
    postgres_password = settings.postgres_password
    postgres_user = settings.postgres_user
    if not read_only:
        host = settings.postgres_master_host
    else:
        host = settings.postgres_replica_host

    # Для asyncpg используем ssl вместо sslmode

    ssl_mode = settings.ssl_mode

    target_session = 'read-write' if not read_only else 'any'

    row_connector = f'postgresql://{postgres_user}:{postgres_password}@{host}:{port}/{postgres_dbname}'
    # if ssl_mode:
    #     row_connector += f'?sslmode={ssl_mode}'
    # row_connector += f'&target_session_attrs={target_session}'



    db_connector = (
        row_connector
    )
    return db_connector



def get_alchemy_row_for_migration(read_only):
    port = settings.postgres_port
    postgres_dbname = settings.postgres_dbname
    postgres_password = settings.postgres_password
    postgres_user = settings.postgres_user
    host = settings.postgres_master_host
    # Для asyncpg используем ssl вместо sslmode

    target_session = 'read-write' if not read_only else 'any'
    db_connector = (
        f'postgresql://{postgres_user}:{postgres_password}@{host}:{port}/{postgres_dbname}'
    )
    return db_connector


read_only_db_connector = get_alchemy_row(read_only=True).replace("postgresql://", "postgresql+asyncpg://")
read_write_db_connector = get_alchemy_row(read_only=False).replace("postgresql://", "postgresql+asyncpg://")

read_only_engine = create_async_engine(
    read_only_db_connector,
    echo=False,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_pre_ping=True
)

read_write_engine = create_async_engine(
    read_write_db_connector,
    echo=False,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_pre_ping=True
)


# Фабрики сессий
read_only_session_maker = sessionmaker(
    read_only_engine,
    expire_on_commit=False,
    class_=AnalyticAsyncSession,
)

read_write_session_maker = sessionmaker(
    read_write_engine,
    expire_on_commit=False,
    class_=AnalyticAsyncSession,
)



@asynccontextmanager
async def get_async_session_maker(semaphore=None, read_only=False) -> AsyncSession:
    session_start = time()
    current_task = asyncio.current_task()

    if semaphore is None:
        semaphore = global_semaphore

    # Выбор нужной фабрики сессий
    session_maker = read_only_session_maker if read_only else read_write_session_maker

    try:
        async with semaphore:
            async with session_maker() as session:
                try:
                    yield session
                finally:
                    hold_time = time() - session_start
                    if hold_time > 1.0:
                        logger.warning(f"Session held for too long: {hold_time:.2f}s by task {current_task.get_name()}")
    except Exception as e:
        logger.error(
            f"Session error after {time() - session_start:.3f}s:\n"
            f"Task: {current_task.get_name()}\n"
            f"Error: {str(e)}",
            exc_info=True
        )
        raise
