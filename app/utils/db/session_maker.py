import logging
import threading
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.settings import settings
from python_modules import path_setting_funcs

logger = logging.getLogger(__name__)

thread_local = threading.local()
lock_counter = threading.Lock()
conn_counter = 0

pool_size = 300
max_overflow = 500

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
            )
            sync_engine = engine.sync_engine
            event.listen(sync_engine, "checkout", log_checkout)
            event.listen(sync_engine, "checkin", log_checkin)

            async_session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            thread_local.session_maker = async_session_maker

        session_maker = thread_local.session_maker
        async with session_maker() as session:
            yield session