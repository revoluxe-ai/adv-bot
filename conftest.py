# mypy: ignore-errors
# IMPORTANT: Set environment variables BEFORE any imports that might use them!
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

# FORCE override ClickHouse settings for tests (must connect to test container, not production!)
os.environ["CLICKHOUSE_PORT"] = "8124"  # HTTP port for test ClickHouse
os.environ["CLICK_HOUSE_HOST"] = "localhost"
os.environ["CLICK_HOUSE_USER"] = "CLICK_HOUSE_USER"  # Username from docker-compose.test.yml
os.environ["CLICK_HOUSE_PASSWORD"] = "password"  # Password from docker-compose.test.yml

# Обязательные переменные для работы settings
os.environ.setdefault("TELEGRAM_WEB_PORT", "8080")
os.environ.setdefault("CH_MAX_THREAD", "10")
os.environ.setdefault("BIDDER_STEP_RUB", "1")
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

# Now it's safe to import modules that use settings
import asyncio
from clickhouse_connect import get_async_client
from fakeredis import FakeRedis
import aiofiles
from dependency_injector import containers
import fakeredis
import typing
if typing.TYPE_CHECKING:
    from app.core.di.app_container import AppContainer
    from app.modules.common_slaves.wildberries.models import WBCabinet

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


# Подставляем заглушку для app.core.wb_api.http_request до реальных импортов
import types

mod_name = "app.core.wb_api.http_request"
import importlib


import subprocess
import time
import atexit
from datetime import datetime, timedelta

import pytest

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text, create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.pool import NullPool

from app.utils.db.base import BaseTable as Base

from typing import AsyncGenerator
# Переменные окружения для тестовой БД
TEST_DB_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_adv_bot_db"
COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "tests", "docker-compose.test.yml")

# Глобальное хранилище для cleanup контейнеров
_DOCKER_CLEANUP_STATE = {"compose_cmd": None, "container_id": None}


