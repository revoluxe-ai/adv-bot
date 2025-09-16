from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Предполагаем, что в run_update_model.py есть функция main или класс ModelUpdater
# Адаптируйте импорт под реальную структуру модуля
try:
    from run_update_model import ModelUpdater

    class_based = True
except ImportError:
    from run_update_model import main

    class_based = False


@pytest.mark.asyncio
async def test_model_updater_loads_data():
    """
    Тест проверяет, что обновление модели корректно загружает данные
    """
    if class_based:
        # Для класса ModelUpdater

        # Создаем экземпляр обновителя модели
        updater = ModelUpdater()

        # Мокируем метод загрузки данных
        test_data = {"X": np.random.rand(100, 10), "y": np.random.randint(0, 2, 100)}
        updater.load_data = MagicMock(return_value=test_data)

        # Мокируем другие методы, чтобы предотвратить их выполнение
        updater.preprocess_data = MagicMock()
        updater.train_model = MagicMock()
        updater.evaluate_model = MagicMock()
        updater.save_model = MagicMock()

        # Вызываем тестируемый метод
        await updater.run()

        # Проверяем, что метод загрузки данных был вызван
        updater.load_data.assert_called_once()

        # Проверяем, что данные были переданы для предобработки
        updater.preprocess_data.assert_called_once_with(test_data)
    else:
        # Для функции main

        # Создаем тестовые данные
        test_data = {"X": np.random.rand(100, 10), "y": np.random.randint(0, 2, 100)}

        # Мокируем функции
        with patch(
            "run_update_model.load_data", return_value=test_data
        ) as mock_load, patch(
            "run_update_model.preprocess_data"
        ) as mock_preprocess, patch(
            "run_update_model.train_model"
        ) as mock_train, patch(
            "run_update_model.evaluate_model"
        ) as mock_eval, patch(
            "run_update_model.save_model"
        ) as mock_save:

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что функция загрузки данных была вызвана
            mock_load.assert_called_once()

            # Проверяем, что данные были переданы для предобработки
            mock_preprocess.assert_called_once_with(test_data)


@pytest.mark.asyncio
async def test_model_updater_trains_model():
    """
    Тест проверяет, что обновление модели корректно обучает модель
    """
    if class_based:
        # Для класса ModelUpdater

        # Создаем экземпляр обновителя модели
        updater = ModelUpdater()

        # Мокируем методы
        test_data = {"X": np.random.rand(100, 10), "y": np.random.randint(0, 2, 100)}
        test_preprocessed = {
            "X_train": np.random.rand(80, 10),
            "X_test": np.random.rand(20, 10),
            "y_train": np.random.randint(0, 2, 80),
            "y_test": np.random.randint(0, 2, 20),
        }
        test_model = MagicMock()

        updater.load_data = MagicMock(return_value=test_data)
        updater.preprocess_data = MagicMock(return_value=test_preprocessed)
        updater.train_model = MagicMock(return_value=test_model)
        updater.evaluate_model = MagicMock()
        updater.save_model = MagicMock()

        # Вызываем тестируемый метод
        await updater.run()

        # Проверяем, что метод обучения модели был вызван с правильными аргументами
        updater.train_model.assert_called_once_with(
            test_preprocessed["X_train"], test_preprocessed["y_train"]
        )

        # Проверяем, что модель была оценена
        updater.evaluate_model.assert_called_once_with(
            test_model, test_preprocessed["X_test"], test_preprocessed["y_test"]
        )

        # Проверяем, что модель была сохранена
        updater.save_model.assert_called_once_with(test_model)
    else:
        # Для функции main

        # Создаем тестовые данные
        test_data = {"X": np.random.rand(100, 10), "y": np.random.randint(0, 2, 100)}
        test_preprocessed = {
            "X_train": np.random.rand(80, 10),
            "X_test": np.random.rand(20, 10),
            "y_train": np.random.randint(0, 2, 80),
            "y_test": np.random.randint(0, 2, 20),
        }
        test_model = MagicMock()

        # Мокируем функции
        with patch(
            "run_update_model.load_data", return_value=test_data
        ) as mock_load, patch(
            "run_update_model.preprocess_data", return_value=test_preprocessed
        ) as mock_preprocess, patch(
            "run_update_model.train_model", return_value=test_model
        ) as mock_train, patch(
            "run_update_model.evaluate_model"
        ) as mock_eval, patch(
            "run_update_model.save_model"
        ) as mock_save:

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что функция обучения модели была вызвана с правильными аргументами
            mock_train.assert_called_once_with(
                test_preprocessed["X_train"], test_preprocessed["y_train"]
            )

            # Проверяем, что модель была оценена
            mock_eval.assert_called_once_with(
                test_model, test_preprocessed["X_test"], test_preprocessed["y_test"]
            )

            # Проверяем, что модель была сохранена
            mock_save.assert_called_once_with(test_model)


@pytest.mark.asyncio
async def test_model_updater_saves_model():
    """
    Тест проверяет, что обновление модели корректно сохраняет модель
    """
    if class_based:
        # Для класса ModelUpdater

        # Создаем экземпляр обновителя модели
        updater = ModelUpdater()

        # Мокируем методы
        test_model = MagicMock()

        updater.load_data = MagicMock()
        updater.preprocess_data = MagicMock()
        updater.train_model = MagicMock(return_value=test_model)
        updater.evaluate_model = MagicMock()
        updater.save_model = MagicMock()

        # Вызываем тестируемый метод
        await updater.run()

        # Проверяем, что метод сохранения модели был вызван с правильной моделью
        updater.save_model.assert_called_once_with(test_model)
    else:
        # Для функции main

        # Создаем тестовую модель
        test_model = MagicMock()

        # Мокируем функции
        with patch("run_update_model.load_data") as mock_load, patch(
            "run_update_model.preprocess_data"
        ) as mock_preprocess, patch(
            "run_update_model.train_model", return_value=test_model
        ) as mock_train, patch(
            "run_update_model.evaluate_model"
        ) as mock_eval, patch(
            "run_update_model.save_model"
        ) as mock_save:

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что функция сохранения модели была вызвана с правильной моделью
            mock_save.assert_called_once_with(test_model)
