import asyncio
import logging
import re
from io import BytesIO

import aiohttp
import faiss
import numpy as np
from PIL import Image as PilImage, UnidentifiedImageError
from sqlalchemy import select, Row, Sequence

from app.modules.common_slaves.wildberries.models import (
    KeywordSetting,
    AdvSetting,
    WBCard,
)
from app.modules.wb_adv_updater.ML import Predictor
from app.utils.db.session_maker import get_async_session_maker as sm
from app.utils.image_master import image_tools
from app.utils.image_master.image_master2 import ImageMaster
from .gds_object import gds
from .update_wb_adv_phrases_in_neo import update_wb_adv_phrases_in_neo
from .word_to_vec_object import word2vec
from ...core.redis_manager.base_redis_manager import BaseRedis
from ...utils import redis_manager, text_cleaner

logger = logging.getLogger(__name__)
from . import fitter

predictor = Predictor()


image_master = ImageMaster()

keywords_hashs_in_neo = set()


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


async def get_words_from_char_value(char_value) -> list[tuple[str, list[float]]]:
    if isinstance(char_value, list):
        char_value = " ".join(char_value)
    words = re.split(r"[ ,\.]+", char_value)
    words = list(filter(None, words))
    groups = []
    for word in words:
        word = word.lower()
        vector: list[float] = await word2vec.average_vector_from_sentence(word)
        groups.append(
            (
                word,
                vector,
            )
        )

    return groups


async def process_product_data(wbcard: WBCard):
    product_data = wbcard.card_json
    # Обработка характеристик
    characteristics_words = {}
    try:
        characteristics = product_data["characteristics"]
    except KeyError:
        logger.error(f"Карточка {wbcard.nmid} не содержит характеристик")
        characteristics = []
    for characteristic in characteristics:
        char_name = characteristic["name"].lower()
        char_value = characteristic["value"]
        if not isinstance(char_value, list) or all(is_number(x) for x in char_value):
            continue
        characteristics_words[char_name]: tuple[str, list[float]] = (
            await get_words_from_char_value(char_value)
        )
    characteristics_words["name"]: tuple[str, list[float]] = (
        await get_words_from_char_value(wbcard.name)
    )
    if "description" in characteristics_words:
        characteristics_words["description"]: tuple[str, list[float]] = (
            await get_words_from_char_value(wbcard.description)
        )
    return characteristics_words


async def __update_cards_in_graph_for_shops(adv_settings: list[AdvSetting]):
    all_nmids = set()
    for adv in adv_settings:
        nmids = adv.nmids
        if not nmids:
            continue
        for nmid in nmids:
            all_nmids.add(nmid)
    if not all_nmids:
        return
    for nmid in all_nmids:
        check_in_neo_by_redis = await gds.check_wb_card_in_neo(nmid)
        try:
            if check_in_neo_by_redis:
                logger.debug(f"Карточка {nmid} уже есть в базе данных")
                continue
            logger.debug(f"Запрашиваем карточку {nmid}")
            async with sm() as session:
                stmt = select(WBCard).where(WBCard.nmid == nmid)
                result = await session.execute(stmt)
                wbcard: WBCard = result.scalar()
                if not wbcard:
                    logger.debug(f"Карточка {nmid} не найдена")
                    continue
                logger.debug(f"Получили карточку {nmid}")
                main_image_url: str = wbcard.photos[0]
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(main_image_url) as response:
                        image_bytes = await response.read()
                        pil_image = PilImage.open(BytesIO(image_bytes))
                characteristics_word = await process_product_data(wbcard)
                vector = await asyncio.to_thread(image_master.get_vector, pil_image)
                dhash = await asyncio.to_thread(image_tools.dhash, pil_image)
                logger.debug(f"Обновляем карточку: {wbcard.name}")
            try:
                await gds.update_wb_card(
                    wbcard, characteristics_word, dhash, vector
                )  # Подтверждение изменений в базе данных
            except Exception:
                logger.error(f"Ошибка обновления карточки:  {wbcard.nmid}")
        except KeyError as exc:
            if exc.args[0] == "photos":
                logger.debug(
                    f"Карточка {wbcard.nmid} не содержит изображений, возможно, карточка не существует"
                )
            else:
                logger.error(
                    f"Ошибка при добавлении карточки в neo4j {wbcard.nmid}: {exc}"
                )
        except UnidentifiedImageError as exc:
            logger.error(
                f"Ошибка UnidentifiedImageError при обработке изображения nmid"
                f" {wbcard.nmid}, url: {main_image_url}: {exc}",
                exc_info=True,
            )


