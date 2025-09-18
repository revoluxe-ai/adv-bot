from abc import ABCMeta, abstractmethod
from collections import namedtuple

Path = namedtuple("Path", ["position", "path"])
from app.utils.image_master import image_tools


class WbItem(metaclass=ABCMeta):
    def __init__(self):
        self._brand = None
        self._image_tools = image_tools

    @property
    @abstractmethod
    def offer_id(self):
        pass


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
