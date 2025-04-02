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
    mock_token.api_key = "test_key"
    mock_token.shop_id = "123"
    mock_token.check_valid = MagicMock(return_value=True)

    # Моки для сессии
    mock_session = AsyncMock()
    
    # Настраиваем результаты запросов
    mock_cabinet_result = AsyncMock()
    mock_cabinet_result.scalar = AsyncMock(return_value=1)  # ID кабинета
    
    mock_cabinet_get_result = AsyncMock()
    mock_cabinet_get_result.scalar = AsyncMock(return_value=mock_cabinet)  # Сам кабинет
    
    # Создаем асинхронный итератор для токенов
    class MockAsyncIterator:
        def __init__(self, tokens):
            self.tokens = tokens
            self.index = 0
            
        def __aiter__(self):
            return self
            
        async def __anext__(self):
            if self.index >= len(self.tokens):
                raise StopAsyncIteration
            token = self.tokens[self.index]
            self.index += 1
            return [token]
    
    mock_token_result = AsyncMock()
    mock_token_result.yield_per = MagicMock(return_value=MockAsyncIterator([mock_token]))
    
    # Настраиваем execute и stream сессии
    mock_session.execute = AsyncMock()
    mock_session.execute.side_effect = [mock_cabinet_result, mock_cabinet_get_result]
    mock_session.stream = AsyncMock(return_value=mock_token_result)
    
    # Настраиваем контекстный менеджер
    @asynccontextmanager
    async def mock_session_manager():
        yield mock_session
    
    # Патчим get_async_session_maker
    with patch('app.modules.common_slaves.wildberries.super_cabinet_manager.get_async_session_maker', 
               new=mock_session_manager):
        # Получаем доступ к кабинету
        access = await get_access_for_wb_cabinet("123")
        
        # Проверяем результаты
        assert access is not None
        assert access.wb_cabinet.shop_id == "123"
        assert access.tokens and len(access.tokens) > 0
        assert access.tokens[0].api_key == "test_key"
        
        # Проверяем, что методы сессии были вызваны правильно
        assert mock_session.execute.call_count == 2
        assert mock_session.stream.call_count == 1 