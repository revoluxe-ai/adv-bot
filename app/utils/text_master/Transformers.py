import asyncio
import logging
import os
import re
from functools import partial
from typing import Any, Union, cast

import numpy as np
from gensim.models.keyedvectors import KeyedVectors # type: ignore
from huggingface_hub import hf_hub_download # type: ignore

logger = logging.getLogger(__name__)


class Word2Vec:
    _model: KeyedVectors | None = None # Добавляем аннотацию типа
    model_path = "ruwiki_20180420_100d.txt"  # Имя файла модели на диске
    _load_model_lock = asyncio.Lock()

    async def _load_model(self) -> None:
        try:
            if os.path.exists(self.model_path):
                func = partial(KeyedVectors.load_word2vec_format, self.model_path, binary=False)
                self._model = await asyncio.to_thread(func)
            else:
                model_url = hf_hub_download(
                    repo_id="Word2vec/wikipedia2vec_ruwiki_20180420_100d",
                    filename="ruwiki_20180420_100d.txt",
                )
                func = partial(KeyedVectors.load_word2vec_format, model_url, binary=False)
                self._model = await asyncio.to_thread(func)
                # Сохранение модели на диск
                if self._model is not None:
                    func = partial(self._model.save_word2vec_format, self.model_path, binary=False)
                    await asyncio.to_thread(func)
        except EOFError as e:
            logger.debug(f"Ошибка загрузки модели: {e}. Попытка перезагрузить модель...")
            # Удаление поврежденного файла модели, если он существует
            if os.path.exists(self.model_path):
                os.remove(self.model_path)
            # Повторный вызов _load_model для перезагрузки
            await self._load_model()
            del e
        except Exception as e:
            logger.error(f"Произошла ошибка при загрузке модели: {e}")
            raise e

    def _most_similar(self, word: str) -> Any:
        if self._model is not None:
            return self._model.most_similar(word)
        return [] # Возвращаем пустой список, если модель не загружена

    async def average_vector_from_sentence(self, phrase: str) -> float | np.ndarray[Any, Any] | None:
        async with self._load_model_lock:
            if self._model is None:
                await self._load_model()
        phrase = re.sub("[-,.]", " ", phrase)
        words = phrase.split()
        vectors = []
        null_vectors = 0
        for word in words:
            if self._model is not None and word in self._model:
                vector = self._model[word]
                vectors.append(vector)
            else:
                null_vectors += 1

        if vectors:
            return cast(Union[float, np.ndarray[Any, Any]], sum(vectors) / (len(vectors) + null_vectors)) # Явно приводим к ожидаемому типу
        else:
            return None  # В случае, если в предложении не было слов из словаря модели

    def get_norm_distance(self, value: float) -> float:
        value = round(value, 5)
        if 0 <= value <= 1:
            if value < 0.5:
                return 1
            else:
                return 1 - (value - 0.5) / 0.5
        else:
            raise ValueError("Значение должно быть в диапазоне от 0 до 1")
