from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.modules.common_slaves.wildberries.exceptions import WBCabinetNotFoundError
from contextlib import asynccontextmanager


@pytest.mark.asyncio
async def test_get_access_nonexistent_cabinet():
    """Тестирует случай, когда кабинет не найден"""
    
    # Моки для сессии
    mock_session = AsyncMock()
    
    # Результат запроса - кабинет не найден
    mock_execute_result = MagicMock()
    mock_execute_result.scalar.return_value = None
    
    # Настраиваем execute сессии
    mock_session.execute.return_value = mock_execute_result
    
    # Настраиваем контекстный менеджер
    @asynccontextmanager
    async def mock_session_manager():
        yield mock_session
    
    # Патчим get_async_session_maker
    with patch('app.modules.common_slaves.wildberries.super_cabinet_manager.get_async_session_maker', 
               new=mock_session_manager):
        # Проверяем, что функция выбрасывает исключение
        with pytest.raises(WBCabinetNotFoundError) as exc_info:
            await get_access_for_wb_cabinet('nonexistent_shop_id')
        
        # Проверяем сообщение об ошибке
        assert str(exc_info.value) == "Кабинет не найден (по shop_id: nonexistent_shop_id)" 