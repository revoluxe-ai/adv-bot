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
from tests.factories import adv_factory
from tests.factories.adv_factory import AdvSettingFactory, KeywordSettingFactory
from app.core.di.app_container import AppContainer

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

from app.modules.common_slaves.wildberries.models import WBCabinet
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
    """Определяет команду для запуска Docker Compose и скипает, если недоступна."""
    cmd = _detect_compose_cmd()
    if not cmd:
        pytest.skip("Docker Compose не найден в системе — скипаем интеграционные тесты БД")
    _DOCKER_CLEANUP_STATE["compose_cmd"] = cmd
    return cmd


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(docker_compose_cmd):
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

    from app.utils.db.base import BaseTable as Base
    from sqlalchemy import create_engine

    print("[MIGRATION] Creating PostgreSQL extensions...")

    # Добавим небольшую задержку перед созданием расширений PostgreSQL
    time.sleep(5)

    # Создаём синхронный движок для создания расширений и таблиц
    sync_engine = create_engine(TEST_DB_URL.replace("postgresql+asyncpg", "postgresql"))

    # Создаём необходимые расширения PostgreSQL ПЕРЕД созданием таблиц
    with sync_engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            conn.commit()
        except Exception as e:
            # Игнорируем ошибку если расширение уже существует (race condition в PostgreSQL)
            if "already exists" in str(e):
                print(f"[INFO] Extension pg_trgm already exists, skipping...")
                conn.rollback()
            else:
                raise

    print("[MIGRATION] Creating tables from models metadata...")
    Base.metadata.create_all(sync_engine)
    
    # Очищаем тестовые таблицы от данных предыдущих запусков
    with sync_engine.connect() as conn:
        conn.execute(text("TRUNCATE keywordsetting, advsetting RESTART IDENTITY CASCADE"))
        conn.commit()
    print("[OK] Test tables truncated.")
    
    sync_engine.dispose()
    print("[OK] Tables created successfully from models metadata.")

    # Проставляем миграции Alembic как применённые
    from alembic.config import Config
    from alembic import command

    print("[MIGRATION] Stamping Alembic migrations for test database...")
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic_")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    command.stamp(alembic_cfg, "head")
    print("[OK] Alembic migrations stamped successfully.")

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
    KeywordStatus,
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
def keywords_mocks() -> list[MagicMock]:
    """
    Фикстура для генерации моков CalculatedKeyword с заданными параметрами
    """
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


@pytest.fixture(name='front_too_many_requests_str', scope='function')
async def front_too_many_requests_str() -> AsyncGenerator[str, None]:
    async with aiofiles.open('tests/wb_front_responses/too-many-requests.txt',
                             mode='r',
                             encoding='utf-8') as f:
        content = await f.read()
        yield content




# TODO: Разработать методологию оценки сроков разработки новых фич, багфиксов и рефакторингов, а также стратегии укладывания в сроки.


@pytest.fixture(name="di_container", scope="function")
async def di_container() -> AsyncGenerator[AppContainer, None]:

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





# TODO: Внедрить исполнителя, который будет тормозить не эффективные РК и запускать потом их снова
# TODO Сделать более информативно какие РК сколько жрут
# TODO: Сделать исполнителя, который будет глушить слова сверху вниз и снизу вверх
# TODO Сделать дашборд по эффективности работы платных клиентов и самому писать им - это будет про-активная поддержка. С сортировкой по эффективности

