import logging
import os
import pickle
from collections.abc import Generator
from typing import Any, Union, cast

import faiss # type: ignore
from sqlalchemy.orm import Query, sessionmaker

from app.modules.common_slaves.wildberries.models.models import AdvKeyword
from app.utils.image_master.database.model import Image
from app.utils.NeoDataScience.driver import DataScience as Neo4jDriver

from .faiss_index import Index

logger = logging.getLogger(__name__)


class FaissManager:
    def __init__(
        self,
        session_maker: sessionmaker[Any],
        neo4j_driver: Neo4jDriver,
        batch_size: int = 300,
    ) -> None:
        self._session_maker = session_maker
        self._neo4j = neo4j_driver
        self._batch_size = batch_size
        self._index_save_list: list[list[Any]] = []

        self._images_in_items: Index | None = None
        self._keywords: Index | None = None
        self._keyword_phrases: Index | None = None
        self._all_images: Index | None = None
        self._background_images: Index | None = None

    async def load_indexes(
        self,
        load_keywords: bool = False,
        load_images: bool = False,
        load_keyword_phrase: bool = False,
    ) -> None:
        if load_images:
            self._images_in_items = await self._get_images_in_items_index("IndexFlatL2")
            print("Индекс images_in_items загружен")
        if load_keywords:
            self._keywords = await self._get_keywords_index("word2vec")
            print("Индекс keywords загружен")
        if load_keyword_phrase:
            self._keyword_phrases = await self.get_keyword_phrases_index()
            print("Индекс keyword_phrases загружен")

    def __enter__(self) -> "FaissManager":
        return self

    @property
    def keywords(self) -> Index | None:
        return self._keywords

    def __exit__(
        self, exc_type: Any, exc_val: Any, exc_tb: Any
    ) -> None:
        self.save_indexes()

    @property
    def all_images(self) -> Index | None:
        return self._all_images

    @property
    def background_images(self) -> Index | None:
        return self._background_images

    @property
    def images_in_items(self) -> Index | None:
        return self._images_in_items

    @property
    def keyword_phrases(self) -> Index | None:
        return self._keyword_phrases

    @staticmethod
    def __get_file_path(file_name: str) -> str:
        index_folder = "indexes"
        current_directory = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_directory, index_folder, file_name)
        return file_path

    async def _get_all_images_index(self) -> Index:
        file_name = "all_images.index"
        file_path = self.__get_file_path(file_name)
        with self._session_maker() as s:
            images = s.query(Image).filter(Image.is_background.is_not(True)).all()
            index = Index(
                images,
                "vector",
                file_path,
                index_type="IndexFlatL2",
                batch_size=self._batch_size,
            )
            self._index_save_list.append([file_path, index])
            return index

    def __get_index(self, objects: Query[Any] | list[Any], file_path: str, vector_property_name: str, index_type: str) -> Index:
        index_instance = Index(
            objects,
            vector_property_name,
            file_path,
            index_type,
            self._batch_size,
        )
        return index_instance

    async def _get_background_images_index(self) -> Index:
        file_name = "background_images.index"
        file_path = self.__get_file_path(file_name)
        with self._session_maker() as s:
            images = s.query(Image).filter(Image.is_background.is_(True)).all()
            index = Index(
                images,
                "vector",
                file_path,
                index_type="IndexFlatL2",
                batch_size=self._batch_size,
            )
            self._index_save_list.append([file_path, index])
            return index

    def save_indexes(self) -> None:
        for _path, index in self._index_save_list:
            index.save_index()

    @staticmethod
    def __get_new_objects(objects: Query[Any], pickle_file_path: str) -> list[Any]:
        images = objects.all()
        with open(pickle_file_path, "wb") as file_write:
            pickle.dump(images, file_write)
        return images

    def _get_objects(self, objects: Query[Any], pickle_file_path: str) -> list[Any]:
        if not os.path.exists(pickle_file_path):
            objects_list = objects.all()
            with open(pickle_file_path, "wb") as file_write:
                pickle.dump(objects_list, file_write)
            return objects_list
        else:
            try:
                with open(pickle_file_path, "rb") as file_read:
                    loaded_objects = cast(list[Any], pickle.load(file_read))
                    if len(loaded_objects) != objects.count():
                        objects_list = objects.all()
                        with open(pickle_file_path, "wb") as file_write:
                            pickle.dump(objects_list, file_write)
                        return objects_list
                    else:
                        return loaded_objects
            except Exception:
                objects_list = objects.all()
                with open(pickle_file_path, "wb") as file_write:
                    pickle.dump(objects_list, file_write)
                return objects_list

    async def _get_images_in_items_index(self, index_type: str) -> Index:
        index_name = "images_in_items"
        index_file_name = index_name + ".index"
        index_file_path = self.__get_file_path(index_file_name)
        with self._session_maker() as s:
            # Image.items не определен на модели Image. Возможно, подразумевается связь через другую таблицу
            # или запрос должен быть другим. Для примера, пока что просто выбираем все Image объекты.
            # Если Image должна быть связана с Item, необходимо определить эту связь в app/utils/image_master/database/model.py
            images = s.query(Image).all() # temporarily select all images to pass mypy
            # images = s.query(Image).join(Image.items).filter(Image.items.any()).distinct(Image.id)
            index = Index(
                images,
                "vector",
                index_file_path,
                index_type,
                self._batch_size,
            )
            self._index_save_list.append([index_file_path, index])
            return index

    async def _get_keywords_index(self, vector_property: str) -> Index:
        file_name = "keyword.index"
        file_path = self.__get_file_path(file_name)
        with self._session_maker() as s:
            keywords = s.query(AdvKeyword).filter(getattr(AdvKeyword, vector_property) is not None).all()
            index = Index(
                keywords,
                vector_property,
                file_path,
                index_type="IndexFlatIP",
                batch_size=self._batch_size,
            )
            return index

    async def get_keyword_phrases_index(self) -> Index:
        file_name = "keyword_phrase.index"
        file_path = self.__get_file_path(file_name)
        keyword_phrase = await self._neo4j.get_keyword_phrases()
        index = Index(
            keyword_phrase,
            "vector",
            file_path,
            index_type="IndexFlatIP",
            batch_size=self._batch_size,
        )
        return index
