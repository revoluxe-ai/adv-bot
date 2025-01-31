import asyncio

from sqlalchemy import select

from .gds_object import gds
from .word_to_vec_object import word2vec
from .get_text_hash import get_text_hash
from ..common_slaves.wildberries.data_classes.namedtuples import KeywordPhrase
from ...core.wb_api.data_classes.namedtuples import KeywordStatForNeo
from ...utils.click_house.client import get_clickhouse_client
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm
from ...utils import redis_manager, text_cleaner
import logging


logger = logging.getLogger(__name__)


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



async def update_wb_adv_phrases_in_neo():
    batch_size = 5
    phrase_data_list = []
    async with sm() as session:
        stmt = select(AdvSetting.adv_id) \
            .where(
                   AdvSetting.bot_active == True)
        adv_ids = await session.execute(stmt)
        adv_ids = adv_ids.scalars().all()
    adv_ids = [adv for adv in adv_ids if adv]

    async with get_clickhouse_client() as ch_client:
        query = f'SELECT DISTINCT text FROM default_db.advkeyword WHERE adv_id IN {adv_ids}'
        result = await ch_client.query(query)
        texts = [text[0] for text in result.result_rows]
        clear_texts = set()
        for text in texts:
            clear_text = text_cleaner.clear(text)
            hash_text = get_text_hash(clear_text)
            check_in_neo_by_redis = await redis_manager.check_phrase_in_neo(hash_text)
            if not check_in_neo_by_redis:
                clear_texts.add(clear_text)
            cluster, _ = await redis_manager.get_cluster_and_preset(text)
            if cluster:
                cluster = text_cleaner.clear(cluster)
                hash_text = get_text_hash(cluster)
                check_in_neo_by_redis = await redis_manager.check_phrase_in_neo(hash_text)
                if not check_in_neo_by_redis:
                    clear_texts.add(cluster)
        texts = clear_texts
        for text in texts:
            if await gds.check_phrase_in_neo(text):
                logger.debug(f'Фраза {text} уже есть в базе данных')
                await redis_manager.add_phrase_hash_like_is_in_neo(hash_text)
                continue
            logger.debug(f'Записываем в нео фразу {text}')
            phrase_data = await get_phrase_data(text)
            logger.debug('Phrase Data получена')
            await redis_manager.add_phrase_hash_like_is_in_neo(hash_text)
            phrase_data_list.append(phrase_data)
            # Записываем, если набрался полный батч
            if len(phrase_data_list) >= batch_size:
                await gds.add_keyword_phrase(phrase_data_list)
                phrase_data_list.clear()

    # Записываем оставшиеся данные, если они есть
    if phrase_data_list:
        await gds.add_keyword_phrase(phrase_data_list)
