from abc import ABC, abstractmethod


class ShopInterface(ABC):

    @property
    @abstractmethod
    def media_template(self):
        pass