def _sync_run(*args: str, timeout: float | None = None) -> tuple[int, str, str]:
    """Синхронный запуск команды с таймаутом. Возвращает (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
            errors="ignore",
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout while running: {' '.join(args)}"


def _detect_compose_cmd() -> list[str]:
    """Определяет доступную форму запуска compose: ['docker', 'compose'] или ['docker-compose']."""
    # Предпочитаем новый docker compose
    rc, *_ = _sync_run("docker", "compose", "version", timeout=5)
    if rc == 0:
        return ["docker", "compose"]
    # Фолбэк на старый docker-compose
    rc, *_ = _sync_run("docker-compose", "version", timeout=5)
    if rc == 0:
        return ["docker-compose"]
    return []


def _emergency_cleanup():
    """Аварийная очистка контейнеров при выходе из pytest (если нормальный teardown провалился)."""
    cid = _DOCKER_CLEANUP_STATE.get("container_id")
    cmd = _DOCKER_CLEANUP_STATE.get("compose_cmd")

    if cid:
        print(f"\n[EMERGENCY CLEANUP] Force removing container: {cid}")
        _sync_run("docker", "stop", "-t", "1", cid, timeout=5)
        _sync_run("docker", "rm", "-f", cid, timeout=5)

    if cmd:
        print(f"\n[EMERGENCY CLEANUP] Compose down: {COMPOSE_FILE}")
        _sync_run(*cmd, "-f", COMPOSE_FILE, "down", "-v", "--timeout", "1", timeout=15)


# Регистрируем emergency cleanup на случай краша pytest
atexit.register(_emergency_cleanup)


@pytest.fixture(scope="session")
def docker_compose_cmd() -> list[str]:
    """Определяет команду для запуска Docker Compose и падает ошибкой, если недоступна."""
    cmd = _detect_compose_cmd()
    if not cmd:
        raise RuntimeError(
            "Docker Compose не найден в системе. Установите Docker Desktop/Engine "
            "и убедитесь, что доступны команды `docker compose` или `docker-compose`, "
            "затем перезапустите pytest."
        )
    _DOCKER_CLEANUP_STATE["compose_cmd"] = cmd
    return cmd


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(docker_compose_cmd):
    from app.modules.common_slaves.wildberries.models import WBCabinet
    """Синхронная фикстура для настройки тестовой базы данных с помощью Docker Compose и Alembic."""
    print(f"\n[SETUP] Starting Docker Compose: {COMPOSE_FILE}")

    # --- Запуск Docker Compose ---
    rc, out, err = _sync_run(*docker_compose_cmd, "-f", COMPOSE_FILE, "up", "-d", "--build", timeout=180)
    if rc != 0:
        raise RuntimeError(f"Failed to start Docker Compose services. rc={rc} stderr={err}")

    # --- Ожидание запуска контейнера ---
    container_id: str = ""
    max_retries = 30
    for i in range(max_retries):
        rc, cid_out, _ = _sync_run(*docker_compose_cmd, "-f", COMPOSE_FILE, "ps", "-q", "test_db", timeout=10)
        container_id = cid_out.strip()
        if container_id:
            _DOCKER_CLEANUP_STATE["container_id"] = container_id  # Сохраняем для emergency cleanup
            rc, health, _ = _sync_run(
                "docker", "inspect", "--format", "{{.State.Health.Status}}", container_id, timeout=10
            )
            if rc == 0 and health.strip() == "healthy":
                print("[OK] Test database is healthy.")
                break
        print(f"[WAIT] Waiting for test database... Attempt {i + 1}/{max_retries}")
        time.sleep(2)
    else:
        # Если так и не дождались health=healthy — покажем статус и логи для диагностики
        _sync_run("docker", "ps", "-a", timeout=10)
        if container_id:
            _sync_run("docker", "logs", container_id, timeout=10)
        raise RuntimeError("Test database did not become healthy in time.")

    print("[DB] Resetting PostgreSQL schema for tests...")

    # Добавим небольшую задержку перед манипуляциями со схемой
    time.sleep(5)

    sync_engine = create_engine(TEST_DB_POSTGRES_URL)

    # Полностью пересоздаём public-схему, чтобы избавиться от старых enum'ов и таблиц
    with sync_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS public;"))

    # Создаём необходимые расширения PostgreSQL в новой схеме
    with sync_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

    print("[DB] Creating tables from SQLAlchemy metadata...")
    Base.metadata.create_all(sync_engine)
    print("[OK] Tables created successfully from models metadata.")

    sync_engine.dispose()

    # --- Базовые данные (async) ---
    # Создаём минимальный event loop только для этой задачи
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async def insert_initial_data():
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

        loop.run_until_complete(insert_initial_data())
    finally:
        loop.close()

    print("[OK] Test database setup complete.")

    yield

    # --- TEARDOWN ---
    print(f"\n[CLEANUP] Stopping Docker Compose: {COMPOSE_FILE}")

    # Сначала пытаемся остановить контейнер gracefully
    if container_id:
        _sync_run("docker", "stop", "-t", "2", container_id, timeout=10)

    # Затем compose down с очень коротким таймаутом
    rc, _, err = _sync_run(
        *docker_compose_cmd,
        "-f",
        COMPOSE_FILE,
        "down",
        "-v",
        "--remove-orphans",
        "--timeout",
        "1",
        timeout=20,
    )
    if rc != 0:
        print(f"[WARNING] 'compose down' failed rc={rc}: {err.strip()}")

    # Финальная зачистка
    if container_id:
        _sync_run("docker", "rm", "-f", container_id, timeout=10)
        _DOCKER_CLEANUP_STATE["container_id"] = None

    print("[OK] Cleanup complete.")



@pytest.fixture(scope="function", name="async_engine")
async def _async_engine():
    """Создаёт async движок для каждого теста."""
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture(name="async_session")
async def _async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Создаёт async сессию с откатом после теста."""
    async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        trans = await session.begin()
        try:
            yield session
        finally:
            if trans.is_active:
                await trans.rollback()
            await session.close()



# Фикстура для доступа к mock access (простая версия)
@pytest.fixture(name="access_mock_simple")
def _access_mock():
    mock = MagicMock()
    mock.wb_cabinet = MagicMock(spec="WBCabinet")
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


from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    KeywordStat,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting, WBToken


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
def wb_cabinet_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def access_mock(tokens_mock, wb_cabinet_mock):
    from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
    access_mock = MagicMock(spec=WBCabinetAccess)
    access_mock.tokens = tokens_mock
    access_mock.wb_cabinet = wb_cabinet_mock
    return access_mock


@pytest.fixture
def adv_setting_mock():
    adv_setting_mock = MagicMock(spec=AdvSetting)
    adv_setting_mock.adv_id = 25040169
    adv_setting_mock.nmids = [222811118]
    adv_setting_mock.search_adv_id = None
    adv_setting_mock.active_status = "started"
    return adv_setting_mock


