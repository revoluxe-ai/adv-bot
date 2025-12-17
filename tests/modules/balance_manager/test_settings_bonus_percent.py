"""Тесты для настройки BALANCE_TOPUP_BONUS_PERCENT."""

import os
from unittest.mock import patch

import pytest

from app.settings.settings_master import Settings


def test_balance_topup_bonus_percent_default():
    """Тест: значение по умолчанию равно 200.0."""
    settings = Settings()

    # Убеждаемся, что переменная окружения не установлена
    with patch.dict(os.environ, {}, clear=True):
        # Удаляем переменную если она была установлена
        if "BALANCE_TOPUP_BONUS_PERCENT" in os.environ:
            del os.environ["BALANCE_TOPUP_BONUS_PERCENT"]

        value = settings.BALANCE_TOPUP_BONUS_PERCENT
        assert value == 200.0, f"Ожидалось значение по умолчанию 200.0, получено {value}"


def test_balance_topup_bonus_percent_from_env():
    """Тест: значение берется из переменной окружения."""
    settings = Settings()

    test_cases = [
        ("100", 100.0),
        ("150", 150.0),
        ("200", 200.0),
        ("250", 250.0),
        ("0", 0.0),
        ("50.5", 50.5),
        ("100.75", 100.75),
    ]

    for env_value, expected_value in test_cases:
        with patch.dict(os.environ, {"BALANCE_TOPUP_BONUS_PERCENT": env_value}):
            value = settings.BALANCE_TOPUP_BONUS_PERCENT
            assert value == expected_value, (
                f"Для env_value={env_value} ожидалось {expected_value}, получено {value}"
            )


def test_balance_topup_bonus_percent_invalid_env_raises_error():
    """Тест: невалидное значение из переменной окружения вызывает ошибку."""
    settings = Settings()

    invalid_values = ["not_a_number", "abc"]

    for invalid_value in invalid_values:
        with patch.dict(os.environ, {"BALANCE_TOPUP_BONUS_PERCENT": invalid_value}):
            with pytest.raises(ValueError):
                _ = settings.BALANCE_TOPUP_BONUS_PERCENT


def test_balance_topup_bonus_percent_negative_allowed():
    """Тест: отрицательные значения из переменной окружения допустимы (валидация в другом месте)."""
    settings = Settings()

    with patch.dict(os.environ, {"BALANCE_TOPUP_BONUS_PERCENT": "-100"}):
        value = settings.BALANCE_TOPUP_BONUS_PERCENT
        assert value == -100.0

