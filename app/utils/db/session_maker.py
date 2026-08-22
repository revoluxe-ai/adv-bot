"""Фабрики асинхронных SQLAlchemy-сессий для PostgreSQL домена adv-bot.

Модуль централизует создание read-only/read-write engine и sessionmaker для
бота, воркеров и фоновых задач. Настройки asyncpg учитывают работу через
PgBouncer, чтобы prepared statements не конфликтовали при transaction pooling.
"""

import asyncio
import logging
import os
import ssl
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import time
from typing import Any
from uuid import uuid4

from sqlalchemy import Result
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.settings import settings

# TODO: Сделать отдельную настройку
#  количества соединений для каждого микросервиса
#  В перспективе Перейти на PGbouncer или Pgpool-II
#  для балансировки нагрузки между мастером и репликами

logger = logging.getLogger(__name__)

conn_counter = 0

pool_size = settings.PG_POOL_SIZE
max_overflow = settings.PG_MAX_OVERFLOW


#
# ssl_context = ssl.create_default_context(cafile=RDS_CERT_PATH)
# ssl_context.verify_mode = ssl.CERT_REQUIRED


class AnalyticAsyncSession(AsyncSession):
    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Result[Any]:
        query_start = time()
        try:
            # Определяем тип операции
            operation_type = type(statement).__name__

            # Анализ стека для поиска вызывающего кода
            stack = traceback.extract_stack()
            caller = next(
                (
                    frame
                    for frame in reversed(stack[:-1])
                    if "sqlalchemy" not in frame.filename
                ),
                None,
            )

            result: Result[Any] = await super().execute(statement, *args, **kwargs)
            duration = time() - query_start

            if duration > 1.0:
                # caller может быть None
                if caller is not None:
                    filename = caller.filename
                    lineno = caller.lineno
                else:
                    filename = "unknown"
                    lineno = 0
                logger.warning(
                    f"Slow query ({duration:.2f}s), Type: {operation_type} "
                    f"Location: {filename}:{lineno} Statement: {statement}"
                )
            return result
        except Exception as e:
            logger.exception("Query error during execution:")
            raise e


def get_alchemy_row(read_only: bool) -> str:
    port = settings.postgres_port
    postgres_dbname = settings.postgres_dbname
    postgres_password = settings.postgres_password
    postgres_user = settings.postgres_user
    if not read_only:
        host = settings.postgres_master_host
    else:
        host = settings.postgres_replica_host
    # Для asyncpg используем ssl через connect_args, не передаём sslmode в URL
    row_connector = f"postgresql://{postgres_user}:{postgres_password}@{host}:{port}/{postgres_dbname}"
    # if ssl_mode:
    #     row_connector += f'?sslmode={ssl_mode}'
    # row_connector += f'&target_session_attrs={target_session}'

    db_connector = row_connector
    return db_connector


def get_alchemy_row_for_migration() -> str:
    """DSN для Alembic: приоритет DATABASE_URL, иначе POSTGRES_* settings."""
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        return database_url
    port = settings.postgres_port
    postgres_dbname = settings.postgres_dbname
    postgres_password = settings.postgres_password
    postgres_user = settings.postgres_user
    host = settings.postgres_master_host
    # Для asyncpg используем ssl через connect_args, не передаём sslmode в URL
    db_connector = f"postgresql://{postgres_user}:{postgres_password}@{host}:{port}/{postgres_dbname}"
    return db_connector


read_only_db_connector = get_alchemy_row(read_only=True).replace(
    "postgresql://", "postgresql+asyncpg://"
)
read_write_db_connector = get_alchemy_row(read_only=False).replace(
    "postgresql://", "postgresql+asyncpg://"
)


def get_ssl_context(
    insecure: bool, ssl_mode: str | None = None
) -> ssl.SSLContext | None:
    """Возвращает SSLContext или None (если SSL отключен).

    Если ssl_mode='disable' — возвращаем None (SSL полностью отключен).
    Если insecure=True — отключаем проверку (только для отладки).
    В противном случае используем системные корни и, при наличии,
    передаём путь к CA из настроек.
    """
    # Полное отключение SSL
    if ssl_mode and ssl_mode.lower() == "disable":
        return None

    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    # Безопасный путь: используем системные корни или указанный CA
    from app.settings import settings

    ca = getattr(settings, "POSTGRES_SSL_CA", None)
    if ca:
        return ssl.create_default_context(cafile=ca)
    return ssl.create_default_context()


ssl_ctx = get_ssl_context(
    getattr(settings, "POSTGRES_SSL_INSECURE", False),
    getattr(settings, "ssl_mode", None),
)

# asyncpg при ssl=None может пытаться SSL-handshake; при disable не передаём ключ.
_pg_connect_args: dict[str, Any] = {
    # PgBouncer transaction mode переиспользует server connections между
    # клиентами, поэтому отключаем client-side prepared statement caches и
    # генерируем уникальные server-side statement names.
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
}
if ssl_ctx is not None:
    _pg_connect_args["ssl"] = ssl_ctx

read_only_engine = create_async_engine(
    read_only_db_connector,
    echo=False,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_recycle=180,
    pool_pre_ping=True,
    connect_args=_pg_connect_args,
)

read_write_engine = create_async_engine(
    read_write_db_connector,
    echo=False,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_recycle=180,
    pool_pre_ping=True,
    connect_args=_pg_connect_args,
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
    read_only: bool = False,
) -> AsyncGenerator[AsyncSession, None]:
    session_start = time()
    current_task = asyncio.current_task()

    from app.utils.resource_limits import get_postgres_query_semaphore

    semaphore = get_postgres_query_semaphore()

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
                        if current_task is not None:
                            try:
                                task_name = current_task.get_name()
                            except Exception:
                                task_name = "unknown"
                        else:
                            task_name = "unknown"
                        logger.warning(
                            f"Session held for too long: {hold_time:.2f}s by task {task_name}"
                        )
    except Exception as e:
        logger.error(
            f"Session error after {time() - session_start:.3f}s:\n"
            f"Task: {current_task.get_name() if current_task else 'Не известная задача'}\n"
            f"Error: {str(e)}",
            exc_info=True,
        )
        raise