@pytest.fixture(scope='function')
async def complex_adv(postgres_session: AsyncSession) -> AsyncGenerator[ComplexAdv, None]:
    """Создает полностью связанную структуру ComplexAdv (реальные ORM-объекты)."""

    await postgres_session.begin()
    adv_setting = AdvSettingFactory.build(
        adv_id=123, # Устанавливаем adv_id для консистентности теста
        nmids=[456], # Добавляем nmids
        auto_update_white_list=True,
        auto_update_target_place=True,
        auto_update_exponent=True,
        auto_add_only_relevant_phrase=False,
        bidder_for_auto=True,
        bidder_active=True,
    )
    adv_setting.cpm = 100
    adv_setting.max_cpm = 250
    adv_setting.max_place = 120
    adv_setting.exponent_predict_ctr = 8.0

    search_adv_setting = AdvSettingFactory.build()
    search_adv_setting.cpm = 90
    adv_setting._search_adv = search_adv_setting.adv_id
    postgres_session.add(adv_setting)
    await postgres_session.flush()
    await postgres_session.refresh(adv_setting)
    # 2️⃣ KeywordSettings
    adv_factory.fake.unique.clear()
    keyword_settings = []
    for idx in range(50):
        ks = KeywordSettingFactory.build(adv_setting_id=adv_setting.id)
        if idx < 10:
            ks.hard_status = 2
            ks.relevant = True
        elif idx < 20:
            ks.hard_status = 1
            ks.relevant = True
        else:
            ks.hard_status = 0
            ks.relevant = False
        keyword_settings.append(ks)
    postgres_session.add_all(keyword_settings)
    await postgres_session.flush()
    for ks in keyword_settings:
        await postgres_session.refresh(ks)

    # 3️⃣ CalculatedKeywords
    def _build_keyword(
        ks: KeywordSetting,
        *,
        status: str,
        hard_status: int,
        predict_ctr: float,
        predict_ctr_exponent: float,
        views: int,
        clicks: int,
        spend: float,
        relevant: bool,
        best: bool = False,
    ) -> CalculatedKeyword:
        return CalculatedKeyword(
            keyword_setting_original_id=ks.id,
            text=ks.text,
            clicks=clicks,
            views=views,
            spend=spend,
            baes_ctr=round(predict_ctr * 0.8, 3),
            predict_ctr=predict_ctr,
            predict_ctr_exponent=predict_ctr_exponent,
            status=status,
            hard_status=hard_status,
            relevant=relevant,
            best_keyword_status=best,
        )

    calculated_keywords: list[CalculatedKeyword] = []
    for idx, ks in enumerate(keyword_settings):
        if idx == 0:
            calculated_keywords.append(
                _build_keyword(
                    ks,
                    status=KeywordStatus.GOOD,
                    hard_status=2,
                    predict_ctr=1.5,
                    predict_ctr_exponent=6.0,
                    views=1500,
                    clicks=200,
                    spend=320.0,
                    relevant=True,
                    best=True,
                )
            )
        elif idx < 10:
            calculated_keywords.append(
                _build_keyword(
                    ks,
                    status=KeywordStatus.GOOD,
                    hard_status=2,
                    predict_ctr=1.2,
                    predict_ctr_exponent=5.0,
                    views=1200,
                    clicks=150,
                    spend=210.0,
                    relevant=True,
                )
            )
        elif idx < 15:
            calculated_keywords.append(
                _build_keyword(
                    ks,
                    status=KeywordStatus.BAD,
                    hard_status=1,
                    predict_ctr=0.35,
                    predict_ctr_exponent=4.0,
                    views=800,
                    clicks=40,
                    spend=45.0,
                    relevant=True,
                )
            )
        elif idx < 20:
            calculated_keywords.append(
                _build_keyword(
                    ks,
                    status=KeywordStatus.GOOD,
                    hard_status=1,
                    predict_ctr=1.1,
                    predict_ctr_exponent=4.5,
                    views=1000,
                    clicks=120,
                    spend=160.0,
                    relevant=True,
                )
            )
        else:
            calculated_keywords.append(
                _build_keyword(
                    ks,
                    status=KeywordStatus.BAD,
                    hard_status=0,
                    predict_ctr=0.25,
                    predict_ctr_exponent=3.0,
                    views=600,
                    clicks=30,
                    spend=30.0,
                    relevant=False,
                )
            )

    # 4️⃣ Асинхронный источник данных для ComplexAdv
    async def get_keywords_func(_: AdvSetting) -> list[CalculatedKeyword]:
        return calculated_keywords

    # 5️⃣ Реальный ComplexAdv
    complex_adv = ComplexAdv(
        shop_id='559785095jljiuilhkh',
        adv_setting=adv_setting,
        get_keywords_func=get_keywords_func,
        search_adv=search_adv_setting,
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
def main_di_container() -> AppContainer:

    container = AppContainer()
    return container




@pytest.fixture(scope='function')
def di_containner_for_adv_auto_updater_v2(main_di_container, fake_redis: FakeRedis) -> AppContainer:
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

    print("[OK] ClickHouse tables created/checked")

    yield client


    client.close()
    print("[OK] ClickHouse client closed")


@pytest.fixture(scope='function')
def app_container():
    container = AppContainer()
    return container