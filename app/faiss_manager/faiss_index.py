import logging
import os
import faiss
import numpy as np
from typing import List, Union, Generator
import sqlalchemy
from sqlalchemy.orm import Query


logger = logging.getLogger(__name__)


class Index:
    def __init__(self, objects: Union[Query, List], vector_property_name, file_path, index_type, batch_size):
        if not os.path.exists(file_path):
            index = self.__create_new_index(objects, vector_property_name, file_path, index_type, batch_size)
        else:
            try:
                index: faiss.IndexIDMap = faiss.read_index(file_path)
                ntotal = index.ntotal
                # ids = index.id_map
                if isinstance(objects, sqlalchemy.orm.query.Query):
                    total = objects.count()
                else:
                    total = len(objects)
                if ntotal != total:
                    index = self.__create_new_index(objects, vector_property_name, file_path, index_type,  batch_size)
            except RuntimeError as exc:
                logger.error(exc)
                index = self.__create_new_index(objects, vector_property_name, file_path, index_type,  batch_size)
        self.index = index
        self._file_path = file_path



    def __create_new_index(self, objects: Union[Query,Generator], vector_property_name, file_path, index_type, batch_size: int):
        index = getattr(faiss, index_type)(len(getattr(objects[0], vector_property_name)))
        index = faiss.IndexIDMap(index)

        vectors = []
        ids = []

        if isinstance(objects, Query):
            objects = objects.yield_per(batch_size)

        for object in objects:
            vector = getattr(object, vector_property_name)
            vectors.append(vector)
            ids.append(object.id)

            if len(vectors) == batch_size:
                # Конвертируем списки в numpy массивы и добавляем в индекс
                vectors_np = np.array(vectors, dtype=np.float32)
                ids_np = np.array(ids, dtype=np.int64)
                faiss.normalize_L2(vectors_np)
                index.add_with_ids(vectors_np, ids_np)

                # Очистка списков для следующего батча
                vectors = []
                ids = []

        # Обработка оставшихся объектов
        if vectors:
            vectors_np = np.array(vectors, dtype=np.float32)
            ids_np = np.array(ids, dtype=np.int64)
            faiss.normalize_L2(vectors_np)
            index.add_with_ids(vectors_np, ids_np)

        # Сохраняем индекс в файл
        faiss.write_index(index, file_path)
        return index



    def get_near_object_id(self, vector: list[float]):
        vector_matrix = np.expand_dims(vector, axis=0)
        distances, ids = self.index.search(vector_matrix, k=1)
        return ids[0][0]

    def save_index(self):
        if self.index.ntotal > 0:
            faiss.write_index(self.index, self._file_path)

    @property
    def objects(self):
        return self._objects