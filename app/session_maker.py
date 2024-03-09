from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from python_modules import path_setting_funcs
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession



def get_async_session_maker():
    """Функция для создания асинхронного генератора сессий."""
    db_connector = path_setting_funcs.get_alchemy_row()
    # Дополняем строку подключения для использования асинхронного драйвера
    async_db_connector = db_connector.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_db_connector)

    # Создаем асинхронный sessionmaker
    async_session_maker = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    return async_session_maker