@pytest.fixture
def session_mock(): # Удаляем result_mock из аргументов
    session_mock = MagicMock()
    session_mock.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=[]))) # Задаем подходящее значение
    session_mock.commit = AsyncMock(return_value=None)
    return session_mock


@pytest.fixture
def get_async_session_mock(session_mock) -> MagicMock:
    session_maker_mock = MagicMock()
    session_maker_mock.__aenter__ = AsyncMock(return_value=session_mock)
    get_session_maker_mock = MagicMock(return_value=session_maker_mock)
    return get_session_maker_mock


from pytest import fixture


@fixture
def keywords_mocks() -> list[CalculatedKeyword]:
    """Создаёт список тестовых CalculatedKeyword с разными статусами.
    
    Включает:
    - 5 ключевых слов в whitelist (hard_status=2), 1 из них best
    - 2 ключевых слова в blacklist (hard_status=0)
    - 2 ключевых слова в тестировании (hard_status=1)
    """
    from tests.factories.keyword_pipeline import (
        GoodKeywordFactory,
        BadKeywordFactory,
        TestingKeywordFactory,
        BestKeywordFactory,
    )
    
    keywords = []
    # 1 лучшее ключевое слово (whitelist, best_keyword_status=True)
    keywords.append(BestKeywordFactory())
    # 4 хороших ключевых слова (whitelist, best_keyword_status=False)
    keywords.extend(GoodKeywordFactory.create_batch(4, state__best_keyword_status=False))
    # 2 плохих ключевых слова (blacklist)
    keywords.extend(BadKeywordFactory.create_batch(2))
    # 2 в тестировании
    keywords.extend(TestingKeywordFactory.create_batch(2))
    
    return keywords


@pytest.fixture(name='front_too_many_requests_str', scope='function')
async def front_too_many_requests_str() -> AsyncGenerator[str, None]:
    async with aiofiles.open('tests/wb_front_responses/too-many-requests.txt',
                             mode='r',
                             encoding='utf-8') as f:
        content = await f.read()
        yield content




# TODO: Разработать методологию оценки сроков разработки новых фич, багфиксов и рефакторингов, а также стратегии укладывания в сроки.


@pytest.fixture(name="di_container", scope="function")
async def di_container() -> AsyncGenerator["AppContainer", None]:
    from app.core.di.app_container import  AppContainer
    AppContainer.wiring_config = containers.WiringConfiguration()
    container = AppContainer()

    yield container



@pytest.fixture(scope="function")
async def postgres_session(async_engine):
    async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope='function')
async def fake_redis():
    """Создает фейковый Redis для тестов (асинхронная версия)."""
    redis = await fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()  # очищаем после теста
    await redis.close()


from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import ComplexAdv
from tests.factories.complex_adv import create_complex_adv_seed





# TODO: Внедрить исполнителя, который будет тормозить не эффективные РК и запускать потом их снова
# TODO Сделать более информативно какие РК сколько жрут
# TODO: Сделать исполнителя, который будет глушить слова сверху вниз и снизу вверх
# TODO Сделать дашборд по эффективности работы платных клиентов и самому писать им - это будет про-активная поддержка. С сортировкой по эффективности

@pytest.fixture(scope='function')
async def complex_adv(postgres_session: AsyncSession) -> AsyncGenerator[ComplexAdv, None]:
    """Создает полностью связанную структуру ComplexAdv (реальные ORM-объекты)."""

    await postgres_session.begin()
    seed = await create_complex_adv_seed(postgres_session)

    async def get_keywords_func(_: AdvSetting) -> list[CalculatedKeyword]:
        return seed.calculated_keywords

    complex_adv = ComplexAdv(
        shop_id="559785095jljiuilhkh",
        get_keywords_func=get_keywords_func,
        adv_setting=seed.adv_setting,
        search_adv=seed.search_adv,
    )

    yield complex_adv
    await postgres_session.rollback()



@pytest.fixture(scope='function')
def complex_adv_mock():
    mock_adv = MagicMock(spec=ComplexAdv)
    mock_adv.get_keywords = AsyncMock(return_value=[])
    mock_adv.adv_setting = MagicMock()
    mock_adv.adv_setting.adv_id = 99999
    mock_adv.adv_setting.name = "Тестовая РК"
    mock_adv.adv_setting.auto_update_white_list = True
    mock_adv.adv_setting.auto_update_target_place = True
    mock_adv.adv_setting.auto_update_exponent = True
    mock_adv.adv_setting._search_adv = None
    mock_adv.search_adv = None
    mock_adv.shop_id = "test_shop"
    return mock_adv




