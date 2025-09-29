"""
Асинхронный клиент для Image Vector gRPC сервиса.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import grpc
import PIL.Image

from app.utils.image_normalizer import safe_image_to_bytes

from ..grpc_service.image_vector_pb2 import ImageRequest
from ..grpc_service.image_vector_pb2_grpc import ImageVectorServiceStub

logger = logging.getLogger(__name__)


class ImageVectorClient:
    """
    Асинхронный клиент gRPC для сервиса Image Vector.
    """

    def __init__(self, endpoint: str):
        """
        Инициализация клиента.

        Args:
            endpoint: Адрес сервера в формате "host:port"
        """
        self._endpoint = endpoint
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[ImageVectorServiceStub] = None

    async def connect(self) -> None:
        """
        Создание соединения с сервером.
        """
        if self._channel is None:
            self._channel = grpc.aio.insecure_channel(self._endpoint)
            self._stub = ImageVectorServiceStub(self._channel)
            logger.info(f"Подключение к серверу Image Vector: {self._endpoint}")

    async def close(self) -> None:
        """
        Закрытие соединения с сервером.
        """
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.info("Соединение с сервером Image Vector закрыто")

    async def get_vector(
        self, image_bytes: bytes, mime: Optional[str] = None
    ) -> Tuple[Optional[list[float]], bool]:
        """
        Получение вектора признаков из изображения.

        Args:
            image_bytes: Байты изображения
            mime: MIME тип изображения (опционально)

        Returns:
            Кортеж (вектор, found), где:
            - вектор: список float или None, если вектор не найден
            - found: булево значение успешности операции

        Raises:
            ValueError: При неверных аргументах запроса
            RuntimeError: При внутренней ошибке сервера
        """
        if self._stub is None:
            await self.connect()

        if not image_bytes:
            raise ValueError("Image bytes cannot be empty")

        request = ImageRequest(image=image_bytes, mime=mime or "")

        try:
            response = await self._stub.GetVector(request)

            if not response.found:
                logger.warning("Vector not found for provided image")
                return None, False

            vector = list(response.vector)
            logger.info(f"Successfully received vector (dimension: {len(vector)})")
            return vector, True

        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.INVALID_ARGUMENT:
                error_msg = f"Invalid argument: {exc.details()}"
                logger.warning(error_msg)
                raise ValueError(error_msg) from exc
            elif exc.code() == grpc.StatusCode.INTERNAL:
                error_msg = f"Internal server error: {exc.details()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from exc
            else:
                error_msg = f"gRPC error ({exc.code()}): {exc.details()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from exc
        except Exception as exc:
            error_msg = f"Unexpected error: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from exc

    @staticmethod
    def from_pil(image: PIL.Image.Image, format: str = "JPEG") -> bytes:
        """
        Преобразование PIL изображения в байты с безопасной обработкой альфаканала.

        Args:
            image: PIL изображение
            format: Формат для сохранения ("JPEG" или "PNG")

        Returns:
            Байты изображения

        Raises:
            ValueError: При неверном формате
        """
        return safe_image_to_bytes(image, format=format)

    @staticmethod
    def from_path(path: str) -> bytes:
        """
        Загрузка изображения из файла в байты.

        Args:
            path: Путь к файлу изображения

        Returns:
            Байты изображения

        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если файл не является изображением
        """
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")

        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as exc:
            raise ValueError(f"Failed to read image file {path}: {exc}") from exc

    # Поддержка async with
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
