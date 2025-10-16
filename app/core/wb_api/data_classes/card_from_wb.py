import os
from typing import Any

# class Size:
#     def __init__(self, data):
#         self._size = data['dimensions']
#
#     @property
#     def height(self):
#         return self._size['height']
#
#     @property
#     def leigth(self):
#         return self._size['length']
#
#     @property
#     def width(self):
#         return self._size['width']


class CardFromWB:
    _data: dict[str, Any]
    _shop_name: str

    @property
    def shop_name(self) -> str:
        return self._shop_name

    @shop_name.setter
    def shop_name(self, value: str) -> None:
        self._shop_name = value

    def __str__(self) -> str:
        name = []
        name.append("<" * 5 + ">" * 5)
        name.append(str(self.nmid))
        name.append("<" * 5 + ">" * 5)
        return "\n".join(name)

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__()
        self._data = data

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    @property
    def name(self) -> str:
        return self.data["title"]

    @property
    def techSize(self) -> str:
        return self.data["sizes"][0]["techSize"]

    @property
    def wb_mediaFiles(self) -> list[str]:
        media = [image["big"] for image in self.data.get("photos", [])]
        return media

    @property
    def subjectID(self) -> int:
        return self.data["subjectID"]

    @property
    def wb_barcode(self) -> str:
        return self.data["sizes"][0]["skus"][0]

    @property
    def offer_id(self) -> str:
        return self.data["vendorCode"]

    @property
    def brand(self) -> str:
        return self.data["brand"]

    # def item_size(self):
    #     size = Size(self.data)
    #     return size

    @property
    def characterisics(self) -> list[dict[str, Any]]:
        return self.data["characteristics"]

    def createdAt(self) -> str:
        return self.data["createdAt"]

    def updatedAt(self) -> str:
        return self.data["updatedAt"]

    @property
    def wb_category_name(self) -> str:
        return self.data["subjectName"]

    @property
    def nmid(self) -> int:
        return int(self.data["nmID"])

    @property
    def _id(self) -> int:
        return self.nmid

    @property
    def imtID(self) -> int:
        return self.data["imtID"]


class CardFromError:
    _nmid: Any
    _offer_id: Any

    def __init__(self, dict_: dict[str, Any]):
        self._nmid = dict_["nmid"]
        self._offer_id = dict_["offer_id"]

    @property
    def nmid(self) -> Any:
        return self._nmid

    @property
    def offer_id(self) -> Any:
        return self._offer_id
