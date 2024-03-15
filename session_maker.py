from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from python_modules import path_setting_funcs
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


def get_async_session_maker(pool_size=500, max_overflow=600):
    """Функция для создания асинхронного генератора сессий с увеличенным размером пула и очереди."""
    db_connector = path_setting_funcs.get_alchemy_row()
    # Дополняем строку подключения для использования асинхронного драйвера
    async_db_connector = db_connector.replace("postgresql://", "postgresql+asyncpg://")

    # Создаем асинхронный движок с настроенными параметрами pool_size и max_overflow
    engine = create_async_engine(
        async_db_connector,
        pool_size=pool_size,  # Размер пула соединений
        max_overflow=max_overflow,
        pool_timeout=30,  # Время ожидания в секундах при попытке получить соединение из пула
        pool_recycle=1800,  # Время в секундах, после которого соединение будет переподключено
        # Настройки тайм-аутов для asyncpg
        connect_args={
            "command_timeout": 60  # Тайм-аут для операций с базой данных в секундах
        }
        # Максимальное количество соединений сверх размера пула
    )

    # Создаем асинхронный sessionmaker
    async_session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


    return async_session_maker








def get_session_maker():
    """функция не отражала суть"""
    return get_session()

def get_session():
    db_connector = path_setting_funcs.get_alchemy_row()
    engine = create_engine(
        db_connector)
    return sessionmaker(bind=engine)
