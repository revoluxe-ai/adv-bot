import pandas as pd
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.utils.NeoDataScience.driver import DataScience
from app.keyword_async_ml_updater.ML import DataGetter, Fitter
from app.modules.keyword_async_ml_updater.data_managers import get_category_name_min_ctr_final_data
from app.modules.keyword_async_ml_updater import data_managers
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
@patch('neo4j.AsyncGraphDatabase.driver', new_callable=AsyncMock)
async def test_get_nmid_vectors(mock_driver):
    # Создаем асинхронный мок для сессии и транзакции
    mock_session = AsyncMock()
    mock_transaction = AsyncMock()
    mock_transaction.run.return_value.data.return_value = [
        {'nmid': 1, 'vector': [1.0, 2.0, 3.0]},
        {'nmid': 2, 'vector': [4.0, 5.0, 6.0]},
        {'nmid': 3, 'vector': None}
    ]

    mock_session.read_transaction.return_value = mock_transaction

    # Конфигурируем мокирование асинхронного контекстного менеджера для driver
    mock_driver.return_value.__aenter__.return_value = mock_session
    mock_driver.return_value.__aexit__ = AsyncMock()  # Добавляем мок для __aexit__

    # Инициализация экземпляра вашего класса и вызов тестируемой функции
    your_instance = DataScience()  # Замените ... на необходимые аргументы
    result = await your_instance.get_nmid_vectors()

    # Проверки результатов
    assert len(result) > 0  # или другие проверки в зависимости от ожидаемого результата


@pytest.mark.asyncio
async def test_get_nmid_vectors():
    # Initialize the DataScience instance
    ds_instance = DataScience()

    # Call the method
    result = await ds_instance.get_nmid_vectors()

    # Assert the result
    assert isinstance(result, list), "Result should be a list"
    assert len(result) > 0, "Result list should not be empty"
    for item in result:
        assert isinstance(item, tuple), "Each item in the result should be a tuple"
        assert len(item) == 2, "Each tuple should have 2 elements"
        assert isinstance(item[0], int), "The first element of the tuple should be an integer (nmid)"
        assert isinstance(item[1], list), "The second element of the tuple should be a list (vector)"
        assert all(isinstance(i, float) for i in item[1]), "The vector should be a list of floats"



@patch('sqlalchemy.ext.asyncio.create_async_session', new_callable=AsyncMock)
async def test___get_df_for_fit(mock_session):
    # Подготовка мокированных данных для возвращения
    mock_adv_settings = AsyncMock()
    mock_adv_settings.scalars.return_value.unique.return_value.all.return_value = [
        MagicMock(adv_id=1, nmids=[101, 102], adv_keywords=[
            MagicMock(text='keyword1', views=100, clicks=10, spend=5.0, real_ctr=0.1),
            MagicMock(text='keyword2', views=200, clicks=20, spend=10.0, real_ctr=0.1)
        ])
    ]

    mock_item_features = AsyncMock()
    mock_item_features.scalars.return_value.all.return_value = [
        MagicMock(feature='{"feature1": 1, "feature2": 2}'),
        MagicMock(feature='{"feature1": 3, "feature2": 4}')
    ]

    mock_keyword_feature = AsyncMock()
    mock_keyword_feature.scalars.return_value.first.return_value = MagicMock(
        feature='{"k_feature1": 0.5, "k_feature2": 1.5}'
    )

    # Настройка мокирования асинхронных вызовов
    mock_session.return_value.__aenter__.return_value.execute.side_effect = [
        mock_adv_settings,  # Первый вызов execute для AdvSetting
        mock_item_features,  # Второй и последующие вызовы для ItemFeature
        mock_item_features,  # Мокирование повторяется для каждого вызова с ItemFeature
        mock_keyword_feature,  # Вызов для KeywordFeature
        mock_keyword_feature  # Повтор для каждого KeywordFeature
    ]

    # Инициализация и вызов тестируемой функции
    your_instance = Fitter()  # Допустим, YourClass содержит __get_df_for_fit
    result_df = await your_instance._get_df_for_fit()

    # Проверки
    assert isinstance(result_df, pd.DataFrame)  # Проверяем, что результат - DataFrame
    assert not result_df.empty  # DataFrame не должен быть пустым
    assert len(result_df.columns) > 0  # Должны быть колонки


@pytest.mark.asyncio
async def test_bayesian_apply():
    # Mocking the get_min_str_settings method
    Fitter.get_min_str_settings = AsyncMock(return_value=(
        {1: 0.1},  # adv_id_min_ctr
        {'cabinet1': {'category1': 0.2}},  # shop_category_min_ctr
        {'cabinet1': 0.3},  # shop_avg_min_ctr
        0.4,  # overall_avg_ctr
        {101: {'cabinet': 'cabinet1', 'wb_category_name': 'category1'}}  # nmid_cabitet_category_refs
    ))

    # Creating a DataFrame to pass to the _bayesian_apply method
    df = pd.DataFrame({
        'adv_id': [1],
        'clicks': [10],
        'views': [100],
        'nmids': [[101]]
    })

    # Creating an instance of Fitter and calling _bayesian_apply
    fitter = Fitter()
    result_df = await fitter._bayesian_apply(df)

    # Checking if the DataFrame is modified as expected
    assert 'ctr' in result_df.columns
    assert result_df['ctr'][0] > 0



@pytest.mark.asyncio
async def test_get_category_name_min_ctr_final_data():
    mock_query_result = MagicMock()
    mock_query_result.unique.return_value.scalars.return_value.all.return_value = [MagicMock(),
                                                                                   MagicMock()]  # Пример с двумя объектами AdvSetting

    # Настройка асинхронного мока сессии, чтобы возвращать настроенный мок результата запроса
    session = AsyncMock()
    session.execute.return_value = mock_query_result  # Обратите внимание, здесь не используется await, так как мы настраиваем возвращаемое значение

    # Define the expected output
    expected_output = {1: 0.1, 2: 0.2}

    # Call the function with the mock session
    result = await get_category_name_min_ctr_final_data(session)

    # Assert that the function returns the expected output
    assert result == expected_output







