"""
Быстрый тест для проверки работы Image Vector сервиса.
"""

import asyncio
import logging
import numpy as np
import PIL.Image

from app.modules.grpcs.image_vector_service.vgg_vectorizer import VGGVectorizer

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def quick_test():
    """
    Быстрый тест сервиса.
    """
    logger.info("🚀 Запускаю быстрый тест Image Vector сервиса")

    # Создаем тестовое изображение
    test_image = PIL.Image.fromarray(
        np.random.randint(0, 255, (300, 400, 3), dtype=np.uint8)
    )

    # Преобразуем в байты
    image_bytes = VGGVectorizer.from_pil(test_image, format="JPEG")
    logger.info(f"Создано тестовое изображение размером {len(image_bytes)} байт")

    try:
        async with VGGVectorizer("localhost:50052") as client:
            logger.info("Подключение к серверу...")

            vector, found = await client.get_vector(image_bytes, mime="image/jpeg")

            if found and vector:
                logger.info(f"✅ Успешно получен вектор размерности {len(vector)}")
                logger.info(f"Первые 5 значений: {vector[:5]}")
                logger.info(f"Последние 5 значений: {vector[-5:]}")
                logger.info("🎉 Тест пройден успешно!")
                return True
            else:
                logger.error("❌ Вектор не найден")
                return False

    except Exception as exc:
        logger.error(f"❌ Ошибка при тестировании: {exc}")
        logger.info(
            "💡 Убедитесь, что сервер запущен: python -m app.modules.image_vector_service.server"
        )
        return False


if __name__ == "__main__":
    asyncio.run(quick_test())
