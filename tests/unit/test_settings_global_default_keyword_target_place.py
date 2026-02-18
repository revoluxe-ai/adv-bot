"""Tests for GLOBAL_DEFAULT_KEYWORD_TARGET_PLACE setting."""

from unittest.mock import patch

import pytest

from app.settings.settings_master import settings


@pytest.mark.unit
def test_global_default_keyword_target_place_zero_env_returns_two():
    """When GLOBAL_DEFAULT_KEYWORD_TARGET_PLACE env is 0 or negative, setting returns 2."""
    with patch("app.settings.settings_master.os.getenv") as mock_getenv:
        mock_getenv.return_value = "0"
        assert settings.GLOBAL_DEFAULT_KEYWORD_TARGET_PLACE == 2


@pytest.mark.unit
def test_global_default_keyword_target_place_negative_env_returns_two():
    """When GLOBAL_DEFAULT_KEYWORD_TARGET_PLACE env is negative, setting returns 2."""
    with patch("app.settings.settings_master.os.getenv") as mock_getenv:
        mock_getenv.return_value = "-1"
        assert settings.GLOBAL_DEFAULT_KEYWORD_TARGET_PLACE == 2


@pytest.mark.unit
def test_global_default_keyword_target_place_positive_env_returns_value():
    """When GLOBAL_DEFAULT_KEYWORD_TARGET_PLACE env is positive, setting returns that value."""
    with patch("app.settings.settings_master.os.getenv") as mock_getenv:
        mock_getenv.return_value = "5"
        assert settings.GLOBAL_DEFAULT_KEYWORD_TARGET_PLACE == 5
