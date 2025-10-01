import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Подставляем заглушку для app.core.wb_api.http_request до реальных импортов
import types
# Устанавливаем безопасные значения переменных окружения, чтобы импорты настроек не падали
os.environ.setdefault("TELEGRAM_WEB_PORT", "8080")
os.environ.setdefault("MIN_SUM", "0")
os.environ.setdefault("BIDDER_STEP_RUB", "1")
# Базовые настройки БД/Redis/ClickHouse, чтобы импорты не падали при коллекции тестов
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DBNAME", "test")
os.environ.setdefault("POSTGRES_MASTER_HOST", "localhost")
os.environ.setdefault("POSTGRES_REPLICA_HOST", "localhost")
os.environ.setdefault("CLICK_HOUSE_HOST", "localhost")
os.environ.setdefault("CLICKHOUSE_PORT", "9000")
os.environ.setdefault("CLICKHOUSE_USER", "default")
os.environ.setdefault("CLICKHOUSE_PASSWORD", "pass")
# Also set the variant with underscore used by settings_master
os.environ.setdefault("CLICK_HOUSE_USER", "default")
os.environ.setdefault("CLICK_HOUSE_PASSWORD", "pass")
os.environ.setdefault("REDIS_MASTER_HOST", "localhost")
os.environ.setdefault("REDIS_REPLICA_HOST", "localhost")
os.environ.setdefault("YOOKASSA_TOKEN", "token")
os.environ.setdefault("WEBHOOK_SECRET", "secret")
os.environ.setdefault("CH_MAX_THREAD", "10")
# Ensure a minimal 'dotenv' is available during tests to avoid import errors
if 'dotenv' not in sys.modules:
    dotenv_stub = types.ModuleType('dotenv')
    def _load_dotenv():
        return None
    def dotenv_values(path=None, **kwargs):
        return {}
    dotenv_stub.load_dotenv = _load_dotenv
    dotenv_stub.dotenv_values = dotenv_values
    sys.modules['dotenv'] = dotenv_stub

mod_name = 'app.core.wb_api.http_request'
import importlib
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
        setattr(m, 'try_except_decorator', _try_except_decorator_stub)
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
    return adv_setting_mock


@pytest.fixture
def session_mock(result_mock):
    session_mock = MagicMock()
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_mock.commit = AsyncMock()
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
