import asyncio
import hashlib
import logging
import os

from neo4j.exceptions import Neo4jError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.utils.db.session_maker import get_async_session_maker
from app.utils.NeoDataScience.driver import DataScience

from .ABC_manager import AbcManager
from .data_getter import DataGetter
from .models import ItemFeature, KeywordFeature

logger = logging.getLogger(__name__)

sm = get_async_session_maker


class GraphUpdater:
    _hash_file_path = os.path.join(AbcManager.data_folder, "hash.txt")
    _gds = DataScience()
    _data_getter = DataGetter()

    def __init__(self):
        self._word2vec: None = None

    @staticmethod
    def __calculate_file_hash(filepath):
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
            with open(self._hash_file_path) as file:
                hash_in_file = file.read()
        hash_now = self.__calculate_file_hash(self._hash_file_path)
        return hash_now == hash_in_file

    async def update_graph_run(self, leingth: int) -> None:
        await self._gds.linking_images_and_keyword()
        while True:
            try:
                await self._gds.update_fastrp(leingth)
                break
            except Neo4jError as e:
                message = e.message
                if message and "a job running with jobId 'fastrp'" in message:
                    while True:
                        try:
                            fastrp_status = await self._data_getter.get_list_progress("fastrp")
                            logger.info(f"Выполнено на {fastrp_status[0]}")
                            await asyncio.sleep(60)  # Подождите немного перед повторной попыткой
                        except Exception:
                            break
                    break
                else:
                    raise e  # Перебросить исключение, если ошибка не связана с выполняющимся заданием

    async def _update_nmids_vectors(self) -> None:
        async with sm() as session:
            stmt = select(ItemFeature.nmid)
            result = await session.execute(stmt)
            nmids = result.scalars().all()
        nmids = list(nmids)
        nmids_vectors: list[tuple[int, list[float]]] = await self._gds.get_nmid_vectors(nmids)

        async with sm(read_only=False) as session:
            for nmid, vector in nmids_vectors:
                stmt = (
                    pg_insert(ItemFeature)
                    .values(nmid=nmid, vector=vector)
                    .on_conflict_do_update(
                        index_elements=["nmid"],  # Specify the column(s) that trigger a conflict
                        set_={"vector": vector},  # Specify which columns to update
                    )
                )
                await session.execute(stmt)
            await session.commit()
        logger.debug("Вектора для nmids обновлены")

    async def _update_keywords_vectors(self) -> None:
        keywords_vectors: list[tuple[str, list[float]]] = await self._gds.get_keywords_vectors()
        async with sm(read_only=False) as session:
            count = 0  # Счетчик для отслеживания количества обработанных записей
            BATCH_SIZE = 100  # Размер порции для коммита
            for keyword_text, vector in keywords_vectors:
                stmt = select(KeywordFeature).where(KeywordFeature.keyword == keyword_text)
                result = await session.execute(stmt)
                existing_keyword = result.scalar()
                if existing_keyword:
                    existing_keyword.vector = vector
                    keyword = existing_keyword
                    keyword.vector = vector
                else:
                    keyword = KeywordFeature(keyword=keyword_text, vector=vector)
                    session.add(keyword)
                count += 1  # Увеличиваем счетчик на 1
                if count % BATCH_SIZE == 0:  # Если достигнут размер порции
                    await session.commit()  # Выполняем коммит
                    logger.debug("Промежуточный коммит выполнен")

            if count % BATCH_SIZE != 0:  # Если после последнего коммита остались несохраненные записи
                await session.commit()  # Выполняем окончательный коммит
                logger.debug("Вектора для ключей обновлены")
