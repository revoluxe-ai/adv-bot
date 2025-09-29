"""
VGGVectorizer класс для извлечения признаковых векторов из изображений с помощью VGG19.
Предзагружает модель при инициализации и переиспользует её между запросами.
"""

import logging
from typing import Optional

import faiss
import numpy as np
import PIL.Image
import tensorflow as tf
from keras.applications import vgg19
from keras.applications.vgg19 import preprocess_input

from app.utils.image_normalizer import normalize_image_mode

logger = logging.getLogger(__name__)


class VGGVectorizer:
    """
    Класс для извлечения признаковых векторов из изображений с помощью VGG19.
    Модель предзагружается при инициализации и переиспользуется между запросами.
    """

    def __init__(self):
        """
        Инициализация VGGVectorizer.
        Предзагружает модель VGG19 с весами ImageNet.
        """
        self._model: Optional[tf.keras.Model] = None
        self._is_loaded = False

    def _load_model(self) -> None:
        """
        Загрузка модели VGG19.
        Вызывается автоматически при первом обращении к get_vector.
        """
        if self._is_loaded:
            return

        logger.info("Загружаю модель VGG19...")

        try:
            # Создание модели VGG19 без классификатора (только feature extractor)
            self._model = vgg19.VGG19(
                weights="imagenet", include_top=False, input_shape=(224, 224, 3)
            )

            # Отключаем обучение для всех слоев
            self._model.trainable = False

            # Компилируем модель для предсказания
            self._model.compile(optimizer="adam", loss="mse")

            self._is_loaded = True
            logger.info("Модель VGG19 успешно загружена")

        except Exception as exc:
            logger.error(f"Ошибка при загрузке модели VGG19: {exc}", exc_info=True)
            raise

    def get_vector(self, image: PIL.Image.Image) -> np.ndarray:
        """
        Извлечение признакового вектора из изображения.

        Args:
            image: PIL изображение

        Returns:
            Одномерный numpy массив float32 с L2-нормализованным вектором признаков

        Raises:
            ValueError: При неверном формате изображения
            RuntimeError: При ошибке обработки изображения
        """
        if not self._is_loaded:
            self._load_model()

        try:
            # Безопасная нормализация режима изображения (обработка RGBA/P)
            image = normalize_image_mode(image)

            # Изменение размера до 224x224 (требование VGG19)
            image = image.resize((224, 224), PIL.Image.Resampling.LANCZOS)

            # Преобразование в numpy массив
            img_array = np.array(image, dtype=np.float32)

            # Добавление batch dimension
            img_array = np.expand_dims(img_array, axis=0)

            # Предобработка для VGG19 (нормализация по ImageNet)
            img_array = preprocess_input(img_array)

            # Извлечение признаков
            features = self._model.predict(img_array, verbose=0)

            # Преобразование в одномерный массив
            vector = features.flatten()

            # Приведение к float32
            vector = vector.astype(np.float32)

            # L2-нормализация с помощью faiss
            # faiss.normalize_L2 работает с 2D массивами, поэтому добавляем batch dimension
            vector_2d = np.expand_dims(vector, axis=0)
            faiss.normalize_L2(vector_2d)
            vector = vector_2d[0]  # Убираем batch dimension

            logger.debug(f"Извлечен вектор размерности {len(vector)}")
            return vector

        except Exception as exc:
            error_msg = f"Ошибка при извлечении вектора из изображения: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from exc

    @property
    def is_loaded(self) -> bool:
        """
        Проверка загружена ли модель.

        Returns:
            True если модель загружена, False иначе
        """
        return self._is_loaded

    @property
    def model(self) -> Optional[tf.keras.Model]:
        """
        Получение экземпляра модели.

        Returns:
            Экземпляр модели VGG19 или None если не загружена
        """
        return self._model
