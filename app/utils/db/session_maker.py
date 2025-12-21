import asyncio
import logging
import os
import ssl
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import time
from typing import Any

from sqlalchemy import Result
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from app.settings import settings

# TODO: Сделать отдельную настройку
#  количества соединений для каждого микросервиса
#  В перспективе Перейти на PGbouncer или Pgpool-II
#  для балансировки нагрузки между мастером и репликами

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

def _is_pytest() -> bool:
    """True when running under pytest.

    Important: in our test suite event loop is often function-scoped; asyncpg connections
    are bound to the loop they were created in. If we keep a pooled connection across tests,
    the next test will run on a new loop and will crash with 'Event loop is closed'.
    """
    return "PYTEST_CURRENT_TEST" in os.environ


def _make_engine(db_url: str):
    if _is_pytest():
        # No pooling in tests to avoid cross-event-loop reuse of asyncpg connections.
        return create_async_engine(
            db_url,
            echo=False,
            poolclass=NullPool,
            pool_pre_ping=True,
            connect_args={"ssl": ssl_ctx},
        )

    return create_async_engine(
        db_url,
        echo=False,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=180,
        pool_pre_ping=True,
        connect_args={"ssl": ssl_ctx},
    )


_read_only_engine: AsyncEngine | None = None
_read_write_engine: AsyncEngine | None = None
_read_only_session_maker: async_sessionmaker[AnalyticAsyncSession] | None = None
_read_write_session_maker: async_sessionmaker[AnalyticAsyncSession] | None = None
_engine_init_lock = asyncio.Lock()


async def _get_engine(read_only: bool) -> AsyncEngine:
    """Lazily build engines so test detection works reliably.

    Important: `PYTEST_CURRENT_TEST` is set by pytest during test execution, not at import
    time. If we eagerly create engines at import time, we may end up with pooled asyncpg
    connections being reused across different event loops (function-scoped loops), causing
    `RuntimeError: Event loop is closed` on Windows.
    
    Thread-safe: использует asyncio.Lock для предотвращения создания нескольких движков
    при одновременных вызовах.
    """
    global _read_only_engine, _read_write_engine
    
    async with _engine_init_lock:
        if read_only:
            if _read_only_engine is None:
                _read_only_engine = _make_engine(read_only_db_connector)
            return _read_only_engine

        if _read_write_engine is None:
            _read_write_engine = _make_engine(read_write_db_connector)
        return _read_write_engine

async def _get_session_maker(read_only: bool):
    global _read_only_session_maker, _read_write_session_maker

    maker = _read_only_session_maker if read_only else _read_write_session_maker
    if maker is not None:
        return maker

    engine = await _get_engine(read_only)

    async with _engine_init_lock:
        maker = _read_only_session_maker if read_only else _read_write_session_maker
        if maker is None:
            maker = async_sessionmaker(
                bind=engine,
                expire_on_commit=False,
                class_=AnalyticAsyncSession,
            )
            if read_only:
                _read_only_session_maker = maker
            else:
                _read_write_session_maker = maker

        return maker
