import asyncio
import hashlib
import logging
import os
from app.session_maker import get_async_session_maker

from app.NeoDataScience.driver import DataScience
from .ABC_manager import AbcManager
from .data_managers import DataGetter
from neo4j import exceptions
from sqlalchemy import select
import datetime

from .models import ItemFeature, KeywordFeature

logger = logging.getLogger(__name__)

sm = get_async_session_maker()


class GraphUpdater:
    _hash_file_path = os.path.join(AbcManager.data_folder, 'hash.txt')
    _gds = DataScience()
    _data_getter = DataGetter()

    def __init__(self):
        self._word2vec = None



    def __calculate_file_hash(self, filepath):
        """Вычисляет SHA256 хеш файла."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:  # Читаем файл в бинарном режиме
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()




    def linking_keywords(self):
        self._gds.linking_keywords()


    def _check_file_hash(self):
        if os.path.exists(self._hash_file_path):
            with open(self._hash_file_path, 'r') as file:
                hash_in_file = file.read()
        hash_now = self.__calculate_file_hash(self._hash_file_path)
        return hash_now == hash_in_file


    async def update_graph_run(self, leingth: int):
        await self._gds.linking_images_and_keyword()
        while True:
            try:
                await self._gds.update_fastrp(leingth)
                break
            except exceptions.Neo4jError as e:
               if "a job running with jobId 'fastrp'" in e.message:
                    while True:
                        try:
                            fastrp_status = await self._data_getter.listProgress('fastrp')
                            logger.info(f'Выполнено на {fastrp_status[0]}')
                            await asyncio.sleep(60)  # Подождите немного перед повторной попыткой
                        except:
                            break
                    break

               else:
                    raise  # Перебросить исключение, если ошибка не связана с выполняющимся заданием



    async def get_nmids_and_keyword_featers_for_ml(self,  saving_data_for_predictor: asyncio.Event):
        nmids_vectors: list[tuple[int, list[float]]] = await self._gds.get_nmid_vectors()
        keywords_vectors: list[tuple[str, list[float]]] = await self._gds.get_keywords_vectors()
        timestamp = datetime.datetime.now()
        async with sm() as session:
            for nmid, vector in nmids_vectors:
                stmt = select(ItemFeature).where(ItemFeature.nmid == nmid)
                item = await session.execute(stmt)
                item = item.scalar()
                if not item:
                    item = ItemFeature(nmid=nmid, vector=vector)
                else:
                    item.vector = vector
                item.timestamp = timestamp
                session.add(item)
            for keyword_text, vector in keywords_vectors:
                stmt = select(KeywordFeature).where(KeywordFeature.keyword == keyword_text)
                keyword = await session.execute(stmt)
                keyword = keyword.scalar()
                if not keyword:
                    keyword = KeywordFeature(keyword=keyword_text, vector=vector)
                else:
                    keyword.vector = vector
                keyword.timestamp = timestamp
                session.add(keyword)
                await session.commit()
            saving_data_for_predictor.clear()

