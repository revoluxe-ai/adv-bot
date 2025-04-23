import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.modules.calculated_keywords_redis_cache_manager.redis_manager import RedisCalculatedKeywordsCacheManager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword

class AsyncContextManagerMock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture
def redis_manager():
    with patch('app.core.redis_manager.RedisManager.__init__', return_value=None):
        manager = RedisCalculatedKeywordsCacheManager()
        pipe_mock = AsyncMock()
        pipe_mock.hset = AsyncMock()
        pipe_mock.execute = AsyncMock()
        
        manager._client = AsyncMock()
        manager._client.pipeline = MagicMock()
        manager._client.pipeline.return_value = AsyncMock()
        manager._client.pipeline.return_value.__aenter__ = AsyncMock(return_value=pipe_mock)
        manager._client.pipeline.return_value.__aexit__ = AsyncMock()
        return manager


@pytest.fixture
def sample_keyword():
    return CalculatedKeyword(
        text="test_keyword",
        adv_id=1,
        clicks=1,
        views=1000,
        spend=100
    )

@pytest.mark.asyncio
async def test_set_calculated_keywords(redis_manager, sample_keyword):
    # Arrange
    keywords = [sample_keyword]
    adv_id = 1
    
    # Act
    await redis_manager.set_calculated_keywords(keywords, adv_id)
    
    # Assert
    redis_manager._client.pipeline.assert_called_once()
    pipe = redis_manager._client.pipeline.return_value.__aenter__.return_value
    pipe.hset.assert_called_once_with(
        name=f"calculated_keywords:{adv_id}",
        key=sample_keyword.text,
        value=sample_keyword.to_json()
    )

@pytest.mark.asyncio
async def test_get_calculated_keyword(redis_manager, sample_keyword):
    # Arrange
    adv_id = 1
    keyword_text = "test_keyword"
    redis_manager._client.hget.return_value = sample_keyword.to_json()
    
    # Act
    result = await redis_manager.get_calculated_keyword(adv_id, keyword_text)
    
    # Assert
    assert result is not None
    assert result.text == sample_keyword.text
    redis_manager._client.hget.assert_called_once_with(
        name=f"calculated_keywords:{adv_id}",
        key=keyword_text
    )

@pytest.mark.asyncio
async def test_get_calculated_keyword_not_found(redis_manager):
    # Arrange
    adv_id = 1
    keyword_text = "non_existent_keyword"
    redis_manager._client.hget.return_value = None
    
    # Act
    result = await redis_manager.get_calculated_keyword(adv_id, keyword_text)
    
    # Assert
    assert result is None
    redis_manager._client.hget.assert_called_once_with(
        name=f"calculated_keywords:{adv_id}",
        key=keyword_text
    )

@pytest.mark.asyncio
async def test_get_calculated_keywords(redis_manager, sample_keyword):
    # Arrange
    keywords = [sample_keyword]
    redis_manager._client.pipeline.return_value.__aenter__.return_value.execute.return_value = [
        sample_keyword.to_json()
    ]
    
    # Act
    result = await redis_manager.get_calculated_keywords(keywords)
    
    # Assert
    assert len(result) == 1
    assert result[0].text == sample_keyword.text
    pipe = redis_manager._client.pipeline.return_value.__aenter__.return_value
    pipe.hget.assert_called_once_with(
        name=f"calculated_keywords:{sample_keyword.adv_id}",
        key=sample_keyword.text
    ) 