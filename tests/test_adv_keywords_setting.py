import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.client_bot.user_interface.views.messages import AdvKeywordsSetting
from aiogram import Bot
from datetime import datetime

@pytest.mark.asyncio
async def test_adv_keywords_setting_init():
    """Тест инициализации класса AdvKeywordsSetting"""
    # Создаем моки
    bot_mock = MagicMock(spec=Bot)
    chat_id = 123456
    keywords = []
    adv_setting = MagicMock()
    adv_setting.name = "Test Campaign"
    adv_setting.active_status = "Active"
    adv_setting.bot_active = True
    adv_setting.adv_id = 1001
    adv_setting.search_adv_id = 1002
    wb_user_cabinet_original_id = 1
    adv_choice_last_page = 1
    image = "test_image.jpg"
    page = 1
    
    # Создаем экземпляр класса
    adv_keywords_setting = AdvKeywordsSetting(
        bot_mock, 
        chat_id, 
        keywords, 
        adv_setting, 
        wb_user_cabinet_original_id, 
        adv_choice_last_page, 
        image, 
        page
    )
    
    # Проверяем, что все атрибуты установлены правильно
    assert adv_keywords_setting._keywords == keywords
    assert adv_keywords_setting._adv_setting == adv_setting
    assert adv_keywords_setting._page == page
    assert adv_keywords_setting._wb_user_cabinet_original_id == wb_user_cabinet_original_id
    assert adv_keywords_setting._adv_choice_last_page == adv_choice_last_page
    assert adv_keywords_setting._image == image
    assert adv_keywords_setting._filter is False
    assert adv_keywords_setting._on_page == 24

@pytest.mark.asyncio
async def test_adv_keywords_setting_basic_text():
    """Тест базовой информации в текстовом представлении"""
    # Создаем моки
    bot_mock = MagicMock(spec=Bot)
    chat_id = 123456
    keywords = []
    adv_setting = MagicMock()
    adv_setting.name = "Test Campaign"
    adv_setting.active_status = "Active"
    adv_setting.bot_active = True
    adv_setting.adv_id = 1001
    adv_setting.search_adv_id = 1002
    adv_setting.exponent_predict_ctr = 1.5
    adv_setting.cpm = 100
    wb_user_cabinet_original_id = 1
    adv_choice_last_page = 1
    image = "test_image.jpg"
    page = 1
    
    # Мокаем методы
    with patch('app.client_bot.user_interface.views.messages.AdvKeywordsSetting._set_statistics', 
               new_callable=AsyncMock) as mock_set_statistics:
        # Устанавливаем необходимые атрибуты для работы property text
        adv_keywords_setting = AdvKeywordsSetting(
            bot_mock, chat_id, keywords, adv_setting, 
            wb_user_cabinet_original_id, adv_choice_last_page, image, page
        )
        adv_keywords_setting.min_ctr = 0.05
        adv_keywords_setting.total_spend = 100.0
        adv_keywords_setting.addition_spend_in_adv = 50.0
        adv_keywords_setting._all_orders_for_last_3_days = 10
        adv_keywords_setting.auto_cpm = 100
        adv_keywords_setting.auction_cpm = 150
        adv_keywords_setting._spend_for_inner_adv_for_3_days = 200.0
        adv_keywords_setting._mean_orders_for_3_days = 3.33  # 10 заказов за 3 дня = 3.33 в день
        
        # Получаем текст
        text = adv_keywords_setting.text
        
        # Проверяем, что текст содержит основную информацию
        assert "Test Campaign" in text
        assert "Active" in text
        assert "1001" in text
        assert "1002" in text
        assert "5.00%" in text  # min_ctr в процентах
        assert "100.00" in text  # total_spend 