from abc import ABC
from typing import Any

import aiogram
from aiogram import Bot
from aiogram.enums import ParseMode


class Base(ABC):
    def __init__(self, bot: aiogram.Bot, chat_id: int):
        self._bot = bot
        self._chat_id = chat_id

    @property
    def bot(self) -> Bot:
        return self._bot

    @property
    def chat_id(self) -> int:
        return self._chat_id

    async def __call__(self: "Base", *args: Any, **kwargs: Any) -> None:
        parse_mode = getattr(self, "parse_mode", None)
        self.parse_mode = parse_mode

    def __get_parent_class_name(self: "Base") -> str:
        # Получаем первый родительский класс из кортежа __bases__
        parent_class = self.__class__.__bases__[0]
        return parent_class.__name__

    def get_content_type(self: "Base") -> str:
        return self.__get_parent_class_name()
