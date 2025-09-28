"""Configuration for token monitoring tests to handle bot initialization issues."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True, scope="session")
def mock_bot_initialization():
    """Auto-mock bot initialization for all tests to prevent token validation errors."""
    with patch('app.client_bot.bot.Bot') as mock_bot_class:
        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance
        
        with patch('app.settings.settings.BOT_TOKEN', 'test_token_for_testing'):
            yield mock_bot_instance


@pytest.fixture(autouse=True, scope="session") 
def mock_environment_settings():
    """Mock environment settings to prevent import issues."""
    with patch.dict('os.environ', {
        'BOT_TOKEN': 'test_token_for_testing',
        'DATABASE_URL': 'sqlite:///:memory:',
        'REDIS_URL': 'redis://localhost:6379'
    }):
        yield