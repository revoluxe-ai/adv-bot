import logging
from app.utils.image_master.database.model import Image, Keyword
import pickle
import faiss
import os
from typing import List
from sqlalchemy.orm import Query
from typing import Union
from .faiss_index import Index

logger = logging.getLogger(__name__)


class FaissManager:
    def __init__(self, batch_size = 300, load_keywords = False, load_images = False, load_keyword_phrase = False):
        self._batch_size = batch_size
        self._index_save_list = []
        # if all_images:
        #     self._all_images = self._get_all_images_index()
        #     print('Индекс all_images загружен')
        # if background_images:
        #     self._background_images = self._get_background_images_index()
        #     print('Индекс background_images загружен')
        if load_images:
             self._images_in_items = self._get_images_in_items_index( 'IndexFlatL2')
             print('Индекс images_in_items загружен')
        if load_keywords:
            self._keywords = self._get_keywords_index('word2vec')
            print('Индекс keywords загружен')

        if load_keyword_phrase:
            self._keyword_phrases = self.get_keyword_phrases_index('vector')

    def __enter__(self):
        return self

    @property
    def keywords(self):
        return self._keywords

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_indexes()


    @property
    def all_images(self):
        return self._all_images


    @property
    def background_images(self):
        return self._background_images


    @property
    def images_in_items(self):
        return self._images_in_items

    @property
    def keyword_phrases(self):
        return self._keyword_phrases


    @staticmethod
    def __get_file_path(file_name):
        index_folder = 'indexes'
        current_directory = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_directory,index_folder, file_name)
        return file_path


    def _get_all_images_index(self) -> faiss.IndexFlatL2:
        file_name = 'all_images.index'
        file_path = self.__get_file_path(file_name)
        criteria = Image.is_background != True
        index = self.__get_index_by_criteria(file_path, criteria)
        self._index_save_list.append([file_path, index])
        faiss.write_index(index, file_path)
        return index

    def __get_index(self, images:  Union[Query, List[Image]], file_path):
        if not os.path.exists(file_path):
            index = self.__create_new_index(images, file_path)
            return index
        else:
            try:
                index = faiss.read_index(file_path)
                ntotal = index.ntotal
            except RuntimeError as exc:
                logger.error(exc)
                index = self.__create_new_index(images, file_path)
                ntotal = index.ntotal

            if ntotal != images.count():
                index = self.__create_new_index(images, file_path)
            return index





    def _get_background_images_index(self):
        file_name = 'background_images.index'
        file_path = self.__get_file_path(file_name)
        criteria =  Image.is_background == True
        index = self.__get_index_by_criteria(file_path, criteria)
        self._index_save_list.append([file_path, index])
        return index


    def __get_index_by_criteria(self, file_path, query_condition=None):
        s = self._db.Session()
        # Создаем базовый запрос
        images = s.query(Image)
        # Применяем условие, если оно было передано
        if query_condition is not None:
            images = images.filter(query_condition)
        index = self.__get_index(images, file_path)
        s.close()
        return index


    def save_indexes(self):
        for path, index in self._index_save_list:
            index.save_index()

    @staticmethod
    def __get_new_objects(objects, pickle_file_path):
        images = objects.all()
        with open(pickle_file_path, 'wb') as file:
            pickle.dump(images, file)
        return images



    def _get_objects(self, objects, pickle_file_path):
        if not os.path.exists(pickle_file_path):
            objects = self.__get_new_objects(objects, pickle_file_path)
            return objects
        else:
            try:
                with open(pickle_file_path, 'rb') as file:
                    images = pickle.load(file)
                    if len(images) != objects.count():
                        images = self.__get_new_objects(objects, pickle_file_path)
                        return images
                    else:
                        return images
            except:
                images = self.__get_new_objects(objects, pickle_file_path)
                return images


    def _get_images_in_items_index(self, index_type):
        index_name = 'images_in_items'
        index_file_name =  index_name + '.index'
        # object_pickle_name = index_name + '.pickle'
        index_file_path = self.__get_file_path(index_file_name)
        # pickle_file_path = self.__get_file_path(object_pickle_name)
        s = self._session_maker()
        images = s.query(Image)\
                .join(Image.items)\
                .filter(Image.items.any()).distinct(Image.id)
        # images = self._get_objects(images, pickle_file_path)
        index =  Index(images, 'vector', index_file_path, index_type, self._batch_size,)
        self._index_save_list.append([index_file_path, index])
        s.close()
        return index

    def _get_keywords_index(self, vector_property):
        file_name = 'keyword.index'
        file_path = self.__get_file_path(file_name)
        s = self._session_maker()
        keywords = s.query(Keyword).filter(getattr(Keyword,  vector_property) != None)
        index = Index(keywords, vector_property , file_path,
                      index_type='IndexFlatIP', batch_size=100)
        return index

    def get_keyword_phrases_index(self):
        file_name = 'keyword_phrase.index'
        file_path = self.__get_file_path(file_name)
        keyword_phrase = self._neo4j.get_all_keyword_phrase()
        index = Index(keyword_phrase, 'vector', file_path,
                      index_type='IndexFlatIP', batch_size=100)
        return index
