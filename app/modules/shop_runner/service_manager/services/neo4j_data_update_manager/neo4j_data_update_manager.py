import logging
from io import BytesIO
from typing import List, Optional, Any

import aiohttp
import grpc.aio
from PIL import Image as PilImage, UnidentifiedImageError
from sqlalchemy import select

from app.core.neo4j_manager import BaseNeo4jManager, neo4j_mixins
from app.modules.common_slaves.wildberries.data_classes.namedtuples import (
    KeywordPhrase,
    KeywordStatForNeo,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCard
from app.modules.grpcs.image_vector_service.grpc_service import (
    image_vector_pb2_grpc,
    image_vector_pb2,
)
from app.modules.grpcs.word2vec_service.grpc_service import (
    word2vec_pb2_grpc,
    word2vec_pb2,
)
from app.utils import text_cleaner
from app.utils.db.session_maker import get_async_session_maker as sm
from app.utils.image_normalizer import safe_image_to_bytes

logger = logging.getLogger(__name__)


class Neo4jDataUpdateManager(neo4j_mixins.Neo4jDataUpdateMixin, BaseNeo4jManager):
    """
    Менеджер для обновления данных в Neo4j.
    Обрабатывает товары и ключевые фразы по одному элементу за раз.
    """

    def __init__(self) -> None:
        super().__init__()
        self._word2vec_channel: Optional[grpc.aio.Channel] = None
        self._image_vector_channel: Optional[grpc.aio.Channel] = None

    async def _get_word2vec_channel(self) -> grpc.aio.Channel:
        """Получить канал для word2vec gRPC сервиса"""
        if (
            self._word2vec_channel is None
            or self._word2vec_channel.get_state() != grpc.ChannelConnectivity.READY
        ):
            # Настройки подключения к word2vec сервису
            # В реальном проекте эти настройки должны браться из конфигурации
            self._word2vec_channel = grpc.aio.insecure_channel("localhost:50051")
        return self._word2vec_channel

    async def _get_image_vector_channel(self) -> grpc.aio.Channel:
        """Получить канал для image vector gRPC сервиса"""
        if (
            self._image_vector_channel is None
            or self._image_vector_channel.get_state() != grpc.ChannelConnectivity.READY
        ):
            # Настройки подключения к image vector сервису
            # В реальном проекте эти настройки должны браться из конфигурации
            self._image_vector_channel = grpc.aio.insecure_channel("localhost:50052")
        return self._image_vector_channel

    async def _get_text_vector(self, text: str) -> Optional[List[float]]:
        """Получить вектор для текста через gRPC"""
        try:
            channel = await self._get_word2vec_channel()
            stub = word2vec_pb2_grpc.Word2VecGetterStub(channel)
            request = word2vec_pb2.GetWordVectorRequest(word=text)
            response = await stub.get_vector_from_word(request, timeout=30.0)
            return list(response.vector)

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.warning(
                    f"Таймаут при получении вектора для текста '{text}' - пропускаем"
                )
                return None
            else:
                logger.error(
                    f"gRPC ошибка при получении вектора для текста '{text}': {e}"
                )
                return None
        except Exception as e:
            logger.error(f"Ошибка получения вектора для текста '{text}': {e}")
            return None

    async def _get_image_vector(self, image_url: str) -> Optional[List[float]]:
        """Получить вектор для изображения через gRPC"""
        try:
            # Загружаем изображение
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        logger.error(
                            f"Ошибка загрузки изображения {image_url}: статус {response.status}"
                        )
                        return None

                    image_bytes = await response.read()
                    image = PilImage.open(BytesIO(image_bytes))

                    # Безопасно конвертируем в JPEG с обработкой альфаканала
                    img_data = safe_image_to_bytes(image, format="JPEG")

            channel = await self._get_image_vector_channel()
            stub = image_vector_pb2_grpc.ImageVectorServiceStub(channel)

            request = image_vector_pb2.ImageRequest(image=img_data, mime="image/jpeg")
            # Добавляем таймаут 60 секунд для обработки изображения
            response = await stub.GetVector(request, timeout=60.0)

            return list(response.vector)

        except UnidentifiedImageError as e:
            logger.error(f"Ошибка обработки изображения {image_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения вектора для изображения {image_url}: {e}")
            return None

    async def _process_product_characteristics(self, wbcard: WBCard) -> List[List[Any]]:
        """Обработать характеристики товара и получить векторы для слов"""
        product_data = wbcard.card_json
        characteristics_words = []

        try:
            characteristics = product_data.get("characteristics", [])
        except KeyError:
            logger.error(f"Карточка {wbcard.nmid} не содержит характеристик")
            characteristics = []

        for characteristic in characteristics:
            char_name = characteristic["name"].lower()
            char_value = characteristic["value"]

            if not isinstance(char_value, list) or all(
                str(x).replace(".", "").replace("-", "").isdigit() for x in char_value
            ):
                continue

            words = []
            for word in char_value:
                if isinstance(word, str):
                    word_vector = await self._get_text_vector(word.lower())
                    if word_vector is not None:
                        words.append([word.lower(), word_vector])

            if words:
                characteristics_words.append([char_name, words])

        # Добавляем название товара
        name_words = []
        name_vector = await self._get_text_vector(wbcard.name)
        if name_vector is not None:
            name_words.append([wbcard.name.lower(), name_vector])

        if name_words:
            characteristics_words.append(["name", name_words])

        # Добавляем описание если есть
        if hasattr(wbcard, "description") and wbcard.description:
            desc_words = []
            desc_vector = await self._get_text_vector(wbcard.description)
            if desc_vector is not None:
                desc_words.append([wbcard.description.lower(), desc_vector])

            if desc_words:
                characteristics_words.append(["description", desc_words])

        return characteristics_words

    async def update_item(self, adv: AdvSetting) -> None:
        """Обновить товар в Neo4j"""
        for nmid in adv.nmids:
            try:
                logger.debug(f"Обработка товара {nmid}")

                # Получаем данные карточки из БД
                async with sm() as session:
                    stmt = select(WBCard).where(WBCard.nmid == nmid)
                    result = await session.execute(stmt)
                    wbcard: WBCard = result.scalar()

                    if not wbcard:
                        logger.debug(f"Карточка {nmid} не найдена в БД")
                        continue

                # Получаем вектор изображения
                image_vector = None
                image_dhash = None
                if wbcard.photos:
                    main_image_url = wbcard.photos[0]
                    logger.info(
                        f"Начало получения вектора изображения для {nmid}: {main_image_url}"
                    )
                    image_vector = await self._get_image_vector(main_image_url)
                    logger.info(
                        f"Вектор изображения получен для {nmid}, размер: {len(image_vector) if image_vector else 0}"
                    )
                    # В реальном проекте dhash должен вычисляться
                    image_dhash = f"dhash_{nmid}"

                # Обрабатываем характеристики
                logger.info(f"Начало обработки характеристик товара {nmid}")
                characteristics = await self._process_product_characteristics(wbcard)
                logger.info(
                    f"Характеристики обработаны для {nmid}, количество: {len(characteristics)}"
                )

                # Обновляем в Neo4j
                logger.info(f"Начало записи в Neo4j для товара {nmid}")
                await self.upsert_item(
                    nmid=nmid,
                    name=wbcard.name,
                    description=getattr(wbcard, "description", ""),
                    brand=wbcard.brand,
                    category_name=wbcard.wb_category.wb_category_name,
                    characteristics=characteristics,
                    image_vector=image_vector,
                    image_dhash=image_dhash,
                )

                logger.info(f"Товар {nmid} успешно обновлен в Neo4j")

            except Exception as e:
                logger.error(f"Ошибка обновления товара {nmid}: {e}", exc_info=True)

    async def update_keyword_phrase(self, text: str) -> None:
        try:
            phrase_data = await self._get_phrase_data(text)
        except Exception as exc:
            logger.error(f"Ошибка получания phrase_data {exc}")
            raise exc
        logger.debug("Phrase Data получена")
        phrase_data_list = [phrase_data]
        await self._add_keyword_phrase(phrase_data_list)

    async def _get_phrase_data(self, text: str):
        logger.debug(f"Обработка ключевой фразы: {text}")

        # Получаем вектор для всей фразы
        phrase_vector = await self._get_average_text_vector_from_phrase(text)
        if phrase_vector is None:
            logger.debug(f"Не удалось получить вектор для фразы '{text}'")
            return

        # Разбиваем фразу на слова и получаем векторы для каждого
        words = text.split()
        keyword_stats = []

        for word in words:
            word_vector = await self._get_average_text_vector_from_phrase(word)
            if word_vector is not None:
                keyword_stats.append(KeywordStatForNeo(text=word, vector=word_vector))

        if not keyword_stats:
            logger.debug(f"Не удалось получить векторы для слов в фразе '{text}'")
            return

        # Создаем объект KeywordPhrase
        phrase_data = KeywordPhrase(
            text=text,
            words=keyword_stats,
            word2vec=phrase_vector,
        )
        return phrase_data

    async def _add_keyword_phrase(self, phrase_data_list: list[KeywordPhrase]) -> None:
        from .neo4j_manager import Neo4jManager

        manager = Neo4jManager()
        await manager.add_keyword_phrase(phrase_data_list)

    async def _get_average_text_vector_from_phrase(self, phrase: str):
        import numpy as np

        phrase = text_cleaner.clear(phrase)
        words = phrase.split()
        vectors = []
        null_vectors = 0
        for word in words:
            vector = await self._get_text_vector(word)
            # Добавляем только если это непустой список чисел
            if (
                isinstance(vector, list)
                and len(vector) > 0
                and all(isinstance(x, (float, int)) for x in vector)
            ):
                vectors.append(vector)
            else:
                null_vectors += 1

        if vectors:
            return (
                np.sum(np.array(vectors), axis=0) / (len(vectors) + null_vectors)
            ).tolist()
        else:
            return None  # В случае, если в предложении не было слов из словаря модели

    async def close_channels(self) -> None:
        """Закрыть gRPC каналы"""
        if self._word2vec_channel:
            await self._word2vec_channel.close()
            self._word2vec_channel = None

        if self._image_vector_channel:
            await self._image_vector_channel.close()
            self._image_vector_channel = None
