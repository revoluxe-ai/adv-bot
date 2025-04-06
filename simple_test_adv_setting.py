"""
Простой тест для проверки AdvSetting
"""
import pytest
import os
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey, DateTime, JSON, text, create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from typing import List, Dict, Any, Optional, AsyncGenerator
import pytest_asyncio  # Добавляем импорт pytest_asyncio

# Создаем базу тестов
Base = declarative_base()
DB_PATH = 'simple_adv_test.sqlite'

# Модель WBCabinet
class WBCabinet(Base):
    __tablename__ = 'wbcabinet'
    id = Column(Integer, primary_key=True)
    shop_id = Column(String, nullable=False, unique=True)
    active = Column(Boolean, default=True)
    adv_settings = relationship("AdvSetting", back_populates="wb_cabinet")

# Модель AdvSetting
class AdvSetting(Base):
    __tablename__ = 'advsetting'
    id = Column(Integer, primary_key=True)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    settings = Column(JSON, default=dict)
    wb_cabinet = relationship("WBCabinet", back_populates="adv_settings")
    keyword_settings = relationship("KeywordSetting", back_populates="adv_setting")

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для JSON сериализации"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "settings": self.settings or {},
            "wb_cabinet_id": self.wb_cabinet_id
        }

# Модель KeywordSetting
class KeywordSetting(Base):
    __tablename__ = 'keywordsetting'
    id = Column(Integer, primary_key=True)
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'), nullable=False)
    keyword = Column(String, nullable=False)
    cpm = Column(Float, default=0.0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    adv_setting = relationship("AdvSetting", back_populates="keyword_settings")

# Создаем асинхронное подключение к БД
engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")
async_session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture
async def setup_db():
    """Фикстура для создания и удаления таблиц БД"""
    # Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield async_session_maker
    
    # Удаляем таблицы после окончания тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Удаляем файл базы данных
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except:
            pass

@pytest_asyncio.fixture
async def session(setup_db) -> AsyncSession:
    """Фикстура для создания сессии БД"""
    async with setup_db() as session:
        yield session

@pytest.mark.asyncio
async def test_create_adv_setting(session):
    """Тест создания настройки рекламы"""
    # Создаем кабинет
    cabinet = WBCabinet(shop_id="test_shop")
    session.add(cabinet)
    await session.flush()
    
    # Создаем настройку рекламы
    adv_setting = AdvSetting(
        wb_cabinet_id=cabinet.id,
        name="Test Setting",
        description="Test Description",
        is_active=True,
        settings={"budget": 1000, "strategy": "manual"}
    )
    session.add(adv_setting)
    await session.commit()
    
    # Проверяем создание
    from sqlalchemy import select
    query = select(AdvSetting).where(AdvSetting.id == adv_setting.id)
    result = await session.execute(query)
    result_setting = result.scalars().first()
    
    assert result_setting is not None
    assert result_setting.name == "Test Setting"
    assert result_setting.description == "Test Description"
    assert result_setting.is_active is True
    assert result_setting.settings == {"budget": 1000, "strategy": "manual"}

@pytest.mark.asyncio
async def test_adv_setting_to_dict(session):
    """Тест метода to_dict"""
    # Создаем кабинет
    cabinet = WBCabinet(shop_id="test_shop")
    session.add(cabinet)
    await session.flush()
    
    # Создаем настройку рекламы
    adv_setting = AdvSetting(
        wb_cabinet_id=cabinet.id,
        name="Test Setting",
        description="Test Description",
        is_active=True,
        settings={"budget": 1000, "strategy": "manual"}
    )
    session.add(adv_setting)
    await session.commit()
    
    # Проверяем метод to_dict
    result_dict = adv_setting.to_dict()
    
    assert result_dict["id"] == adv_setting.id
    assert result_dict["name"] == "Test Setting"
    assert result_dict["description"] == "Test Description"
    assert result_dict["is_active"] is True
    assert result_dict["settings"] == {"budget": 1000, "strategy": "manual"}
    assert result_dict["wb_cabinet_id"] == cabinet.id

@pytest.mark.asyncio
async def test_adv_setting_relationships(session):
    """Тест связей настройки рекламы"""
    # Создаем кабинет
    cabinet = WBCabinet(shop_id="test_shop")
    session.add(cabinet)
    await session.flush()
    
    # Создаем настройку рекламы
    adv_setting = AdvSetting(
        wb_cabinet_id=cabinet.id,
        name="Test Setting",
        description="Test Description",
        is_active=True
    )
    session.add(adv_setting)
    await session.flush()
    
    # Создаем настройки ключевых слов
    keyword_settings = [
        KeywordSetting(
            adv_setting_id=adv_setting.id,
            keyword=f"keyword_{i}",
            cpm=100 + i * 10,
            active=True
        )
        for i in range(3)
    ]
    for ks in keyword_settings:
        session.add(ks)
    await session.commit()
    
    # Проверяем связь с кабинетом
    assert adv_setting.wb_cabinet_id == cabinet.id
    assert adv_setting.wb_cabinet.shop_id == "test_shop"
    
    # Проверяем связь с настройками ключевых слов
    from sqlalchemy import select
    query = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting.id)
    result = await session.execute(query)
    result_keywords = result.scalars().all()
    
    assert len(result_keywords) == 3
    assert all(ks.adv_setting_id == adv_setting.id for ks in result_keywords)
    assert any(ks.keyword == "keyword_0" and ks.cpm == 100 for ks in result_keywords)
    assert any(ks.keyword == "keyword_1" and ks.cpm == 110 for ks in result_keywords)
    assert any(ks.keyword == "keyword_2" and ks.cpm == 120 for ks in result_keywords)

@pytest.mark.asyncio
async def test_update_adv_setting(session):
    """Тест обновления настройки рекламы"""
    # Создаем кабинет
    cabinet = WBCabinet(shop_id="test_shop")
    session.add(cabinet)
    await session.flush()
    
    # Создаем настройку рекламы
    adv_setting = AdvSetting(
        wb_cabinet_id=cabinet.id,
        name="Test Setting",
        description="Test Description",
        is_active=True,
        settings={"budget": 1000, "strategy": "manual"}
    )
    session.add(adv_setting)
    await session.commit()
    
    # Обновляем настройку
    adv_setting.name = "Updated Setting"
    adv_setting.description = "Updated Description"
    adv_setting.is_active = False
    adv_setting.settings = {"budget": 2000, "strategy": "auto"}
    await session.commit()
    
    # Проверяем обновление
    from sqlalchemy import select
    query = select(AdvSetting).where(AdvSetting.id == adv_setting.id)
    result = await session.execute(query)
    updated_setting = result.scalars().first()
    
    assert updated_setting.name == "Updated Setting"
    assert updated_setting.description == "Updated Description"
    assert updated_setting.is_active is False
    assert updated_setting.settings == {"budget": 2000, "strategy": "auto"}

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 