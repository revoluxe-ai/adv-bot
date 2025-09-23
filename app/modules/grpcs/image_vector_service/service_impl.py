"""
Реализация gRPC сервиса для извлечения векторов признаков из изображений.
"""

import io
import logging
from typing import List

import grpc
import numpy as np
import PIL.Image

from app.modules.grpcs.image_vector_service.vgg_vectorizer import VGGVectorizer
from .grpc_service.image_vector_pb2_grpc import ImageVectorServiceServicer

logger = logging.getLogger(__name__)


class ImageVectorServiceImpl(ImageVectorServiceServicer):
    """
    Реализация gRPC сервиса ImageVectorService.
    """

    def __init__(self, vectorizer_instance: VGGVectorizer):
        """
        Инициализация сервиса.

        Args:
            vectorizer_instance: Экземпляр класса VGGVectorizer
        """
        self.vectorizer = vectorizer_instance

    async def GetVector(self, request, context):
        """
        Обработка запроса на извлечение вектора признаков из изображения.

        Args:
            request: ImageRequest с байтами изображения
            context: gRPC контекст

        Returns:
            VectorResponse с вектором признаков и флагом found
        """
        image_bytes = request.image
        mime_type = request.mime

        # Валидация входных данных
        if not image_bytes:
            error_msg = "Image bytes cannot be empty"
            logger.warning(f"Invalid request: {error_msg}")
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, error_msg)

        try:
            # Парсинг изображения из байтов
            try:
                image = PIL.Image.open(io.BytesIO(image_bytes))

                # Проверка что изображение было успешно загружено
                if image is None:
                    error_msg = "Failed to decode image from bytes"
                    logger.warning(f"Image decoding failed: {error_msg}")
                    return self._create_response([], False)

                # Проверка формата изображения
                if image.format not in ["JPEG", "PNG", "WEBP"]:
                    logger.warning(f"Unsupported image format: {image.format}")
                    return self._create_response([], False)

            except PIL.UnidentifiedImageError as exc:
                error_msg = f"Invalid image format: {str(exc)}"
                logger.warning(f"Image parsing failed: {error_msg}")
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, error_msg)
            except Exception as exc:
                error_msg = f"Failed to parse image: {str(exc)}"
                logger.warning(f"Image parsing failed: {error_msg}")
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, error_msg)

            # Извлечение вектора признаков
            try:
                vector = self.vectorizer.get_vector(image)

                # Преобразование numpy array в список float
                if isinstance(vector, np.ndarray):
                    vector_list = vector.tolist()
                else:
                    vector_list = list(vector)

                logger.info(
                    f"Successfully extracted vector from image "
                    f"(format: {image.format}, size: {image.size}, dimension: {len(vector_list)})"
                )
                return self._create_response(vector_list, True)

            except Exception as exc:
                error_msg = f"Failed to extract vector from image: {str(exc)}"
                logger.warning(f"Vector extraction failed: {error_msg}")
                return self._create_response([], False)

        except grpc.RpcError:
            # Проброс gRPC ошибок без изменений
            raise
        except Exception as exc:
            error_msg = f"Unexpected error processing image: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, error_msg)

    def _create_response(self, vector: List[float], found: bool):
        """
        Создание ответа gRPC.

        Args:
            vector: Список значений вектора
            found: Флаг успешного извлечения вектора

        Returns:
            VectorResponse объект
        """
        # Импорт здесь для избежания циклических зависимостей
        from .grpc_service.image_vector_pb2 import VectorResponse

        return VectorResponse(vector=vector, found=found)
