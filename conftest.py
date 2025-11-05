# mypy: ignore-errors

import os

# Устанавливаем переменные окружения для тестовой БД ДО любых импортов
os.environ["POSTGRES_MASTER_HOST"] = "localhost"
os.environ["POSTGRES_REPLICA_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_DBNAME"] = "test_adv_bot_db"
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "test_password"
os.environ["POSTGRES_SSL_MODE"] = "disable"
os.environ["POSTGRES_SSL_INSECURE"] = "true"

# Обязательные переменные для работы settings
os.environ.setdefault("TELEGRAM_WEB_PORT", "8080")
os.environ.setdefault("CH_MAX_THREAD", "10")
os.environ.setdefault("BIDDER_STEP_RUB", "1")
os.environ.setdefault("CLICKHOUSE_PORT", "9000")
os.environ.setdefault("CLICK_HOUSE_HOST", "localhost")
os.environ.setdefault("CLICK_HOUSE_USER", "default")
os.environ.setdefault("CLICK_HOUSE_PASSWORD", "test")
os.environ.setdefault("REDIS_MASTER_HOST", "localhost")
os.environ.setdefault("REDIS_REPLICA_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("BOT_TOKEN", "test_token_123")
os.environ.setdefault("WEBHOOK_SECRET", "test_secret")
os.environ.setdefault("YOOKASSA_TOKEN", "test_yookassa")
os.environ.setdefault("MIN_SUM", "0")

TEST_DB_POSTGRES_URL = "postgresql://test_user:test_password@localhost:5433/test_adv_bot_db"
os.environ["TEST_DB_POSTGRES_URL"] = TEST_DB_POSTGRES_URL


import dotenv

# Загружаем .env, но НЕ перезаписываем уже установленные переменные окружения для тестов
dotenv.load_dotenv(override=False)
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


# Подставляем заглушку для app.core.wb_api.http_request до реальных импортов
import types

mod_name = "app.core.wb_api.http_request"
import importlib

import asyncio
import os
import time
from unittest.mock import MagicMock
from datetime import datetime, timedelta


import pytest

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app.modules.common_slaves.wildberries.models import WBCabinet

# Переменные окружения для тестовой БД
TEST_DB_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_adv_bot_db"
COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "tests", "docker-compose.test.yml")


@pytest.fixture(scope="session")
def docker_compose_file():
    return COMPOSE_FILE


@pytest.fixture(scope="session")
def event_loop():
    """Создаёт новый event loop и безопасно закрывает его после всех тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    try:
        # Корректно завершаем асинхронные генераторы и таски
        loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        loop.close()



@pytest.fixture(scope="session", autouse=True)
async def setup_test_database(docker_compose_file):
    print(f"Starting Docker Compose: {docker_compose_file}")
    import subprocess
    subprocess.run(["docker-compose", "-f", docker_compose_file, "up", "-d", "--build"], check=True)

    # --- Ожидание запуска контейнера ---
    max_retries = 30
    for i in range(max_retries):
        try:
            result = subprocess.run(["docker-compose", "-f", docker_compose_file, "ps", "-q", "test_db"],
                                    capture_output=True, text=True, check=True)
            container_id = result.stdout.strip()

            if container_id:
                health_status_result = subprocess.run(
                    ["docker", "inspect", "--format", '{{.State.Health.Status}}', container_id],
                    capture_output=True, text=True, check=True)
                health_status = health_status_result.stdout.strip()
                if health_status == "healthy":
                    print("[OK] Test database is healthy.")
                    break
            print(f"[WAIT] Waiting for test database... Attempt {i + 1}/{max_retries}")
        except subprocess.CalledProcessError as e:
            print(f"Error checking Docker health: {e}")
            print(e.stderr)
        time.sleep(2)
    else:
        raise RuntimeError("Test database did not become healthy in time.")

    from app.utils.db.base import BaseTable as Base
    from sqlalchemy import create_engine
    
    print("[MIGRATION] Creating PostgreSQL extensions...")
    
    # Создаем синхронный движок для создания расширений и таблиц
    sync_engine = create_engine(TEST_DB_URL.replace("postgresql+asyncpg", "postgresql"))
    
    # Создаем необходимые расширения PostgreSQL ПЕРЕД созданием таблиц
    with sync_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        conn.commit()
    
    print("[MIGRATION] Creating tables from models metadata...")
    
    # Создаем все таблицы из метадаты моделей
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    
    print("[OK] Tables created successfully from models metadata.")
    
    # Теперь применяем миграции (если есть изменения схемы)
    from alembic.config import Config
    from alembic import command

    print("[MIGRATION] Running Alembic migrations for test database (Python API)...")

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic_")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)

    # Помечаем все миграции как применённые, так как мы создали таблицы из моделей
    command.stamp(alembic_cfg, "head")

    print("[OK] Alembic migrations stamped successfully.")

    # --- Гарантируем наличие базовых данных ---
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        initial_wb_cabinet_data = {
            "id": 1,
            "shop_id": "test_shop_id",
            "active": True,
            "expiration_time": datetime.now() + timedelta(days=7),
            "balance": 0.0,
            "bonus": 0.0,
            "demo": True,
            "expiration_alarm_days_pass": None,
            "white_list_update_active": False,
        }

        insert_stmt = insert(WBCabinet).values(initial_wb_cabinet_data)
        on_conflict_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={k: v for k, v in initial_wb_cabinet_data.items() if k != "id"},
        )
        await conn.execute(on_conflict_stmt)
        await conn.commit()

    await engine.dispose()

    yield

    print(f"[CLEANUP] Stopping Docker Compose: {docker_compose_file}")
    subprocess.run(["docker-compose", "-f", docker_compose_file, "down", "-v"], check=True)


@pytest.fixture(scope="session", name="async_engine")
async def _async_engine():
    """Создаёт движок для всей сессии."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield engine
    # ⚠️ важно: не await здесь, а делаем безопасно через таск
    try:
        await engine.dispose()
    except Exception:
        pass


