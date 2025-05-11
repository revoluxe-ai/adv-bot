import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

from app.modules.common_slaves.wildberries.models import WBToken, AdvSetting
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
def access_mock(tokens_mock):
    access_mock = MagicMock(spec=WBCabinetAccess)
    access_mock.tokens = tokens_mock
    return access_mock


@pytest.fixture
def adv_setting_mock():
    adv_setting_mock = MagicMock(spec=AdvSetting)
    adv_setting_mock.max_pay_for_order = 300
    adv_setting_mock.adv_id = 25040169
    adv_setting_mock.nmids = [222811118]
    return adv_setting_mock


@pytest.fixture
def get_async_session_mock():
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = "Юбки"
    session_mock = MagicMock()
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_maker_mock = MagicMock()
    session_maker_mock.__aenter__ = AsyncMock(return_value=session_mock)

    get_session_maker_mock = MagicMock(return_value=session_maker_mock)
    return get_session_maker_mock
