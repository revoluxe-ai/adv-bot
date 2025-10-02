"""
Реализация gRPC сервиса для Word2Vec.
"""

import logging
from typing import List, Optional

import grpc
import numpy as np

from .grpc_service.word2vec_pb2_grpc import Word2VecGetterServicer
from app.modules.grpcs.word2vec_service.word2vec import Word2Vec

logger = logging.getLogger(__name__)


class Word2VecServiceImpl(Word2VecGetterServicer):
    """
    Реализация gRPC сервиса Word2VecGetter.
    """

    def __init__(self, word2vec_instance: Word2Vec):
        """
        Инициализация сервиса.

        Args:
            word2vec_instance: Экземпляр класса Word2Vec
        """
        self.word2vec = word2vec_instance

    async def get_vector_from_word(self, request, context):
        """
        Обработка запроса на получение вектора для одного слова.

        Args:
            request: GetWordVectorRequest с словом
            context: gRPC контекст

        Returns:
            GetWordVectorResponse с вектором
        """
        word = request.word

        # Валидация входных данных
        if not word or not word.strip():
            error_msg = "Word cannot be empty or whitespace-only"
            logger.warning(f"Invalid request: {error_msg}")
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, error_msg)

        try:
            # Получение вектора для одного слова
            vector = await self._get_word_vector(word.strip())

            if vector is None:
                logger.warning(f"No vector found for word: '{word}'")
                return self._create_response([])

            logger.info(
                f"Successfully generated vector for word: '{word}' (dimension: {len(vector)})"
            )
            return self._create_response(vector)

        except Exception as exc:
            error_msg = f"Unexpected error processing word '{word}': {str(exc)}"
            logger.error(error_msg, exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, error_msg)

    def _create_response(self, vector: List[float]):
        """
        Создание ответа gRPC.

        Args:
            vector: Список значений вектора

        Returns:
            GetVectorResponse объект
        """
        # Импорт здесь для избежания циклических зависимостей
        from .grpc_service.word2vec_pb2 import GetWordVectorResponse

        return GetWordVectorResponse(vector=vector)

    async def _get_word_vector(self, word: str) -> Optional[List[float]]:
        """
        Получение вектора для одного слова.

        Args:
            word: Слово для получения вектора

        Returns:
            Вектор слова или None, если слово не найдено
        """
        # Загружаем модель если не загружена
        if self.word2vec._model is None:
            await self.word2vec._load_model()

        # Проверяем, есть ли слово в модели
        if word in self.word2vec._model:
            vector = self.word2vec._model[word]
            if isinstance(vector, np.ndarray):
                return vector.tolist()
            elif isinstance(vector, (int, float)):
                return [float(vector)]
            else:
                return list(vector)
        else:
            return None
