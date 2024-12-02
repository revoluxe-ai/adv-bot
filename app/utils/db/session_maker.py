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
async def get_async_session_maker(semaphore=None) -> AsyncSession:
    session_start = time()
    current_task = asyncio.current_task()

    if semaphore is None:
        semaphore = global_semaphore

    try:
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

            # Логируем время ожидания сессии
            wait_time = time() - session_start
            if wait_time > 0.1:  # Если ждали больше 100мс
                logger.warning(
                    f"Long session wait time:\n"
                    f"Wait duration: {wait_time:.3f}s\n"
                    f"Task: {current_task.get_name()}\n"
                    f"Active connections: {conn_counter}"
                )

            async with session_maker() as session:
                try:
                    yield session
                finally:
                    hold_time = time() - session_start
                    if hold_time > 1.0:  # Логируем долгие удержания сессии
                        stack = traceback.extract_stack()
                        caller = next((frame for frame in reversed(stack[:-1])
                                       if 'sqlalchemy' not in frame.filename), None)

                        # Собираем больше контекста
                        stack_trace = ''.join(traceback.format_stack()[:-1])

                        logger.warning(
                            f"Long session hold detected:\n"
                            f"Total duration: {hold_time:.3f}s\n"
                            f"Wait time: {wait_time:.3f}s\n"
                            f"Task name: {current_task.get_name()}\n"
                            f"Location: {caller.filename}:{caller.lineno}\n"
                            f"Active connections: {conn_counter}\n"
                            f"Stack trace:\n{stack_trace}"
                        )
    except Exception as e:
        logger.error(
            f"Session error after {time() - session_start:.3f}s:\n"
            f"Task: {current_task.get_name()}\n"
            f"Error: {str(e)}",
            exc_info=True
        )
        raise

