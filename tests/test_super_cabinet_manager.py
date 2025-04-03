import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
from app.modules.common_slaves.wildberries.models import WBCabinet, WBToken
from contextlib import asynccontextmanager

@pytest.mark.asyncio
async def test_get_access_for_wb_cabinet():
    """Тестирование функции получения доступа к кабинету с учетом балансов и бонусов"""
    
    # Создаем мок кабинета
    mock_cabinet = MagicMock(spec=WBCabinet)
    mock_cabinet.id = 1
    mock_cabinet.shop_id = "123"
    mock_cabinet.balance = 100.0
    mock_cabinet.bonus = 50.0

    # Создаем мок токена
    mock_token = MagicMock(spec=WBToken)
    mock_token.api_key = "test_api_key"
    mock_token.active = True
    mock_token.user_id = 1
    mock_token.shop_id = "123"
    mock_token.check_valid = MagicMock(return_value=True)

    # Создаем мок для сессии
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    
    # Настраиваем execute для получения кабинета
    cabinet_result = MagicMock()
    cabinet_result.scalar = MagicMock(return_value=mock_cabinet)
    mock_session.execute = AsyncMock(return_value=cabinet_result)
    
    # Настраиваем stream для токенов
    class MockAsyncIterator:
        def __init__(self, tokens):
            self.tokens = tokens
            self._index = 0
        
        def yield_per(self, _):
            return self
        
        async def __aiter__(self):
            for token in self.tokens:
                yield (token,)
    
    stream_result = MockAsyncIterator([mock_token])
    mock_session.stream = AsyncMock(return_value=stream_result)
    
    # Патчим функцию sm для возврата нашего мока сессии
    with patch('app.modules.common_slaves.wildberries.super_cabinet_manager.sm', return_value=mock_session):
        # Вызываем тестируемую функцию
        result = await get_access_for_wb_cabinet("123")
        
        # Проверяем результат
        assert result.wb_cabinet == mock_cabinet
        assert len(result.tokens) == 1
        assert result.tokens[0] == mock_token
        mock_session.execute.assert_called()
        mock_session.stream.assert_called_once() 