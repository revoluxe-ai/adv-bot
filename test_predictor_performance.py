"""
Тест производительности оптимизированного Predictor
"""

import asyncio
import time
from unittest.mock import MagicMock

import numpy as np

# Импортируем наш оптимизированный Predictor
from app.modules.grpcs.predict_ctr_service.predictor import Predictor


class MockDataGetter:
    """Мок для DataGetter"""

    async def get_item_features_from_redis(self, nmids):
        # Создаем тестовые данные
        result = []
        for nmid in nmids:
            # Создаем случайный вектор признаков
            features = np.random.rand(100).tolist()
            result.append((nmid, features))
        return result

    async def get_keyword_features_from_redis(self, texts):
        # Создаем тестовые данные для ключевых слов
        result = []
        for text in texts:
            # Создаем случайный вектор признаков для ключевого слова
            features = np.random.rand(50).tolist()
            result.append((text, features))
        return result


async def test_performance():
    """Тест производительности"""

    # Создаем мок модель
    mock_model = MagicMock()
    mock_model.predict.return_value = np.random.rand(100)

    # Создаем predictor с мок DataGetter
    predictor = Predictor(mock_model)
    predictor._data_getter = MockDataGetter()

    # Тестовые данные
    nmids = list(range(1, 101))  # 100 товаров
    texts = [f"keyword_{i}" for i in range(1000)]  # 1000 ключевых слов

    print("Тестируем производительность...")
    print(f"Количество товаров: {len(nmids)}")
    print(f"Количество ключевых слов: {len(texts)}")

    # Тест обычного метода
    start_time = time.time()
    result1 = await predictor.predict(nmids, texts)
    time1 = time.time() - start_time

    print(f"Время выполнения обычного метода: {time1:.2f} секунд")

    # Тест батчевого метода
    start_time = time.time()
    result2 = await predictor.predict_batch(nmids, texts, batch_size=200)
    time2 = time.time() - start_time

    print(f"Время выполнения батчевого метода: {time2:.2f} секунд")
    print(f"Ускорение: {time1 / time2:.2f}x")

    # Проверяем, что результаты одинаковые
    assert len(result1) == len(result2), "Количество результатов должно совпадать"
    print("✓ Результаты корректны")


async def test_memory_usage():
    """Тест использования памяти"""
    import psutil
    import os

    process = psutil.Process(os.getpid())

    # Создаем мок модель
    mock_model = MagicMock()
    mock_model.predict.return_value = np.random.rand(100)

    # Создаем predictor
    predictor = Predictor(mock_model)
    predictor._data_getter = MockDataGetter()

    # Тестовые данные
    nmids = list(range(1, 50))
    texts = [f"keyword_{i}" for i in range(500)]

    # Измеряем память до
    memory_before = process.memory_info().rss / 1024 / 1024  # MB

    # Выполняем предсказание
    result = await predictor.predict(nmids, texts)

    # Измеряем память после
    memory_after = process.memory_info().rss / 1024 / 1024  # MB

    print("Использование памяти:")
    print(f"До: {memory_before:.2f} MB")
    print(f"После: {memory_after:.2f} MB")
    print(f"Разница: {memory_after - memory_before:.2f} MB")


if __name__ == "__main__":
    print("Запуск тестов производительности...")

    # Запускаем тесты
    asyncio.run(test_performance())
    print()
    asyncio.run(test_memory_usage())

    print("\nТесты завершены!")
