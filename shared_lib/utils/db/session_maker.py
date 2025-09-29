import asyncio
import logging
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import time
from typing import Any

from sqlalchemy import Result
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from shared_lib import settings

logger = logging.getLogger(__name__)

conn_counter = 0

pool_size = settings.PG_POOL_SIZE
max_overflow = settings.PG_MAX_OVERFLOW

count_sem = settings.COUNT_SEMAPHORE_TO_POSTGRES
global_semaphore = asyncio.Semaphore(count_sem)


#
# ssl_context = ssl.create_default_context(cafile=RDS_CERT_PATH)
# ssl_context.verify_mode = ssl.CERT_REQUIRED


class AnalyticAsyncSession(AsyncSession):
    async def execute(self, statement: Any, *args, **kwargs) -> Result[Any]:
        query_start = time()
        try:
            # Определяем тип операции
            operation_type = type(statement).__name__

            # Анализ стека для поиска вызывающего кода
            stack = traceback.extract_stack()
            caller = next(
                (frame for frame in reversed(stack[:-1]) if "sqlalchemy" not in frame.filename),
                None,
            )

            result: Result[Any] = await super().execute(statement, *args, **kwargs)
            duration = time() - query_start

            if duration > 1.0:
                logger.warning(
                    f"Slow query ({duration:.2f}s), Type: {operation_type} "
                    f"Location: {caller.filename}:{caller.lineno} Statement: {statement}"
                )
            return result
        except Exception as e:
            logger.exception("Query error during execution:")
            raise e


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
    postgres_dbname = settings.postgres_dbname
    postgres_password = settings.postgres_password
    postgres_user = settings.postgres_user
    if not read_only:
        host = settings.postgres_master_host
    else:
        host = settings.postgres_replica_host
    # Для asyncpg используем ssl вместо sslmode
    row_connector = (
        f"postgresql://{postgres_user}:{postgres_password}@{host}:{port}/{postgres_dbname}"
    )
    # if ssl_mode:
    #     row_connector += f'?sslmode={ssl_mode}'
    # row_connector += f'&target_session_attrs={target_session}'

    db_connector = row_connector
    return db_connector


def get_alchemy_row_for_migration():
    port = settings.postgres_port
    postgres_dbname = settings.postgres_dbname
    postgres_password = settings.postgres_password
    postgres_user = settings.postgres_user
    host = settings.postgres_master_host
    # Для asyncpg используем ssl вместо sslmode
    db_connector = (
        f"postgresql://{postgres_user}:{postgres_password}@{host}:{port}/{postgres_dbname}"
    )
    return db_connector


read_only_db_connector = get_alchemy_row(read_only=True).replace(
    "postgresql://", "postgresql+asyncpg://"
)
read_write_db_connector = get_alchemy_row(read_only=False).replace(
    "postgresql://", "postgresql+asyncpg://"
)

read_only_engine = create_async_engine(
    read_only_db_connector,
    echo=False,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_pre_ping=True,
)

read_write_engine = create_async_engine(
    read_write_db_connector,
    echo=False,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_pre_ping=True,
)

# Фабрики сессий
read_only_session_maker = async_sessionmaker(
    bind=read_only_engine,
    expire_on_commit=False,
    class_=AnalyticAsyncSession,
)

read_write_session_maker = async_sessionmaker(
    bind=read_write_engine,
    expire_on_commit=False,
    class_=AnalyticAsyncSession,
)


@asynccontextmanager
async def get_async_session_maker(
        read_only=False,
) -> AsyncGenerator[AsyncSession, None]:
    session_start = time()
    current_task = asyncio.current_task()

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
                        task_name = current_task.get_name()
                        if not task_name:
                            task_name = "unknown"
                        logger.warning(
                            f"Session held for too long: {hold_time:.2f}s by task {task_name}"
                        )
    except Exception as e:
        logger.error(
            f"Session error after {time() - session_start:.3f}s:\n"
            f"Task: {current_task.get_name()}\n"
            f"Error: {str(e)}",
            exc_info=True,
        )
        raise
