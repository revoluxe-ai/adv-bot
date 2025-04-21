import math
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.my_types import AdvSetting
from app.modules.wb_adv_updater import data_manager

@pytest.fixture
def sample_keyword():
    return CalculatedKeyword(
        text="test keyword",
        clicks=10,
        views=100,
        spend=1000.0,
        predict_ctr=0.15,
        status=KeywordStatus.GOOD,
        base_position=5,
        predict_ctr_exponent=1.5
    )

@pytest.fixture
def sample_adv_setting():
    adv = AdvSetting()
    adv.id = 1
    adv.adv_id = 123
    adv.updated_at = datetime.now()
    adv.exponent_predict_ctr = 1.5
    return adv

@pytest.mark.asyncio
async def test_calculated_keyword_serialization(sample_keyword):
    """Тест сериализации/десериализации CalculatedKeyword"""
    # Сериализуем в JSON
    json_data = sample_keyword.model_dump_json()
    
    # Десериализуем обратно
    restored = CalculatedKeyword.model_validate_json(json_data)
    
    # Проверяем основные поля
    assert restored.text == sample_keyword.text
    assert restored.clicks == sample_keyword.clicks
    assert restored.views == sample_keyword.views
    assert restored.spend == sample_keyword.spend
    assert restored.predict_ctr == sample_keyword.predict_ctr
    assert restored.status == sample_keyword.status
    assert restored.base_position == sample_keyword.base_position
    assert restored.predict_ctr_exponent == sample_keyword.predict_ctr_exponent

@pytest.mark.asyncio
async def test_keyword_caching(sample_keyword, sample_adv_setting):
    """Тест кеширования отдельных ключевых слов"""
    # Подготавливаем моки для redis
    with patch('app.utils.redis_manager.get', new_callable=AsyncMock) as mock_redis_get:
        # Настраиваем поведение mock_redis_get
        mock_redis_get.return_value = sample_keyword.model_dump_json()
        
        # Кешируем ключевое слово
        cache_key = f"good_bad_phrases:{sample_adv_setting.id}:{sample_adv_setting.updated_at.timestamp()}:{sample_keyword.text}"
        await data_manager.get_cached_keyword(sample_adv_setting, sample_keyword.text)
        
        # Проверяем, что redis.get был вызван с правильными параметрами
        mock_redis_get.assert_called_once_with(cache_key)

@pytest.mark.asyncio
async def test_get_good_bad_phrases_caching(sample_adv_setting):
    """Тест кеширования результатов get_good_bad_phrases"""
    # Создаем тестовые данные
    keywords = [
        CalculatedKeyword(
            text=f"keyword_{i}",
            clicks=10,
            views=100,
            spend=1000.0,
            predict_ctr=0.15,
            status=KeywordStatus.GOOD,
            base_position=5,
            predict_ctr_exponent=1.5
        ) for i in range(3)
    ]
    
    # Подготавливаем моки
    with patch('app.modules.wb_adv_updater.data_manager.get_keywords_statistic_clickhouse') as mock_get_stats, \
         patch('app.utils.redis_manager.set', new_callable=AsyncMock) as mock_redis_set:
        
        mock_get_stats.return_value = keywords
        
        # Вызываем тестируемую функцию
        result = await data_manager.get_good_bad_phrases(sample_adv_setting)
        
        # Проверяем, что каждое ключевое слово было закешировано
        assert mock_redis_set.call_count == len(keywords)
        
        # Проверяем результаты
        assert len(result) == len(keywords)
        for kw in result:
            assert isinstance(kw, CalculatedKeyword)
            assert kw.predict_ctr_exponent == sample_adv_setting.exponent_predict_ctr

@pytest.mark.asyncio
async def test_cache_invalidation(sample_adv_setting, sample_keyword):
    """Тест инвалидации кеша при изменении updated_at"""
    # Изменяем updated_at
    old_updated_at = sample_adv_setting.updated_at
    sample_adv_setting.updated_at = datetime.now() + timedelta(hours=1)
    
    # Подготавливаем моки для redis
    with patch('app.utils.redis_manager.get', new_callable=AsyncMock) as mock_redis_get:
        mock_redis_get.return_value = None  # Симулируем отсутствие данных в кеше
        
        # Пытаемся получить закешированное значение
        cached_kw = await data_manager.get_cached_keyword(sample_adv_setting, sample_keyword.text)
        
        # Проверяем, что значение не найдено в кеше
        assert cached_kw is None
        
        # Проверяем, что был использован новый ключ кеша
        cache_key = f"good_bad_phrases:{sample_adv_setting.id}:{sample_adv_setting.updated_at.timestamp()}:{sample_keyword.text}"
        mock_redis_get.assert_called_once_with(cache_key)

@pytest.mark.asyncio
async def test_keyword_rating_calculation(sample_keyword):
    """Тест расчета рейтинга ключевых слов"""
    # Устанавливаем необходимые параметры
    sample_keyword.views = 1000
    sample_keyword.predict_ctr = 0.15
    sample_keyword.base_position = 5
    sample_keyword.predict_ctr_exponent = 1.5
    
    # Рассчитываем ожидаемый рейтинг
    expected_rating = (0.15 ** 1.5) * 1000 / (1 * math.log(1 + 5))
    
    # Проверяем расчет рейтинга
    assert abs(sample_keyword.rating_by_predict_ctr - expected_rating) < 0.0001

@pytest.mark.asyncio
async def test_sorting_by_rating(sample_adv_setting):
    """Тест сортировки ключевых слов по рейтингу"""
    # Создаем тестовые данные с разными рейтингами
    keywords = [
        CalculatedKeyword(
            text=f"keyword_{i}",
            clicks=10,
            views=100 * (i + 1),
            spend=1000.0,
            predict_ctr=0.1 * (i + 1),
            base_position=5,
            predict_ctr_exponent=1.5,
            status=KeywordStatus.GOOD
        ) for i in range(3)
    ]
    
    # Подготавливаем моки
    with patch('app.modules.wb_adv_updater.data_manager.get_keywords_statistic_clickhouse') as mock_get_stats:
        mock_get_stats.return_value = keywords
        
        # Получаем отсортированные результаты
        result = await data_manager.get_good_bad_phrases(sample_adv_setting)
        
        # Проверяем сортировку
        ratings = [kw.rating_by_predict_ctr for kw in result]
        assert ratings == sorted(ratings, reverse=True) 