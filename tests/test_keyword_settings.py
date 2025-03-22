import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import KeywordStatus

@pytest.mark.asyncio
async def test_keyword_white_list_filter():
    # Создаем тестовые данные
    keyword1 = MagicMock()
    keyword1.keyword_setting.hard_status = 1
    keyword1.status = KeywordStatus.BAD
    keyword1.reason = "max_position"
    keyword1.text = "test1"
    
    keyword2 = MagicMock()
    keyword2.keyword_setting.hard_status = 1
    keyword2.status = KeywordStatus.BAD
    keyword2.reason = "other_reason"
    keyword2.text = "test2"
    
    keyword3 = MagicMock()
    keyword3.keyword_setting.hard_status = 0
    keyword3.status = KeywordStatus.BAD
    keyword3.reason = "max_position"
    keyword3.text = "test3"
    
    keywords = [keyword1, keyword2, keyword3]
    
    # Фильтруем ключевые слова
    filtered_keywords = [keyword for keyword in keywords 
                        if keyword.keyword_setting.hard_status == 1 
                        and keyword.status == KeywordStatus.BAD 
                        and keyword.reason == "max_position"]
    
    # Проверяем результат
    assert len(filtered_keywords) == 1
    assert filtered_keywords[0].text == "test1" 