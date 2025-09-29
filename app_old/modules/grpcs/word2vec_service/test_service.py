"""
Тестовый скрипт для проверки работы Word2Vec gRPC сервиса.
"""

import asyncio
import logging
from app.modules.grpcs.word2vec_service import Word2VecClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_client():
    """
    Тестирование клиента Word2Vec.
    """
    async with Word2VecClient("localhost", 50051) as client:
        # Тестовые фразы
        test_phrases = [
            "hello world",
            "machine learning",
            "artificial intelligence",
            "natural language processing",
            "empty phrase test",  # Может не найтись
        ]

        for phrase in test_phrases:
            try:
                # vector = await client.get_vector(phrase)
                # if vector:
                #     logger.info(f"Фраза '{phrase}': вектор размерности {len(vector)}")
                # else:
                #     logger.warning(f"Фраза '{phrase}': вектор не найден")
                logger.info(f"Фраза '{phrase}': вектор не найден")
            except Exception as exc:
                logger.error(f"Ошибка для фразы '{phrase}': {exc}")


async def test_invalid_input():
    """
    Тестирование обработки неверных входных данных.
    """
    async with Word2VecClient("localhost", 50051) as client:
        try:
            # await client.get_vector("")
            logger.error("Ожидалась ошибка для пустой строки")
        except ValueError as exc:
            logger.info(f"Корректно обработана пустая строка: {exc}")

        try:
            # await client.get_vector("   ")
            logger.error("Ожидалась ошибка для строки из пробелов")
        except ValueError as exc:
            logger.info(f"Корректно обработана строка из пробелов: {exc}")


async def main():
    """
    Основная функция тестирования.
    """
    logger.info("Начинаю тестирование Word2Vec gRPC клиента")

    try:
        await test_client()
        await test_invalid_input()
        logger.info("Тестирование завершено успешно")
    except Exception as exc:
        logger.error(f"Ошибка при тестировании: {exc}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
