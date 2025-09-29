"""
Word2Vec класс для работы с векторизацией текста.
Загружает модель KeyedVectors и предоставляет метод для получения среднего вектора фразы.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from gensim.models import KeyedVectors

logger = logging.getLogger(__name__)


class Word2Vec:
    """
    Класс для работы с Word2Vec моделью.
    Автоматически загружает модель при первом обращении или скачивает её при отсутствии.
    """

    def __init__(self, model_path: str = "ruwiki_20180420_100d.txt"):
        """
        Инициализация Word2Vec.

        Args:
            model_path: Путь к файлу модели Word2Vec
        """
        self.model_path = Path(model_path)
        self._model: Optional[KeyedVectors] = None
        self._loading_lock = asyncio.Lock()

    async def _load_model(self) -> None:
        """
        Асинхронная загрузка модели Word2Vec.
        Если файл модели отсутствует, скачивает его.
        """
        async with self._loading_lock:
            if self._model is not None:
                return

            try:
                if self.model_path.exists():
                    logger.info(f"Загружаю модель Word2Vec из {self.model_path}")
                    # Загрузка модели в отдельном потоке для избежания блокировки
                    loop = asyncio.get_event_loop()
                    func = lambda: KeyedVectors.load_word2vec_format(
                        str(self.model_path), binary=False, no_header=False
                    )
                    self._model = await loop.run_in_executor(None, func)
                else:
                    logger.info(
                        f"Модель не найдена по пути {self.model_path}, начинаю загрузку..."
                    )
                    await self._download_model()
                    # Повторная загрузка после скачивания
                    loop = asyncio.get_event_loop()
                    func = lambda: KeyedVectors.load_word2vec_format(
                        str(self.model_path), binary=False, no_header=False
                    )
                    self._model = await loop.run_in_executor(None, func)

                logger.info("Модель Word2Vec успешно загружена")

            except Exception as e:
                logger.error(f"Произошла ошибка при загрузке модели: {e}")
                # Если файл модели поврежден, удаляем его и перескачиваем
                if self.model_path.exists():
                    logger.info("Удаляю поврежденный файл модели...")
                    self.model_path.unlink()
                    logger.info("Перескачиваю модель...")
                    await self._download_model()
                    # Повторная загрузка после перескачивания
                    loop = asyncio.get_event_loop()
                    func = lambda: KeyedVectors.load_word2vec_format(
                        str(self.model_path), binary=False, no_header=False
                    )
                    self._model = await loop.run_in_executor(None, func)
                    logger.info("Модель Word2Vec успешно перезагружена")
                else:
                    raise e

    async def _download_model(self) -> None:
        """
        Скачивание модели Word2Vec.
        Использует ту же русскую модель, что и legacy код.
        """
        logger.info("Скачиваю русскую модель Word2Vec...")

        def download_model():
            from huggingface_hub import hf_hub_download
            from gensim.models.keyedvectors import KeyedVectors

            # Скачиваем модель с HuggingFace
            model_url = hf_hub_download(
                repo_id="Word2vec/wikipedia2vec_ruwiki_20180420_100d",
                filename="ruwiki_20180420_100d.txt",
            )

            # Загружаем модель
            model = KeyedVectors.load_word2vec_format(model_url, binary=False)

            # Сохраняем модель на диск
            model.save_word2vec_format(str(self.model_path), binary=False)

        # Скачивание в отдельном потоке
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_model)

        logger.info(f"Русская модель Word2Vec скачана и сохранена в {self.model_path}")

    async def average_vector_from_sentence(self, sentence: str) -> Optional[np.ndarray]:
        """
        Получение среднего вектора для предложения.

        Args:
            sentence: Входное предложение для векторизации

        Returns:
            Средний вектор предложения или None, если не удалось получить вектор
        """
        if self._model is None:
            await self._load_model()

        if not sentence or not sentence.strip():
            return None

        # Выносим синхронные операции с моделью в executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._compute_sentence_vector, sentence)

    def _compute_sentence_vector(self, sentence: str) -> Optional[np.ndarray]:
        """
        Синхронное вычисление вектора предложения.
        Выполняется в отдельном потоке через executor.
        Использует тот же алгоритм, что и legacy код.

        Args:
            sentence: Входное предложение

        Returns:
            Средний вектор предложения или None
        """
        import re

        # Очистка текста как в legacy коде
        phrase = re.sub("[-,.]", " ", sentence)
        words = phrase.split()

        assert self._model
        vectors = []
        null_vectors = 0

        for word in words:
            if word in self._model:
                vector = self._model[word]
                vectors.append(vector)
            else:
                null_vectors += 1

        if vectors:
            # Используем тот же алгоритм усреднения, что и в legacy коде
            return sum(vectors) / (len(vectors) + null_vectors)
        else:
            logger.warning(f"Не найдено валидных слов в предложении: '{sentence}'")
            return None

    def is_loaded(self) -> bool:
        """
        Проверка, загружена ли модель.

        Returns:
            True, если модель загружена, иначе False
        """
        return self._model is not None
