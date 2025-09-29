"""
Асинхронный клиент для Word2Vec gRPC сервиса.
"""

import asyncio
import logging
from typing import Optional

import grpc

from app.core.wb_api.data_classes.namedtuples import KeywordStatForNeo, KeywordPhrase
from app.utils import text_cleaner
from ..grpc_service.word2vec_pb2 import GetWordVectorRequest
from ..grpc_service.word2vec_pb2_grpc import Word2VecGetterStub

logger = logging.getLogger(__name__)


class Word2VecClient:
    """
    Асинхронный клиент gRPC для сервиса Word2Vec.
    """

    def __init__(self, host: str = "localhost", port: int = 50051):
        """
        Инициализация клиента.

        Args:
            host: Хост сервера
            port: Порт сервера
        """
        self._target = f"{host}:{port}"
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[Word2VecGetterStub] = None

    async def connect(self) -> None:
        """
        Создание соединения с сервером.
        """
        if self._channel is None:
            self._channel = grpc.aio.insecure_channel(self._target)
            self._stub = Word2VecGetterStub(self._channel)
            logger.info(f"Подключение к серверу Word2Vec: {self._target}")

    async def close(self) -> None:
        """
        Закрытие соединения с сервером.
        """
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.info("Соединение с сервером Word2Vec закрыто")

    async def get_phrase_data(self, phrase: str) -> KeywordPhrase:
        """
        Получение данных для фразы: чистка, разбивка на слова, получение векторов.

        Args:
            phrase: Исходная фраза

        Returns:
            KeywordPhrase объект для отправки в Neo4j
        """
        # 1. Чистим фразу
        clear_phrase = text_cleaner.clear(phrase)

        # 2. Разбиваем на слова (с дополнительной обработкой знаков препинания)
        import re

        clean_phrase = re.sub("[-,.]", " ", clear_phrase)
        words = clean_phrase.split()

        # 3. Получаем векторы для каждого слова
        keywords = []
        for word in words:
            if word.strip():  # Проверяем, что слово не пустое
                vector = await self._get_word_vector(word.strip())
                keywords.append(KeywordStatForNeo(text=word.strip(), vector=vector))
                await asyncio.sleep(0)  # Даем другим задачам выполниться

        # 4. Получаем вектор для всей фразы (усреднение)
        phrase_vector = await self._get_phrase_vector(words)

        # 5. Создаем объект для Neo4j
        phrase_data = KeywordPhrase(
            text=clear_phrase,
            words=keywords,
            word2vec=phrase_vector,
        )

        return phrase_data

    async def _get_phrase_vector(self, words: list[str]) -> Optional[list[float]]:
        """
        Получение усредненного вектора для фразы (как в legacy коде).

        Args:
            words: Список слов

        Returns:
            Усредненный вектор или None
        """
        vectors = []
        null_vectors = 0

        for word in words:
            if word.strip():
                vector = await self._get_word_vector(word.strip())
                if vector is not None:
                    vectors.append(vector)
                else:
                    null_vectors += 1

        if vectors:
            # Используем тот же алгоритм усреднения, что и в legacy коде
            import numpy as np

            return (
                np.sum(np.array(vectors), axis=0) / (len(vectors) + null_vectors)
            ).tolist()
        else:
            return None

    def _get_norm_distance(self, value):
        value = round(value, 5)
        if 0 <= value <= 1:
            if value < 0.5:
                return 1
            else:
                return 1 - (value - 0.5) / 0.5
        else:
            raise ValueError("Значение должно быть в диапазоне от 0 до 1")

    async def _get_word_vector(self, word: str) -> Optional[list[float]]:
        """
        Получение вектора для одного слова через gRPC.

        Args:
            word: Слово для получения вектора

        Returns:
            Вектор слова или None, если слово не найдено
        """
        if self._stub is None:
            await self.connect()

        if not word or not word.strip():
            return None

        request = GetWordVectorRequest(word=word.strip())

        try:
            response = await self._stub.get_vector_from_word(request)

            if not response.vector:  # Пустой список означает, что вектор не найден
                logger.debug(f"Vector not found for word: '{word}'")
                return None

            vector = list(response.vector)
            logger.debug(
                f"Successfully received vector for word: '{word}' (dimension: {len(vector)})"
            )
            return vector

        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.INVALID_ARGUMENT:
                error_msg = f"Invalid argument: {exc.details()}"
                logger.warning(error_msg)
                return None
            elif exc.code() == grpc.StatusCode.INTERNAL:
                error_msg = f"Internal server error: {exc.details()}"
                logger.error(error_msg)
                return None
            else:
                error_msg = f"gRPC error ({exc.code()}): {exc.details()}"
                logger.error(error_msg)
                return None
        except Exception as exc:
            error_msg = f"Unexpected error: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            return None

    # Поддержка async with
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
