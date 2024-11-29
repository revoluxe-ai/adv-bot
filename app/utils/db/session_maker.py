import logging
import threading
import asyncio
import traceback
from contextlib import asynccontextmanager
from time import time

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.settings import settings
from python_modules import path_setting_funcs

logger = logging.getLogger(__name__)

thread_local = threading.local()
lock_counter = threading.Lock()
conn_counter = 0

pool_size = 20
max_overflow = 30


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
                logger.error(
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

def log_checkout(dbapi_con, con_record, con_proxy):
    logger.debug("Соединение взято из пула")
    global conn_counter
    with lock_counter:
        conn_counter += 1
    logger.debug(f"Количество соединений: {conn_counter}")

def log_checkin(dbapi_con, con_record):
    logger.debug("Соединение возвращено в пул")
    global conn_counter
    with lock_counter:
        conn_counter -= 1
    logger.debug(f"Количество соединений: {conn_counter}")

@asynccontextmanager
async def get_async_session_maker(semaphore = None) -> AsyncSession:
    if semaphore is None:
        semaphore = global_semaphore
    async with semaphore:
        if not hasattr(thread_local, "session_maker"):
            db_connector = path_setting_funcs.get_alchemy_row()
            async_db_connector = db_connector.replace("postgresql://", "postgresql+asyncpg://")
            engine = create_async_engine(
                async_db_connector,
                echo=False,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True
            )
            sync_engine = engine.sync_engine
            event.listen(sync_engine, "checkout", log_checkout)
            event.listen(sync_engine, "checkin", log_checkin)

            async_session_maker = sessionmaker(engine, expire_on_commit=False,
                                               class_=AnalyticAsyncSession)
            thread_local.session_maker = async_session_maker

        session_maker = thread_local.session_maker
        async with session_maker() as session:
            yield session

