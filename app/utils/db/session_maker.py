import asyncio
import logging
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import time
from typing import Any, Sequence, Mapping, Union, overload

from sqlalchemy import Result, Executable, UpdateBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
# from sqlalchemy.sql._typing import _TypedReturnsRows as TypedReturnsRows
# from sqlalchemy.engine.interfaces import _OrmKnownExecutionOptions

from app.settings import settings

logger = logging.getLogger(__name__)

conn_counter = 0

pool_size = settings.PG_POOL_SIZE
max_overflow = settings.PG_MAX_OVERFLOW

count_sem = settings.COUNT_SEMAPHORE_TO_POSTGRES
global_semaphore = asyncio.Semaphore(count_sem)


def get_alchemy_row(read_only: bool) -> str:
    port = settings.postgres_port
    postgres_dbname = settings.postgres_dbname
    postgres_password = settings.postgres_password
    postgres_user = settings.postgres_user
    if not read_only:
        host = settings.postgres_master_host
    else:
        host = settings.postgres_replica_host
    row_connector = f"postgresql://{postgres_user}:{postgres_password}@{host}:{port}/{postgres_dbname}"
    db_connector = row_connector
    return db_connector

def get_alchemy_row_for_migration() -> str:
    port = settings.postgres_port
    postgres_dbname = settings.postgres_dbname
    postgres_password = settings.postgres_password
    postgres_user = settings.postgres_user
    host = settings.postgres_master_host
    db_connector = f"postgresql://{postgres_user}:{postgres_password}@{host}:{port}/{postgres_dbname}"
    return db_connector

read_only_db_connector = get_alchemy_row(read_only=True).replace("postgresql://", "postgresql+asyncpg://")
read_write_db_connector = get_alchemy_row(read_only=False).replace("postgresql://", "postgresql+asyncpg://")

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

read_only_session_maker = sessionmaker(
    bind=read_only_engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession, # type: ignore[call-overload]
)

read_write_session_maker = sessionmaker(
    bind=read_write_engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession, # type: ignore[call-overload]
)

@asynccontextmanager
async def get_async_session_maker(
    read_only: bool = False,
) -> AsyncGenerator[AsyncSession, None]:
    session_start = time()
    current_task = asyncio.current_task()

    semaphore = global_semaphore

    session_maker = read_only_session_maker if read_only else read_write_session_maker

    try:
        async with semaphore:
            async with session_maker() as session:
                try:
                    yield session
                finally:
                    hold_time = time() - session_start
                    if hold_time > 1.0:
                        task_name = current_task.get_name() if current_task else "Unknown Task"
                        logger.warning(f"Session held for too long: {hold_time:.2f}s by task {task_name}")
    except Exception as e:
        task_name = current_task.get_name() if current_task else "Unknown Task"
        logger.error(
            f"Session error after {time() - session_start:.3f}s:\nTask: {task_name}\nError: {str(e)}",
            exc_info=True,
        )
        raise
