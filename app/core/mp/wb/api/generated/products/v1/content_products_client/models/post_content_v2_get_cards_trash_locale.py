from enum import Enum


class PostContentV2GetCardsTrashLocale(str, Enum):
    EN = "en"
    RU = "ru"
    ZH = "zh"

    def __str__(self) -> str:
        return str(self.value)
