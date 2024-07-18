from abc import ABCMeta, abstractmethod
from collections import namedtuple

Path = namedtuple('Path', ['position', 'path'])
import importlib
import inspect
import os
import re
from typing import final

import PIL
from PIL import Image

from app.utils.image_master import image_tools
from app.utils.image_master.database.model import WB_CARD_MEDIA_FOLDER


class WbItem(metaclass=ABCMeta):

    def __init__(self):
        self._brand = None
        self._image_tools = image_tools





    @property
    @abstractmethod
    def offer_id(self):
        pass

#
#
# class WBCard( metaclass= ABCMeta):
#
#
#
#     def __str__(self):
#         strings = []
#         for property in inspect.getmembers(type(self)):
#             property = property[0]
#             if not property.startswith('_'):
#                 try:
#                     value = getattr(self, property)
#                     if not callable(value):
#                         strings.append(f'{property}:{value}')
#                 except Exception as e:
#                     pass
#
#         return '\n'.join(strings)
#
#     @final
#     @property
#     def size(self):
#         assert self.wb_category_name in ['Картины', 'Постеры']
#         drivers_module = importlib.import_module('wb.cards_manager_old.drivers')
#         WbNeo4j = getattr(drivers_module, 'WbNeo4j')
#         neo4j = WbNeo4j(self.brand)
#         main_image = neo4j.get_main_image_path(self.offer_id)
#         image = PIL.Image.open(main_image)
#         return image_tools.get_standard_proportion(image)
#
#
#     @final
#     @property
#     def url(self):
#         return f'https://www.wildberries.ru/catalog/{self.nmid}/detail.aspx'
#
#
#     @final
#     @property
#     def size_int(self) -> int:
#         return int(''.join(re.match('(\d{2}).(\d{2})', self.size).groups()))
#
#     @final
#     @property
#     def wb_local_fotos(self) -> list:
#         brand_folder = os.path.join(WB_CARD_MEDIA_FOLDER, self.brand)
#         card_folder = os.path.join(brand_folder, self.offer_id)
#         media = []
#         for file in os.listdir(card_folder):
#             file_path = os.path.join(card_folder, file)
#             media.append(file_path)
#         media.sort(key=lambda path:  int(re.search('(\d{1,2})\.', path).group(1)))
#
#         return media
#
#
#     @final
#     def insert_image(self, image: Image, position: int):
#         folder = os.path.join('cards/wb_local_photos/', self.offer_id)
#         # Получение и сортировка списка файлов
#         files = sorted([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))],
#                        key=lambda x: int(os.path.splitext(x)[0]))
#         # Переименование файлов, начиная с последнего
#         for filename in reversed(files):
#             number = int(os.path.splitext(filename)[0])
#             if number >= position:
#                 new_number = number + 1
#                 new_name = f"{new_number}{os.path.splitext(filename)[1]}"
#                 os.rename(os.path.join(folder, filename), os.path.join(folder, new_name))
#
#         new_image_name = f"{position}.png"
#         image.save(os.path.join(folder, new_image_name))
#
#
#
#     @property
#     def stock(self) -> int:
#         return self._stock
#
#     @stock.setter
#     def stock(self, value):
#         assert isinstance(value, int)
#         self._stock = value
#
#
#
#     @property
#     @abstractmethod
#     def wb_category_name(self):
#         pass
#
#     @final
#     @property
#     def brand(self):
#         if not self._brand:
#             raise Exception('Установите свойство brand через Сеттер. Бренд в объекте магазина магазина')
#         else:
#             return self._brand
#
#     @brand.setter
#     def brand(self, value):
#         self._brand = value
#
#     @property
#     @abstractmethod
#     def wb_barcode(self)-> str:
#         pass
#
#
#     @property
#     def statistic(self):
#         return self._statistic_card
#
#     @statistic.setter
#     def statistic(self, value):
#         assert isinstance(value, CardStatistic)
#         self._statistic_card = value
#
#     @property
#     def url(self):
#         return f'https://www.wildberries.ru/catalog/{self.nmid}/detail.aspx?targetUrl=GP'
#
#
#


class CardGroupABC(metaclass=ABCMeta):

    @property
    @abstractmethod
    def targetIMT(self):
        pass

    @property
    @abstractmethod
    def nmIDs(self):
        pass

    @property
    @abstractmethod
    def json(self):
        pass
