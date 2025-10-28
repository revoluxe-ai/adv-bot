import asyncio
import hashlib
import logging
import os

from neo4j.exceptions import Neo4jError

from app.utils.db.session_maker import get_async_session_maker
from app.utils.NeoDataScience.driver import DataScience

from .ABC_manager import AbcManager
from .data_getter import DataGetter


logger = logging.getLogger(__name__)

sm = get_async_session_maker


class GraphUpdater:
    _hash_file_path = os.path.join(AbcManager.data_folder, "hash.txt")
    _gds = DataScience()
    _data_getter = DataGetter()

    def __init__(self):
        self._word2vec = None

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

    async def update_graph_run(self, leingth: int):
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
                            fastrp_status = await self._data_getter.get_list_progress(
                                "fastrp"
                            )
                            logger.info(f"Выполнено на {fastrp_status[0]}")
                            await asyncio.sleep(
                                60
                            )  # Подождите немного перед повторной попыткой
                        except:
                            break
                    break
                else:
                    raise e  # Перебросить исключение, если ошибка не связана с выполняющимся заданием


