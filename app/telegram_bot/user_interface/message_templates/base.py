from abc import ABC, abstractmethod

import aiogram

from app.my_types import LastMessage
import datetime
import app

class Base(ABC):
    def __init__(self, bot, last_message: LastMessage, chat_id: int):
        self.last_message = last_message
        self.bot = bot
        self.chat_id = chat_id


    @abstractmethod
    async def __call__(self)-> (LastMessage, str):
        pass

    def __get_parent_class_name(self):
        # Получаем первый родительский класс из кортежа __bases__
        parent_class = self.__class__.__bases__[0]
        return parent_class.__name__

    def get_content_type(self):
        return self.__get_parent_class_name()

    def can_edit_message(self, message: LastMessage) -> bool:
        message_date = message.date
        if isinstance(message_date, str):
            message_date = datetime.datetime.fromisoformat(message_date)
        # Определяем текущее время
        now = datetime.datetime.now(datetime.timezone.utc)
        # Рассчитываем разницу времени
        time_diff = now - message_date
        # Сообщение можно редактировать в течение 48 часов
        return time_diff < datetime.timedelta(hours=48)

    def __check_message_copy(last_message: LastMessage,
                             text: str,
                             keyboard: aiogram.types.InlineKeyboardMarkup):
        return last_message.text == text and last_message.reply_markup == keyboard