@pytest.fixture(scope='function')
async def sm_generator(postgres_session):
    class _FakeSessionMaker:
        def __call__(self, *args, **kwargs):
            return self  # имитируем async context
        async def __aenter__(self):
            return postgres_session
        async def __aexit__(self, exc_type, exc, tb):
            pass

    return _FakeSessionMaker()


SYNC_TEST_DB_URL = TEST_DB_URL.replace("postgresql+asyncpg", "postgresql")
SYNC_TEST_ENGINE = create_engine(SYNC_TEST_DB_URL, poolclass=NullPool)


@pytest.fixture(autouse=True)
def clean_db():
    """Синхронно очищает ключевые таблицы до и после каждого теста."""
    with SYNC_TEST_ENGINE.begin() as conn:
        conn.execute(text("TRUNCATE keywordsetting, advsetting RESTART IDENTITY CASCADE"))

    yield

    with SYNC_TEST_ENGINE.begin() as conn:
        conn.execute(text("TRUNCATE keywordsetting, advsetting RESTART IDENTITY CASCADE"))


@pytest.fixture(scope='function')
def main_di_container() -> "AppContainer":
    from app.core.di.app_container import AppContainer
    container = AppContainer()
    return container




@pytest.fixture(scope='function')
def di_containner_for_adv_auto_updater_v2(main_di_container, fake_redis: FakeRedis) -> "AppContainer":
    main_di_container.wiring_config.modules = ['app.core.redis_cache',  # Отключаем автоматическое встраивание зависимостей
                                       "old_modules.setting_auto_updater_v2.adv_control_system."
                                       "executors.target_place_executor.utils",
                                       ]
    main_di_container.redis_client.override(fake_redis)
    return main_di_container


@pytest.fixture(scope="function")
async def clickhouse_client(setup_test_database):
    """
    Создаёт async-клиент ClickHouse.
    Зависит от setup_test_database (который запускает docker-compose).
    """
    host =  "localhost"
    port =  8124
    user = "CLICK_HOUSE_USER"
    password = "password"

    client = await get_async_client(
            host=host,
            port=port,
            username=user,
            password=password,
            database="default_db",
        )


    print("[OK] ClickHouse async client created")

    # Добавим небольшую задержку, чтобы ClickHouse полностью инициализировался
    await asyncio.sleep(5)

    # Создаём таблицы ClickHouse, если их нет
    await client.command("""
        CREATE TABLE IF NOT EXISTS default_db.full_adv_wb_stat (
            adv_id Int32,
            date Date,
            views Int32,
            clicks Int32,
            spend Float64,
            added_to_cart Int32,
            orders Int32,
            sum_price_orders Float64,
            version Float64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, date, version)
    """)

    await client.command("""
        CREATE TABLE IF NOT EXISTS default_db.advkeyword_new (
            adv_id Int32,
            text String,
            date Date,
            clicks_state AggregateFunction(argMax, Int32, Float64),
            views_state AggregateFunction(argMax, Int32, Float64),
            spend_state AggregateFunction(argMax, Float64, Float64),
            version Float64
        ) ENGINE = AggregatingMergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, text, date)
    """)

    await client.command("""
        CREATE TABLE IF NOT EXISTS default_db.clusters_adv_stats (
            adv_id UInt32,
            nmid UInt64,
            wb_category LowCardinality(String),
            norm_query LowCardinality(String),
            views UInt32,
            clicks UInt32,
            ctr Float64,
            cpm Float64,
            add_to_cart UInt32,
            orders UInt32,
            cpc Float64,
            avr_pos Float64,
            date Date,
            timestamp DateTime default now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (wb_category, nmid, norm_query, date, timestamp)
        SETTINGS index_granularity = 8192
    """)

    print("[OK] ClickHouse tables created/checked")

    yield client


    client.close()
    print("[OK] ClickHouse client closed")


@pytest.fixture(scope='function')
def app_container():
    from app.core.di.app_container import AppContainer
    container = AppContainer()
    return container


@pytest.fixture(scope='function')
def bidder_keywords_300() -> list[CalculatedKeyword]:
    from tests.factories.keyword_pipeline import CalculatedKeywordFactory
    return CalculatedKeywordFactory.create_batch(300)