import pytest
from unittest.mock import AsyncMock, patch
from app.modules.shop_runner.service_manager.services.delete_keywords_from_wl_by_mean_auto_ctr_manager.delete_keywords_from_wl_by_mean_auto_ctr_manager import delete_keywords_from_wl_by_mean_auto_ctr
from tests.factories.keyword_pipeline import KeywordFactory # Предполагаемая фабрика

@pytest.mark.asyncio
async def test_delete_keywords_from_wl_by_mean_auto_ctr_removes_matching_keywords():
    # Arrange
    shop_id = 123
    mean_ctr = 0.5

    # Ключевые слова для удаления (из белого списка)
    keyword_to_delete_1 = KeywordFactory(
        shop_id=shop_id,
        hard_status=2,
        predict_ctr=0.4,
        mean_ctr=mean_ctr,
        keyword="удаляемое слово 1",
        id="id1"
    )
    keyword_to_delete_2 = KeywordFactory(
        shop_id=shop_id,
        hard_status=2,
        predict_ctr=0.5,
        mean_ctr=mean_ctr,
        keyword="удаляемое слово 2",
        id="id2"
    )

    # Ключевые слова, которые не должны быть удалены (predict_ctr > mean_ctr)
    keyword_to_keep_1 = KeywordFactory(
        shop_id=shop_id,
        hard_status=2,
        predict_ctr=0.6,
        mean_ctr=mean_ctr,
        keyword="сохраняемое слово 1",
        id="id3"
    )
    # Ключевые слова, которые не должны быть удалены (hard_status != 2 - не в белом списке)
    keyword_to_keep_2 = KeywordFactory(
        shop_id=shop_id,
        hard_status=1,
        predict_ctr=0.4,
        mean_ctr=mean_ctr,
        keyword="сохраняемое слово 2",
        id="id4"
    )

    all_keywords_in_db = [
        keyword_to_delete_1,
        keyword_to_delete_2,
        keyword_to_keep_1,
        keyword_to_keep_2
    ]

    # Мокируем зависимости
    with patch("app.modules.shop_runner.service_manager.services.delete_keywords_from_wl_by_mean_auto_ctr_manager.delete_keywords_from_wl_by_mean_auto_ctr_manager.KeywordManager", new_callable=AsyncMock) as MockKeywordManager:
        mock_keyword_manager_instance = MockKeywordManager.return_value
        mock_keyword_manager_instance.get_white_list_keywords_by_shop_id.return_value = all_keywords_in_db
        mock_keyword_manager_instance.delete_white_list_keywords.return_value = None

        # Act
        await delete_keywords_from_wl_by_mean_auto_ctr(shop_id, mean_ctr)

        # Assert
        delete_calls = mock_keyword_manager_instance.delete_white_list_keywords.call_args_list
        assert mock_keyword_manager_instance.delete_white_list_keywords.called

        deleted_keywords_ids = {call.args[0] for call in delete_calls if call.args}
        expected_deleted_ids = {
            keyword_to_delete_1.id,
            keyword_to_delete_2.id
        }
        assert deleted_keywords_ids == expected_deleted_ids

        mock_keyword_manager_instance.get_white_list_keywords_by_shop_id.assert_called_once_with(shop_id)

@pytest.mark.asyncio
async def test_delete_keywords_from_wl_by_mean_auto_ctr_no_keywords():
    # Arrange
    shop_id = 123
    mean_ctr = 0.5

    with patch("app.modules.shop_runner.service_manager.services.delete_keywords_from_wl_by_mean_auto_ctr_manager.delete_keywords_from_wl_by_mean_auto_ctr_manager.KeywordManager", new_callable=AsyncMock) as MockKeywordManager:
        mock_keyword_manager_instance = MockKeywordManager.return_value
        mock_keyword_manager_instance.get_white_list_keywords_by_shop_id.return_value = [] # Нет ключей
        mock_keyword_manager_instance.delete_white_list_keywords.return_value = None

        # Act
        await delete_keywords_from_wl_by_mean_auto_ctr(shop_id, mean_ctr)

        # Assert
        mock_keyword_manager_instance.get_white_list_keywords_by_shop_id.assert_called_once_with(shop_id)
        mock_keyword_manager_instance.delete_white_list_keywords.assert_not_called() # Не должно быть вызовов удаления

@pytest.mark.asyncio
async def test_delete_keywords_from_wl_by_mean_auto_ctr_no_matching_keywords_to_delete():
    # Arrange
    shop_id = 123
    mean_ctr = 0.5

    # Ключевые слова, которые не должны быть удалены (predict_ctr > mean_ctr или hard_status != 2)
    keyword_to_keep_1 = KeywordFactory(
        shop_id=shop_id,
        hard_status=2,
        predict_ctr=0.6,
        mean_ctr=mean_ctr,
        keyword="сохраняемое слово 1",
        id="id5"
    )
    keyword_to_keep_2 = KeywordFactory(
        shop_id=shop_id,
        hard_status=1,
        predict_ctr=0.4,
        mean_ctr=mean_ctr,
        keyword="сохраняемое слово 2",
        id="id6"
    )

    all_keywords_in_db = [
        keyword_to_keep_1,
        keyword_to_keep_2
    ]

    with patch("app.modules.shop_runner.service_manager.services.delete_keywords_from_wl_by_mean_auto_ctr_manager.delete_keywords_from_wl_by_mean_auto_ctr_manager.KeywordManager", new_callable=AsyncMock) as MockKeywordManager:
        mock_keyword_manager_instance = MockKeywordManager.return_value
        mock_keyword_manager_instance.get_white_list_keywords_by_shop_id.return_value = all_keywords_in_db
        mock_keyword_manager_instance.delete_white_list_keywords.return_value = None

        # Act
        await delete_keywords_from_wl_by_mean_auto_ctr(shop_id, mean_ctr)

        # Assert
        mock_keyword_manager_instance.get_white_list_keywords_by_shop_id.assert_called_once_with(shop_id)
        mock_keyword_manager_instance.delete_white_list_keywords.assert_not_called() # Не должно быть вызовов удаления
