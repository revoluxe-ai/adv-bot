import logging
import threading

import sqlalchemy.orm.session
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from python_modules import path_setting_funcs

logger = logging.getLogger(__name__)

thread_local = threading.local()

lock_counter = threading.Lock()

thread_local.connect_opened = False

conn_counter = 0

def get_async_session_maker(pool_size=100, max_overflow=200)-> sessionmaker:
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

    if not hasattr(thread_local, "session_maker"):
        db_connector = path_setting_funcs.get_alchemy_row()
        async_db_connector = db_connector.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(
            async_db_connector,
            echo=False,
            pool_size=pool_size,
            max_overflow=max_overflow,
            # Параметры pool_size и max_overflow можно добавить здесь
        )
        sync_engine = engine.sync_engine
        event.listen(sync_engine, "checkout", log_checkout)
        event.listen(sync_engine, "checkin", log_checkin)

        async_session_maker = sessionmaker(engine,
                                           expire_on_commit=False,
                                           class_=AsyncSession)
        thread_local.session_maker = async_session_maker
    return thread_local.session_maker

def get_session_maker():
    connector = path_setting_funcs.get_alchemy_row()
    engine = create_engine(connector)
    return sessionmaker(bind=engine)
