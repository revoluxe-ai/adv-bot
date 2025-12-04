"""Conftest для unit-тестов calculated_keywords_manager.

Эти тесты не требуют базы данных, поэтому переопределяем фикстуры из корневого conftest.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Переопределяем фикстуру из корневого conftest - unit-тесты не требуют БД."""
    yield


@pytest.fixture(autouse=True)
def clean_db():
    """Переопределяем фикстуру clean_db - unit-тесты не требуют БД."""
    yield

