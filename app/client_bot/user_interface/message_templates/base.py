import datetime
from abc import ABC, abstractmethod

import aiogram
from aiogram.enums import ParseMode


class Base(ABC):
    def __init__(self, bot: aiogram.Bot, chat_id: int):
        self._bot = bot
        self._chat_id = chat_id

    @property
    def bot(self):
        return self._bot

    @property
    def chat_id(self):
        return self._chat_id

    def _escape_markdown_2(self, text: str) -> str:
        return text\
            .replace('[', '\\[') \
            .replace('`', '\\`') \
            .replace(']', '\\]') \
            .replace('(', '\\(') \
            .replace(')', '\\)') \
            .replace('~', '\\~') \
            .replace('>', '\\>') \
            .replace('#', '\\#') \
            .replace('+', '\\+') \
            .replace('-', '\\-') \
            .replace('=', '\\=') \
            .replace('{', '\\{') \
            .replace('}', '\\}')


    async def __call__(self) -> (str):  # type: ignore
        parse_mode = getattr(self, 'parse_mode', None)
        self.parse_mode = parse_mode
        if parse_mode == ParseMode.MARKDOWN_V2:
            text = self.text  # type: ignore
            self.text = self._escape_markdown_2(text)

    def __get_parent_class_name(self):
        # Получаем первый родительский класс из кортежа __bases__
        parent_class = self.__class__.__bases__[0]
        return parent_class.__name__

    def get_content_type(self):
        return self.__get_parent_class_name()

    @staticmethod
    def can_edit_message(message) -> bool:
        message_date = message.date
        if isinstance(message_date, str):
            message_date = datetime.datetime.fromisoformat(message_date)
        # Определяем текущее время
        now = datetime.datetime.now(datetime.timezone.utc)
        # Рассчитываем разницу времени
        time_diff = now - message_date
        # Сообщение можно редактировать в течение 48 часов
        return time_diff < datetime.timedelta(hours=48)

    def __check_message_copy(last_message,
                             text: str,
                             keyboard: aiogram.types.InlineKeyboardMarkup):
        return last_message.text == text and last_message.reply_markup == keyboard
