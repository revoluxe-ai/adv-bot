"""
gRPC сервер для Word2Vec сервиса.
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
from app.modules.grpcs.word2vec_service.service_impl import Word2VecServiceImpl
from app.modules.grpcs.word2vec_service.word2vec import Word2Vec
from app.modules.grpcs.word2vec_service.grpc_service.word2vec_pb2_grpc import (
    add_Word2VecGetterServicer_to_server,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Singleton экземпляр Word2Vec
_word2vec_instance: Optional[Word2Vec] = None


def get_word2vec_instance() -> Word2Vec:
    """
    Получение singleton экземпляра Word2Vec.

    Returns:
        Экземпляр Word2Vec
    """
    global _word2vec_instance
    if _word2vec_instance is None:
        _word2vec_instance = Word2Vec()
    return _word2vec_instance


async def preload_model() -> None:
    """
    Предзагрузка модели Word2Vec перед запуском сервера.
    """
    logger.info("Начинаю предзагрузку модели Word2Vec...")

    word2vec = get_word2vec_instance()

    try:
        # Принудительная загрузка модели
        await word2vec._load_model()

        # Прогрев модели через тестовый запрос
        test_phrase = "warmup test phrase"
        await word2vec.average_vector_from_sentence(test_phrase)

        logger.info("Модель Word2Vec успешно предзагружена и прогрета")

    except Exception as exc:
        logger.error(f"Ошибка при предзагрузке модели: {exc}", exc_info=True)
        raise


async def serve(host: str = "0.0.0.0", port: int = 50051) -> None:
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

    # Получение экземпляра Word2Vec и создание сервиса
    word2vec = get_word2vec_instance()
    service_impl = Word2VecServiceImpl(word2vec)

    # Регистрация сервиса
    add_Word2VecGetterServicer_to_server(service_impl, server)

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
    parser = argparse.ArgumentParser(description="Word2Vec gRPC Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=50051, help="Port to bind to")

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
