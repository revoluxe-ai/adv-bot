import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager

from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet, WBCabinetAccess
from app.modules.common_slaves.wildberries.models import WBCabinet, WBToken
from app.modules.common_slaves.wildberries.exceptions import WBCabinetNotFoundError
from app.core.wb_api.exceptions import ApiForbiddenError


@pytest.mark.asyncio
async def test_get_access_for_wb_cabinet_by_id():
    """Тестирование получения доступа к кабинету по cabinet_id"""
    
    # Создаем мок кабинета
    mock_cabinet = AsyncMock(spec=WBCabinet)
    mock_cabinet.id = 1
    mock_cabinet.shop_id = '123'
    mock_cabinet.balance = 100.0
    
    # Создаем мок токена с правильным JWT
    mock_token = AsyncMock(spec=WBToken)
    mock_token.api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzaWQiOiIxMjMiLCJleHAiOjE3MzA5NzI4MDB9.dummy"
    mock_token.user_id = 1
    mock_token.active = True
    mock_token.shop_id = '123'
    mock_token.check_valid = AsyncMock(return_value=True)
    
    # Создаем мок сессии
    session_mock = AsyncMock()
    
    # Настраиваем execute для получения кабинета
    cabinet_result = AsyncMock()
    cabinet_result.scalar = AsyncMock(return_value=mock_cabinet)
    session_mock.execute = AsyncMock(return_value=cabinet_result)
    
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
    
    stream_result = AsyncMock()
    stream_result.yield_per.return_value = MockAsyncIterator([mock_token])
    session_mock.stream = AsyncMock(return_value=stream_result)
    
    # Создаем контекстный менеджер
    class MockSessionManager:
        async def __aenter__(self):
            return session_mock
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    # Патчим get_async_session_maker
    with patch('app.modules.common_slaves.wildberries.super_cabinet_manager.sm', 
               return_value=MockSessionManager()):
        
        # Вызываем функцию с числовым cabinet_id
        access = await get_access_for_wb_cabinet(1)
        
        # Проверяем результаты
        assert access is not None
        assert access.wb_cabinet == mock_cabinet
        assert len(access.tokens) == 1
        assert access.tokens[0] == mock_token
        
        # Проверяем, что execute был вызван с правильным запросом
        session_mock.execute.assert_called()
        
        # Проверяем, что stream был вызван для получения токенов
        session_mock.stream.assert_called_once()


@pytest.mark.asyncio
async def test_get_access_for_wb_cabinet_by_shop_id():
    """Тестирование получения доступа к кабинету по shop_id"""
    
    # Создаем мок кабинета
    mock_cabinet = AsyncMock(spec=WBCabinet)
    mock_cabinet.id = 1
    mock_cabinet.shop_id = '123'
    mock_cabinet.balance = 100.0
    
    # Создаем мок токена с правильным JWT
    mock_token = AsyncMock(spec=WBToken)
    mock_token.api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzaWQiOiIxMjMiLCJleHAiOjE3MzA5NzI4MDB9.dummy"
    mock_token.user_id = 1
    mock_token.active = True
    mock_token.shop_id = '123'
    mock_token.check_valid = AsyncMock(return_value=True)
    
    # Создаем мок сессии для первого вызова (поиск cabinet_id)
    session_mock1 = AsyncMock()
    execute_result1 = AsyncMock()
    execute_result1.scalar = AsyncMock(return_value=1)  # ID кабинета
    session_mock1.execute = AsyncMock(return_value=execute_result1)
    
    # Создаем мок сессии для второго вызова (получение кабинета и токенов)
    session_mock2 = AsyncMock()
    execute_result2 = AsyncMock()
    execute_result2.scalar = AsyncMock(return_value=mock_cabinet)
    session_mock2.execute = AsyncMock(return_value=execute_result2)
    
    # Настраиваем stream для токенов
    class MockAsyncIterator:
        def __init__(self, tokens):
            self.tokens = tokens
        
        def yield_per(self, _):
            return self
        
        async def __aiter__(self):
            for token in self.tokens:
                yield (token,)
    
    stream_result = AsyncMock()
    stream_result.yield_per.return_value = MockAsyncIterator([mock_token])
    session_mock2.stream = AsyncMock(return_value=stream_result)
    
    # Создаем контекстный менеджер, который будет возвращать разные моки
    sessions = [session_mock1, session_mock2]
    session_index = 0
    
    class MockSessionManager:
        async def __aenter__(self):
            nonlocal session_index
            current_session = sessions[session_index]
            session_index = (session_index + 1) % len(sessions)
            return current_session
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    # Патчим get_async_session_maker
    with patch('app.modules.common_slaves.wildberries.super_cabinet_manager.sm', 
               return_value=MockSessionManager()):
        # Вызываем функцию со строковым shop_id
        access = await get_access_for_wb_cabinet('123')
        
        # Проверяем результаты
        assert access is not None
        assert access.wb_cabinet == mock_cabinet
        assert len(access.tokens) == 1
        assert access.tokens[0] == mock_token


@pytest.mark.asyncio
async def test_get_access_for_wb_cabinet_no_tokens():
    """Тестирование получения доступа к кабинету без токенов"""
    
    # Создаем мок кабинета
    mock_cabinet = AsyncMock(spec=WBCabinet)
    mock_cabinet.id = 1
    mock_cabinet.shop_id = '123'
    mock_cabinet.balance = 100.0
    
    # Создаем мок сессии
    session_mock = AsyncMock()
    
    # Настраиваем execute для получения кабинета
    execute_result = AsyncMock()
    execute_result.scalar = AsyncMock(return_value=mock_cabinet)
    session_mock.execute = AsyncMock(return_value=execute_result)
    
    # Настраиваем stream для пустого списка токенов
    class MockAsyncIterator:
        def __init__(self, tokens):
            self.tokens = tokens
        
        def yield_per(self, _):
            return self
        
        async def __aiter__(self):
            for token in self.tokens:
                yield (token,)
    
    stream_result = AsyncMock()
    stream_result.yield_per.return_value = MockAsyncIterator([])
    session_mock.stream = AsyncMock(return_value=stream_result)
    
    # Создаем контекстный менеджер
    class MockSessionManager:
        async def __aenter__(self):
            return session_mock
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    # Патчим get_async_session_maker
    with patch('app.modules.common_slaves.wildberries.super_cabinet_manager.sm',
               return_value=MockSessionManager()):
        # Вызываем функцию и ожидаем исключение
        with pytest.raises(ApiForbiddenError):
            await get_access_for_wb_cabinet(1)


@pytest.mark.asyncio
async def test_get_access_for_nonexistent_cabinet():
    """Тестирование получения доступа к несуществующему кабинету"""
    
    # Создаем мок сессии
    session_mock = AsyncMock()
    
    # Настраиваем execute для возврата None (кабинет не найден)
    execute_result = AsyncMock()
    execute_result.scalar = AsyncMock(return_value=None)
    session_mock.execute = AsyncMock(return_value=execute_result)
    
    # Создаем контекстный менеджер
    class MockSessionManager:
        async def __aenter__(self):
            return session_mock
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    # Патчим get_async_session_maker
    with patch('app.modules.common_slaves.wildberries.super_cabinet_manager.sm',
               return_value=MockSessionManager()):
        # Вызываем функцию и ожидаем исключение
        with pytest.raises(WBCabinetNotFoundError):
            await get_access_for_wb_cabinet(1) 