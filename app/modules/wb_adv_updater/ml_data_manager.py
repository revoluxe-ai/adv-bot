import asyncio
import hashlib
import re
from datetime import datetime
from io import BytesIO
from app.utils.image_master import image_tools
import aiohttp
from sqlalchemy import select, or_
from app.modules.common_slaves.wildberries.models import KeywordSetting, AdvSetting, WBCard, WBCabinet
from app.utils.NeoDataScience.driver import DataScience
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.common_slaves.wildberries.data_classes.namedtuples import KeywordStatForNeo, KeywordPhrase
from app.modules.wb_adv_updater.ML import Predictor, Fitter
from app.utils.image_master.image_master2 import ImageMaster
from app.utils.text_master.Transformers import Word2Vec
import logging
from PIL import Image as PilImage, UnidentifiedImageError

from ...utils import redis_manager, text_cleaner
from ...utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)
from . import fitter

predictor = Predictor()
word2vec = Word2Vec()
gds = DataScience()
image_master = ImageMaster()

keywords_hashs_in_neo = set()


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


async def get_words_from_char_value(char_value):
        if isinstance(char_value, list):
            char_value = " ".join(char_value)
        words = re.split(r'[ ,\.]+', char_value)
        words = list(filter(None, words))
        groups = []
        for word in words:
            word =  word.lower()
            vector = await word2vec.average_vector_from_sentence(word)
            groups.append((word, vector,))

        return groups



async def process_product_data(wbcard: WBCard):
    product_data = wbcard.card_json
    # Обработка характеристик
    characteristics_words = {}
    for characteristic in product_data["characteristics"]:
        char_name = characteristic['name'].lower()
        char_value = characteristic['value']
        if not isinstance(char_value, list) or all(
                is_number(x) for x in char_value):
            continue
        characteristics_words[char_name]: tuple(str, list[float]) = await get_words_from_char_value(char_value)
    characteristics_words['name']: tuple(str, list[float]) = await get_words_from_char_value(wbcard.name)
    if 'description' in characteristics_words:
        characteristics_words['description']: tuple(str, list[float]) = await get_words_from_char_value(
            wbcard.description)
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
    async with sm() as session:
        stmt = select(WBCard).where(WBCard.nmid.in_(all_nmids))
        wbcards: list[WBCard] = await session.stream(stmt)
        async for wbcard in wbcards.scalars():
            try:
                 check_in_neo = await gds.check_wb_card_in_neo(wbcard.nmid)
                 if check_in_neo:
                     continue
            except Exception:
                logger.error(f'Ошибка чека карты в neo Артикул: {wbcard.nmid} ', exc_info=True)
            try:
                main_image_url: str = wbcard.photos[0]
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(main_image_url) as response:
                        image_bytes = await response.read()
                        pil_image = PilImage.open(BytesIO(image_bytes))
                characteristics_word = await process_product_data(wbcard)
                vector = await asyncio.to_thread(image_master.get_vector, pil_image)
                dhash = await asyncio.to_thread(image_tools.dhash, pil_image)
                logger.debug(f"Обновляем карточку: {wbcard.name}")
                await gds.update_wb_card(wbcard, characteristics_word, dhash,
                                         vector)  # Подтверждение изменений в базе данных
            except KeyError as exc:
                if exc.args[0] == 'photos':
                    logger.debug(f"Карточка {wbcard.nmid} не содержит изображений, возможно, карточка не существует")
                else:
                    logger.error(f"Ошибка при добавлении карточки в neo4j {wbcard.nmid}: {exc}")
            except UnidentifiedImageError as exc:
                logger.error(f"Ошибка UnidentifiedImageError при обработке изображения nmid"
                             f" {wbcard.nmid}, url: {main_image_url}: {exc}", exc_info=True)




async def update_cards_in_graph_for_shops_big_cycle():
    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.active_status == 'pause')
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.scalars().all()
    await __update_cards_in_graph_for_shops(adv_settings)



async def update_cards_in_graph_small_cycle():
    async with sm() as session:
        stmt = select(AdvSetting) \
            .where(or_(AdvSetting.bot_active == True,
                       AdvSetting.active_status == 'active'))
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.scalars().all()
    await __update_cards_in_graph_for_shops(adv_settings)



async def fit_and_save_model():
    await fitter.getGradientBoostingFullFitModel()

async def update_model():
    logger.debug('Старт обучения и сохранения модели')
    await fit_and_save_model()
    logger.debug('Устанавливаю сет, разрешаю обновление ключей')


def get_text_hash(text):
    hash_text = hashlib.md5(text.encode()).hexdigest()
    return hash_text


async def get_phrase_data(text):
    words = text.split()
    keywords = []
    for word in words:
        vector = await word2vec.average_vector_from_sentence(word)
        if vector is not None:
            vector = list(vector)
        keywords.append(KeywordStatForNeo(text=word, vector=vector))
        await asyncio.sleep(0)

    phrase_data = KeywordPhrase(
        text=text,
        words=keywords,
        word2vec=await word2vec.average_vector_from_sentence(text)
    )

    return phrase_data

async def update_wb_adv_phrase_in_neo_small_cycle():
    batch_size = 100
    phrase_data_list = []
    async with sm() as session:
        stmt = select(AdvSetting.adv_id)\
        .where(AdvSetting.active_status.in_(['started']),
               AdvSetting.bot_active == True)
        adv_ids = await session.execute(stmt)
        adv_ids = adv_ids.scalars().all()

    async with get_clickhouse_client() as ch_client:
        query = f'SELECT DISTINCT text FROM default_db.advkeyword WHERE adv_id IN {adv_ids}'
        result = await ch_client.query(query)
        texts = [text[0] for text in result.result_rows]
        clear_texts = set()
        for text in texts:
            clear_text = text_cleaner.clear(text)
            clear_texts.add(clear_text)
            cluster = await redis_manager.get_cluster_name(clear_text)
            logger.debug(f'Имя кластера: {cluster}')
            if cluster:
               clear_texts.add(cluster)
        texts = clear_texts
        for text in texts:
            hash_text = get_text_hash(text)
            check_in_neo_by_redis = await redis_manager.check_phrase_in_neo(hash_text)
            if check_in_neo_by_redis:
                logger.debug(f'Фраза {text} уже есть в базе данных')
                await asyncio.sleep(0)
                continue
            if await gds.check_phrase_in_neo(text):
                logger.debug(f'Фраза {text} уже есть в базе данных')
                await redis_manager.add_phrase_hash_like_is_in_neo(hash_text)
                await asyncio.sleep(0)
                continue
            logger.debug(f'Записываем в нео фразу {text}')
            phrase_data = await get_phrase_data(text)
            await redis_manager.add_phrase_hash_like_is_in_neo(hash_text)
            phrase_data_list.append(phrase_data)
            # Записываем, если набрался полный батч
            if len(phrase_data_list) >= batch_size:
                await gds.add_keyword_phrase(phrase_data_list)
                phrase_data_list.clear()
            await asyncio.sleep(0)

    # Записываем оставшиеся данные, если они есть
    if phrase_data_list:
        await gds.add_keyword_phrase(phrase_data_list)
        await asyncio.sleep(0)
    pass

async def update_wb_adv_phrase_in_db():
    while True:
       try:
           await update_wb_adv_phrase_in_neo_small_cycle()
       except:
           logger.error('Ошибка обновления фраз в neo', exc_info=True)
       await asyncio.sleep(0)

