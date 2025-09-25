from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio.session import async_sessionmaker # Импортируем async_sessionmaker
import os
from typing import Any

# Я предполагаю, что настройки базы данных берутся из переменных окружения
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

Base = declarative_base()

class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    dhash = Column(String, unique=True, index=True)
    is_background = Column(Boolean, default=False)
    # Добавьте другие поля, если они используются, например, путь к файлу или URL
    # path = Column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<Image(id={self.id}, dhash='{self.dhash}', is_background={self.is_background})>"

# Создаем асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаем фабрику сессий
async_session = async_sessionmaker(
    bind=engine, expire_on_commit=False # Используем async_sessionmaker
)

def get_session() -> Any:
    # Возвращаем фабрику сессий, чтобы DataBase мог создавать новые сессии
    return async_session

# Функция для создания таблиц (для инициализации базы данных)
async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