async def update_cards_in_graph_for_shops_big_cycle():
    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.active_status == "pause")
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.scalars().all()
    await __update_cards_in_graph_for_shops(adv_settings)


async def update_cards_in_graph_small_cycle():
    async with sm() as session:
        stmt = select(AdvSetting).where(
            AdvSetting.bot_active == True,
        )
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.scalars().all()
    await __update_cards_in_graph_for_shops(adv_settings)


async def fit_and_save_model():
    await fitter.getGradientBoostingFullFitModel()


async def update_model():
    logger.debug("Старт обучения и сохранения модели")
    await fit_and_save_model()
    logger.debug("Устанавливаю сет, разрешаю обновление ключей")


async def update_wb_adv_phrase_in_neo_small_cycle():
    try:
        await update_wb_adv_phrases_in_neo()
    except:
        logger.error("Ошибка обновления фраз в neo", exc_info=True)
        raise


async def update_wb_adv_phrase_in_neo4j():
    while True:
        try:
            await update_wb_adv_phrase_in_neo_small_cycle()
        except:
            logger.error("Ошибка обновления фраз в neo", exc_info=True)
        await asyncio.sleep(0)


index = None
keywords = []


async def update_keywords_ctr_by_similary():
    global index, keywords
    async with sm() as session:
        stmt = (
            select(KeywordSetting.text, AdvSetting.adv_id)
            .join(AdvSetting, KeywordSetting.adv_setting_id == AdvSetting.id)
            .where(AdvSetting.bot_active == True)
        )
        result = await session.execute(stmt)
        keyword_texts_adv_ids: Sequence[Row[tuple[str, int]]] = result.all()

    # Получение ключей из Redis
    keys = await redis_manager.get_keys("predict_ctr*")
    if not keys:
        return

    vectors = []
    new_keywords = []  # Для новых ключевых слов

    for key in keys:
        key = key.decode("utf-8")
        try:
            adv_id, keyword_text = key.split(":")[1:]
        except Exception:
            logger.error(f"Ошибка парсинга ключа {key}", exc_info=True)
            continue
        if keyword_text in keywords:
            continue
        vector = await word2vec.average_vector_from_sentence(keyword_text)
        if vector is not None:
            vector = np.array(vector, dtype=np.float32)
            vectors.append(vector)
            new_keywords.append(
                (
                    adv_id,
                    keyword_text,
                )
            )

    # Добавление векторов в индекс
    if vectors:
        vectors_np = np.array(vectors, dtype=np.float32)
        if index is None:
            d = vectors_np.shape[1]  # Размерность векторов
            index = faiss.IndexFlatL2(d)  # Создание нового индекса
            index = faiss.IndexIDMap(index)  # Создание IDMap для индекса
        ids = np.arange(len(new_keywords), dtype=np.int64)
        faiss.normalize_L2(vectors_np)
        index.add_with_ids(vectors_np, ids)
        keywords.extend(new_keywords)  # Обновление списка ключевых слов

    # Поиск и обновление данных

    for keyword_text_adv_id in keyword_texts_adv_ids:
        target_text = keyword_text_adv_id[0]
        target_text = text_cleaner.clear(target_text)
        if not target_text:
            continue
        target_adv_id = keyword_text_adv_id[1]
        logger.debug(
            f"Обработка ключевого слова {target_text} для объявления {target_adv_id}"
        )
        original_predict_ctr = await redis_manager.get_predict_ctr(
            target_adv_id, target_text
        )
        if original_predict_ctr:
            continue
        vector = await word2vec.average_vector_from_sentence(target_text)
        if vector is None:
            continue
        vector = np.array(vector, dtype=np.float32)
        vector = vector.reshape(1, -1)  # Преобразование в форму (1, d) для поиска

        # Поиск ближайших векторов
        D, I = index.search(vector, index.ntotal)
        redis_base_manager = BaseRedis()
        async with redis_base_manager.client.pipeline() as redis_pipeline:
            for idx in I[0]:
                if idx == -1:
                    break
                adv_id, text = keywords[idx]
                adv_id = int(adv_id)
                if text == target_text:
                    continue
                if adv_id != target_adv_id:
                    continue
                predict_ctr = await redis_manager.get_predict_ctr(adv_id, text)
                if predict_ctr:
                    logger.debug(
                        f"Обновление CTR для ключевого слова {target_text} и объявления {adv_id} "
                        f"на значение {predict_ctr}"
                    )
                    await redis_manager.set_predict_ctr_with_pipeline(redis_pipeline,
                                                                      adv_id,
                                                                      target_text,
                                                                      predict_ctr)
                    break
            await redis_pipeline.execute()