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

thread_local = threading.local()
lock_counter = threading.Lock()
conn_counter = 0

pool_size = 20
max_overflow = 30

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


def get_alchemy_row(read_only):
    port = settings.postgres_port
    file_path = path_setting_funcs.get_setting_path()
    postgres_dbname = path_setting_funcs.get_document_by_key_name(file_path, 'postgres-dbname')
    # postgres_host = path_setting_funcs.get_document_by_key_name(file_path, 'postgres-host')
    postgres_password = path_setting_funcs.get_document_by_key_name(file_path, 'postgres-password')
    postgres_user = path_setting_funcs.get_document_by_key_name(file_path, 'postgres-user')
    if not read_only:
        host = path_setting_funcs.get_document_by_key_name(file_path, 'postgres-master-host')
    else:
        host = path_setting_funcs.get_document_by_key_name(file_path, 'postgres-replica-host')

    # Для asyncpg используем ssl вместо sslmode

    target_session = 'read-write' if not read_only else 'any'
    db_connector = (
        f'postgresql://{postgres_user}:{postgres_password}@{host}:{port}/{postgres_dbname}'
        '?ssl=verify-full'
        f'&target_session_attrs={target_session}'
    )
    return db_connector


@asynccontextmanager
async def get_async_session_maker(semaphore=None, read_only=True) -> AsyncSession:
    session_start = time()
    current_task = asyncio.current_task()

    if semaphore is None:
        semaphore = global_semaphore

    try:
        async with semaphore:
            if not hasattr(thread_local, "session_maker"):
                db_connector = get_alchemy_row(read_only)
                async_db_connector = db_connector.replace("postgresql://", "postgresql+asyncpg://")

                engine = create_async_engine(
                    async_db_connector,
                    echo=False,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_pre_ping=False
                )

                sync_engine = engine.sync_engine
                event.listen(sync_engine, "checkout", log_checkout)
                event.listen(sync_engine, "checkin", log_checkin)

                async_session_maker = sessionmaker(
                    engine,
                    expire_on_commit=False,
                    class_=AnalyticAsyncSession
                )
                thread_local.session_maker = async_session_maker

            session_maker = thread_local.session_maker

            async with session_maker() as session:
                # if read_only:
                #     await session.execute(text("SET TRANSACTION READ ONLY"))
                try:
                    yield session
                finally:
                    hold_time = time() - session_start
                    if hold_time > 1.0:
                        # ... код логирования ...
                        pass
    except Exception as e:
        logger.error(
            f"Session error after {time() - session_start:.3f}s:\n"
            f"Task: {current_task.get_name()}\n"
            f"Error: {str(e)}",
            exc_info=True
        )
        raise