@pytest.fixture(name="async_session")
async def _async_session(async_engine) -> AsyncSession:
    """Создаёт сессию с безопасным откатом после теста."""
    async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        trans = await session.begin()
        yield session
        if trans.is_active:  # ✅ rollback только если транзакция ещё открыта
            await trans.rollback()
        await session.close()


# Фикстура для доступа к mock access
@pytest.fixture(name="access_mock")
def _access_mock():
    mock = MagicMock()
    mock.wb_cabinet = MagicMock(spec=WBCabinet)
    mock.wb_cabinet.id = 1
    mock.wb_cabinet.shop_id = "test_shop_id"
    return mock


try:
    # If a previous stub without __file__ exists, remove it to allow real import
    if mod_name in sys.modules and not getattr(sys.modules[mod_name], "__file__", None):
        del sys.modules[mod_name]
    m = importlib.import_module(mod_name)

    # Защитим декоратор на случай проблем с импортом/циклическими зависимостями
    def _try_except_decorator_stub(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

    try:
        setattr(m, "try_except_decorator", _try_except_decorator_stub)
    except Exception:
        pass
except Exception:
    # During early test phases some deps may be missing — create a stub module
    stub_mod = types.ModuleType(mod_name)

    def try_except_decorator(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

    # Do not stub 'requests' here; tests should mock HTTP behavior themselves
    stub_mod.try_except_decorator = try_except_decorator
    sys.modules[mod_name] = stub_mod

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBToken
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Настраиваем переменные окружения для тестов
os.environ["PYTHONPATH"] = str(project_root)


def pytest_configure(config) -> None:
    """
    Конфигурация pytest для корректного поиска и запуска тестов
    """
    # Добавляем метки для тестов
    config.addinivalue_line("markers", "unit: маркирует unit-тесты")
    config.addinivalue_line("markers", "integration: маркирует интеграционные тесты")


@pytest.fixture
def tokens_mock() -> list[MagicMock]:
    token_mock = MagicMock(spec=WBToken)
    return [token_mock]


@pytest.fixture
def wb_cabinet_mock() -> MagicMock():
    return MagicMock()


@pytest.fixture
def access_mock(tokens_mock, wb_cabinet_mock):
    access_mock = MagicMock(spec=WBCabinetAccess)
    access_mock.tokens = tokens_mock
    access_mock.wb_cabinet = wb_cabinet_mock
    return access_mock


@pytest.fixture
def adv_setting_mock():
    adv_setting_mock = MagicMock(spec=AdvSetting)
    adv_setting_mock.adv_id = 25040169
    adv_setting_mock.nmids = [222811118]
    adv_setting_mock.active_status = "started"
    return adv_setting_mock


@pytest.fixture
def session_mock(result_mock):
    session_mock = MagicMock()
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_mock.commit = AsyncMock(return_value=None)
    return session_mock


@pytest.fixture
def get_async_session_mock(session_mock) -> MagicMock:
    session_maker_mock = MagicMock()
    session_maker_mock.__aenter__ = AsyncMock(return_value=session_mock)
    get_session_maker_mock = MagicMock(return_value=session_maker_mock)
    return get_session_maker_mock


from unittest.mock import MagicMock

from pytest import fixture


@fixture
def keywords_mocks() -> list[MagicMock]:
    """Фикстура для генерации моков CalculatedKeyword с заданными параметрами"""
    keyword_params = [
        {
            "best_keyword_status": True,
            "baes_ctr": 0.5,
            "hard_status": 2,
            "spend": 100,
            "relevant": True,
            "keyword_setting_original_id": 1,
        },
        {
            "best_keyword_status": False,
            "baes_ctr": 0.2,
            "hard_status": 2,
            "spend": 10,
            "relevant": False,
            "keyword_setting_original_id": 2,
        },
        {
            "best_keyword_status": False,
            "baes_ctr": 0.1,
            "hard_status": 2,
            "spend": 40,
            "relevant": True,
            "keyword_setting_original_id": 3,
        },
        {
            "best_keyword_status": False,
            "baes_ctr": 0.4,
            "hard_status": 1,
            "spend": 0,
            "relevant": False,
            "keyword_setting_original_id": 4,
        },
    ]

    mocks = []
    for params in keyword_params:
        mock = MagicMock(spec=CalculatedKeyword)
        for key, value in params.items():
            setattr(mock, key, value)
        mocks.append(mock)

    return mocks
