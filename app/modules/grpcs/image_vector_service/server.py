"""
gRPC сервер для Image Vector сервиса.
"""

import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
import argparse
import asyncio
import logging
from typing import Optional
import grpc
from app.modules.grpcs.image_vector_service.service_impl import ImageVectorServiceImpl
from app.modules.grpcs.image_vector_service.vgg_vectorizer import VGGVectorizer
from app.modules.grpcs.image_vector_service.grpc_service.image_vector_pb2_grpc import (
    add_ImageVectorServiceServicer_to_server,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Singleton экземпляр VGGVectorizer
_vectorizer_instance: Optional[VGGVectorizer] = None


def get_vectorizer_instance() -> VGGVectorizer:
    """
    Получение singleton экземпляра VGGVectorizer.

    Returns:
        Экземпляр VGGVectorizer
    """
    global _vectorizer_instance
    if _vectorizer_instance is None:
        _vectorizer_instance = VGGVectorizer()
    return _vectorizer_instance


async def preload_model() -> None:
    """
    Предзагрузка модели VGG19 перед запуском сервера.
    """
    logger.info("Начинаю предзагрузку модели VGG19...")

    vectorizer = get_vectorizer_instance()

    try:
        # Принудительная загрузка модели
        vectorizer._load_model()

        # Прогрев модели через тестовое изображение
        import numpy as np
        import PIL.Image

        # Создаем тестовое изображение 224x224 RGB
        test_image = PIL.Image.fromarray(
            np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        )

        # Извлекаем вектор для прогрева
        test_vector = vectorizer.get_vector(test_image)

        logger.info(
            f"Модель VGG19 успешно предзагружена и прогрета "
            f"(размерность вектора: {len(test_vector)})"
        )

    except Exception as exc:
        logger.error(f"Ошибка при предзагрузке модели: {exc}", exc_info=True)
        raise


async def serve(host: str = "0.0.0.0", port: int = 50052) -> None:
    """
    Запуск gRPC сервера.

    Args:
        host: Хост для привязки сервера
        port: Порт для привязки сервера
    """
    # Предзагрузка модели
    await preload_model()

    # Создание сервера
    server = grpc.aio.server()

    # Получение экземпляра VGGVectorizer и создание сервиса
    vectorizer = get_vectorizer_instance()
    service_impl = ImageVectorServiceImpl(vectorizer)

    # Регистрация сервиса
    add_ImageVectorServiceServicer_to_server(service_impl, server)

    # Привязка к адресу
    listen_addr = f"{host}:{port}"
    server.add_insecure_port(listen_addr)

    logger.info(f"Запускаю gRPC сервер на {listen_addr}")

    try:
        await server.start()
        logger.info(f"gRPC сервер успешно запущен на {listen_addr}")
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, останавливаю сервер...")
        await server.stop(grace=30)
    except Exception as exc:
        logger.error(f"Ошибка при работе сервера: {exc}", exc_info=True)
        raise
    finally:
        await server.stop(grace=0)
        logger.info("Сервер остановлен")


def main():
    """
    Точка входа для запуска сервера.
    """
    parser = argparse.ArgumentParser(description="Image Vector gRPC Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=50052, help="Port to bind to")

    args = parser.parse_args()

    try:
        asyncio.run(serve(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Сервер остановлен пользователем")
    except Exception as exc:
        logger.error(f"Критическая ошибка: {exc}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
