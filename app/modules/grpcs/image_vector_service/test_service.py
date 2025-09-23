"""
Тестовый скрипт для проверки работы Image Vector gRPC сервиса.
"""

import asyncio
import logging
import numpy as np
import PIL.Image
from pathlib import Path

from .image_vector_client.client import ImageVectorClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_with_synthetic_image():
    """
    Тест с синтетическим изображением.
    """
    logger.info("Тестирую с синтетическим изображением...")

    # Создаем тестовое изображение
    test_image = PIL.Image.fromarray(
        np.random.randint(0, 255, (300, 400, 3), dtype=np.uint8)
    )

    # Преобразуем в байты
    image_bytes = ImageVectorClient.from_pil(test_image, format="JPEG")

    async with ImageVectorClient("localhost:50052") as client:
        try:
            vector, found = await client.get_vector(image_bytes, mime="image/jpeg")

            if found and vector:
                logger.info(f"✅ Успешно получен вектор размерности {len(vector)}")
                logger.info(f"Первые 5 значений: {vector[:5]}")
                return True
            else:
                logger.error("❌ Вектор не найден")
                return False

        except Exception as exc:
            logger.error(f"❌ Ошибка при тестировании: {exc}")
            return False


async def test_with_invalid_data():
    """
    Тест с невалидными данными.
    """
    logger.info("Тестирую с невалидными данными...")

    async with ImageVectorClient("localhost:50052") as client:
        try:
            # Тест с пустыми байтами
            vector, found = await client.get_vector(b"", mime="image/jpeg")
            logger.error("❌ Ожидалась ошибка для пустых байтов")
            return False

        except ValueError as exc:
            logger.info(f"✅ Корректно обработана ошибка: {exc}")
            return True
        except Exception as exc:
            logger.error(f"❌ Неожиданная ошибка: {exc}")
            return False


async def test_with_corrupted_image():
    """
    Тест с поврежденным изображением.
    """
    logger.info("Тестирую с поврежденным изображением...")

    # Создаем "поврежденные" байты
    corrupted_bytes = b"not an image data"

    async with ImageVectorClient("localhost:50052") as client:
        try:
            vector, found = await client.get_vector(corrupted_bytes, mime="image/jpeg")

            if not found:
                logger.info("✅ Корректно обработан поврежденный файл (found=False)")
                return True
            else:
                logger.error("❌ Ожидалось found=False для поврежденного файла")
                return False

        except ValueError as exc:
            logger.info(f"✅ Корректно обработана ошибка: {exc}")
            return True
        except Exception as exc:
            logger.error(f"❌ Неожиданная ошибка: {exc}")
            return False


async def test_from_path():
    """
    Тест загрузки изображения из файла (если есть тестовый файл).
    """
    logger.info("Тестирую загрузку из файла...")

    # Ищем тестовое изображение в проекте
    test_image_paths = [
        Path("test_image.jpg"),
        Path("test_image.png"),
        Path("docs/test_image.jpg"),
        Path("docs/test_image.png"),
    ]

    test_image_path = None
    for path in test_image_paths:
        if path.exists():
            test_image_path = path
            break

    if not test_image_path:
        logger.info("⚠️ Тестовое изображение не найдено, пропускаю тест")
        return True

    try:
        image_bytes = ImageVectorClient.from_path(str(test_image_path))

        async with ImageVectorClient("localhost:50052") as client:
            vector, found = await client.get_vector(image_bytes)

            if found and vector:
                logger.info(f"✅ Успешно обработано изображение {test_image_path}")
                logger.info(f"Размерность вектора: {len(vector)}")
                return True
            else:
                logger.error(f"❌ Не удалось обработать изображение {test_image_path}")
                return False

    except Exception as exc:
        logger.error(f"❌ Ошибка при тестировании файла: {exc}")
        return False


async def main():
    """
    Основная функция тестирования.
    """
    logger.info("🚀 Начинаю тестирование Image Vector gRPC сервиса")
    logger.info("Убедитесь, что сервер запущен на localhost:50052")

    tests = [
        ("Синтетическое изображение", test_with_synthetic_image),
        ("Невалидные данные", test_with_invalid_data),
        ("Поврежденное изображение", test_with_corrupted_image),
        ("Загрузка из файла", test_from_path),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as exc:
            logger.error(f"❌ Критическая ошибка в тесте '{test_name}': {exc}")
            results.append((test_name, False))

    # Итоговый отчет
    logger.info("\n" + "=" * 50)
    logger.info("ИТОГОВЫЙ ОТЧЕТ")
    logger.info("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1

    logger.info(f"\nРезультат: {passed}/{total} тестов пройдено")

    if passed == total:
        logger.info("🎉 Все тесты пройдены успешно!")
    else:
        logger.warning(f"⚠️ {total - passed} тестов провалено")


if __name__ == "__main__":
    asyncio.run(main())
