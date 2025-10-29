import logging
import os

import faiss
import numpy as np
from PIL import Image as PilImg
from tqdm import tqdm

from app.utils.faiss_manager.faiss_index import Index
from app.utils.faiss_manager.faiss_index_manager import FaissManager
from app.utils.image_master import image_tools
from app.utils.image_master.database.model import Image
from keras.applications.vgg19 import VGG19, preprocess_input
from keras.preprocessing.image import img_to_array

from .database import model


def ensure_used_with_with(func):
    """Декоратор для проверки использования объекта с оператором `with`"""

    def wrapper(instance, *args, **kwargs):
        assert (
            instance._used_with_with
        ), "Объект должен быть использован с оператором `with`"
        return func(instance, *args, **kwargs)

    return wrapper


logger = logging.getLogger(__name__)


class ImageMaster:
    def __init__(self, load_indexes=False) -> None:
        im_tools = image_tools
        self._im_tools = im_tools
        current_folder = os.path.dirname(os.path.abspath(__file__))
        self._images_folder = os.path.join(current_folder, "image_sources")
        if load_indexes:
            self._indexes = FaissManager()
        self._model = VGG19(include_top=False)
        # self._alchemy_session_maker = get_session_maker()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "_indexes"):
            self._indexes.save_indexes()

    @property
    def indexes(self):
        return self._indexes

    def get_vector(self, img: PilImg) -> Image:
        # Ensure the image is in RGB mode

        if img.mode != "RGB":
            img = img.convert("RGB")

        # Ensure the tensor has three channels
        img = img.resize((224, 224))
        x = img_to_array(img)
        assert x.shape[-1] == 3, "Image tensor does not have 3 channels!"

        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        model = self._model
        features = model.predict(x)
        vector = features.flatten()
        vector = np.expand_dims(vector, axis=0)
        faiss.normalize_L2(vector)
        return vector[0]

    def _add_image_common(
        self,
        img: PilImg,
        dhash=None,
        is_background: bool = False,
        min_level: float = None,
        keywords: list = None,
    ) -> Image:
        if min_level == None:
            min_level = 0
        if not dhash:
            dhash = self._im_tools.dhash(img)
        s = self._alchemy_session_maker()
        if s.query(Image).filter(Image.dhash == dhash).first():
            return None
        img = self._im_tools.remove_white_space(img)
        vector = self.get_vector(img)
        vector_matrix = np.expand_dims(vector, axis=0)
        target_index = (
            self._indexes.background_images
            if is_background
            else self._indexes.all_images
        )

        if min_level > 0 and is_background == False:
            if target_index.ntotal > 0:
                distances, ids = target_index.search(vector_matrix, k=1)
                distance = distances[0][0] ** 1 / 2
                if min_level is not None and distance <= min_level:
                    logger.debug(f"Похожее изображение уже есть, дистанция: {distance}")
                    id_ = int(ids[0][0])
                    while True:
                        try:
                            image = s.query(Image).filter(Image.id == id_).first()
                            break
                        except:
                            logger.error("Ошибка запроса к БД")
                            s.close()
                            s = self._alchemy_session_maker()
                    if keywords:
                        image.keywords = keywords
                        s.commit()
                        s.close()
                    return image
                elif np.isclose(distance, 0):
                    logger.debug("Аналогичное изображение уже есть")
                    id_ = int(ids[0][0])
                    image = s.query(Image).filter(Image.id == id_).first()
                    s.close()
                    return image

        image = model.Image(
            dhash=dhash, vector=vector, keywords=keywords, is_background=is_background
        )

        s.add(image)
        s.commit()
        id_ = image.id
        vector_matrix = np.expand_dims(vector, axis=0)
        ids = np.expand_dims(id_, axis=0)
        target_index.add_with_ids(vector_matrix, ids)
        s.close()
        return image

    def add_background_image(self, img: PilImg):
        self._add_image_common(img, is_background=True)

    def add_main_image(
        self, img: PilImg, dhash, min_level=0.24, keywords=None
    ) -> Image:
        return self._add_image_common(
            img, dhash, min_level=min_level, keywords=keywords
        )

    def check_as_background(self, vector: np.ndarray):
        """
        Из базы я вытаскиваю вектор, поэтому аргумент в виде
        PilImg не универсальный. Нужно переделать аргументы, а получать
        вектор можно self.get_vector(img)

        мне очеч кажется, но строка ниже лишняя, если все работает
        без нее - удалить
        """
        vector = vector.reshape(1, -1)
        index = self._indexes.background_images
        distances, indexes = index.search(vector, k=1)
        distance = distances[0][0] ** 1 / 2
        if distance > 0.65:
            return False, distance, indexes[0][0]
        else:
            return True, distance, indexes[0][0]

    def search_all_for_one(self, vector, index: Index) -> (list[float], list[object]):
        vector = vector.reshape(1, -1)
        assert self.is_normalized_l2(vector)
        assert index.index.ntotal > 0
        distances, indexes = index.index.search(vector, k=index.index.ntotal)
        distances = distances**1 / 2
        objects = [index.id_to_object[int(i)] for i in indexes[0]]
        return distances, objects

    def search_one(self, vector, index) -> (float, Image):
        vector = vector.reshape(1, -1)
        assert self.is_normalized_l2(vector)
        assert index.ntotal > 0
        distances, indexes = index.search(vector, k=1)
        distance = distances[0][0] ** 1 / 2
        s = self._alchemy_session_maker()
        index = int(indexes[0][0])
        image: Image = s.query(Image).filter(Image.id == index).first()
        return distance, image

    @staticmethod
    def is_normalized_l2(vector):
        l2_norm = np.linalg.norm(vector, 2)
        return np.isclose(l2_norm, 1.0)

    @ensure_used_with_with
    def get_most_unique_images_ids(self, batch_size) -> list[Image]:
        def yield_batch(images):
            batch = []
            for image in images:
                batch.append(image)
                if len(batch) == batch_size:
                    yield np.array([image.vector for image in batch])
                    batch = []
            if batch:
                yield np.array([image.vector for image in batch])

        session = self._alchemy_session_maker()
        images_ids_in_items = self._neo4j.get_images_ids_in_items()
        images = session.query(Image).filter(Image.id.in_(images_ids_in_items))
        second_min_distances = []
        for vectors in tqdm(yield_batch(images)):
            # Отправляем батч векторов в FAISS
            distances, _ = self._indexes.images_in_items.search(
                vectors, k=self._indexes.images_in_items.ntotal + 1
            )
            # Обработка результатов для каждого вектора в батче
            for distance in distances:
                second_min_distance = np.sort(distance)[1]
                second_min_distances.append(second_min_distance)

        logger.debug("Завершили цикл")
        sorted_indices = np.argsort(second_min_distances, axis=0)[
            ::-1
        ]  # [::-1] для сортировки по убыванию
        logger.debug("Получили сортировочные индексы")
        session.close()  # Не забудьте закрыть сессию после использования
        return sorted_indices

    def get_matrix_for_image_in_items(self, batch):
        index = self._indexes.images_in_items
        k = index.ntotal
        s = self._alchemy_session_maker()
        ids = self._neo4j.get_images_ids_in_items("Картины")
        images = s.query(Image).filter(Image.id.in_(ids))

        vectors = []
        all_distances = []
        all_labels = []

        for image in images.yield_per(batch):
            vectors.append(image.vector)
            if len(vectors) == batch:
                distances, labels = index.search(
                    np.array(vectors), k
                )  # предполагая, что 'k' - это количество ближайших соседей, которое вы хотите найти
                all_distances.append(distances)
                all_labels.append(labels)
                vectors = []

        # Обрабатываем оставшиеся векторы, если их количество менее 500
        if vectors:
            distances, labels = index.search(np.array(vectors), k)
            all_distances.append(distances)
            all_labels.append(labels)

        # Объединяем результаты
        final_distances = np.vstack(all_distances)
        final_distances = final_distances**1 / 2
        final_labels = np.vstack(all_labels)

        return final_distances, final_labels

    def delete_background_image(self):
        s = self._alchemy_session_maker()
        images = s.query(Image).filter(Image.is_background == True)
        images.delete(synchronize_session=False)
        s.commit()
