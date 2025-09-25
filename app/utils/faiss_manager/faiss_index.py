import logging
import os
from collections.abc import Generator
from typing import Any, Union

import faiss # type: ignore
import numpy as np
import sqlalchemy
from sqlalchemy.orm import Query

logger = logging.getLogger(__name__)


class Index:
    def __init__(
        self,
        objects: Query[Any] | list[Any],
        vector_property_name: str,
        file_path: str,
        index_type: str,
        batch_size: int,
    ) -> None:
        self._objects = objects
        self._vector_property_name = vector_property_name
        self._file_path = file_path
        self._index_type = index_type
        self._batch_size = batch_size

        self.index: faiss.IndexIDMap
        if not os.path.exists(file_path):
            self.index = self.__create_new_index(objects, vector_property_name, file_path, index_type, batch_size)
        else:
            try:
                loaded_index = faiss.read_index(file_path)
                ntotal = loaded_index.ntotal
                if isinstance(objects, Query):
                    total = objects.count()
                else:
                    total = len(objects)
                if ntotal != total:
                    self.index = self.__create_new_index(objects, vector_property_name, file_path, index_type, batch_size)
                else:
                    self.index = loaded_index
            except RuntimeError as exc:
                logger.error(exc)
                del exc
                self.index = self.__create_new_index(objects, vector_property_name, file_path, index_type, batch_size)

    def __create_new_index(
        self,
        objects: Query[Any] | Generator[Any, Any, Any] | list[Any],
        vector_property_name: str,
        file_path: str,
        index_type: str,
        batch_size: int,
    ) -> faiss.IndexIDMap:
        first_object_vector = None
        if isinstance(objects, Query):
            first_object = objects.first()
            if first_object:
                first_object_vector = getattr(first_object, vector_property_name)
        elif isinstance(objects, list) and objects:
            first_object_vector = getattr(objects[0], vector_property_name)
        
        if first_object_vector is None:
            raise ValueError("Cannot create index from empty objects or objects without vector property.")

        index = getattr(faiss, index_type)(len(first_object_vector))
        index = faiss.IndexIDMap(index)

        vectors: list[np.ndarray[Any, Any]] = []
        ids: list[int] = []

        if isinstance(objects, Query):
            objects_iter = objects.yield_per(batch_size)
        else:
            objects_iter = objects # type: ignore

        for obj in objects_iter:
            vector = getattr(obj, vector_property_name)
            vectors.append(vector)
            ids.append(obj.id)

            if len(vectors) == batch_size:
                vectors_np = np.array(vectors, dtype=np.float32)
                ids_np = np.array(ids, dtype=np.int64)
                faiss.normalize_L2(vectors_np)
                index.add_with_ids(vectors_np, ids_np)

                vectors = []
                ids = []

        if vectors:
            vectors_np = np.array(vectors, dtype=np.float32)
            ids_np = np.array(ids, dtype=np.int64)
            faiss.normalize_L2(vectors_np)
            index.add_with_ids(vectors_np, ids_np)

        faiss.write_index(index, file_path)
        return index

    def get_near_object_id(self, vector: list[float]) -> int:
        vector_matrix = np.expand_dims(vector, axis=0)
        distances, ids = self.index.search(vector_matrix, k=1)
        return int(ids[0][0])

    def save_index(self) -> None:
        if self.index.ntotal > 0:
            faiss.write_index(self.index, self._file_path)

    @property
    def objects(self) -> Query[Any] | list[Any]:
        return self._objects
