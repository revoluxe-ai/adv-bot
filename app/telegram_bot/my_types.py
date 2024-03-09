from abc import abstractmethod
from datetime import datetime, timedelta, timezone
from aiogram import types as tp
import aiogram
import logging





logger = logging.getLogger(__name__)

class LastMessage(tp.Message):
    message_type: str


    def __get_parent_class_name(self):
        # Получаем первый родительский класс из кортежа __bases__
        parent_class = self.__class__.__bases__[0]
        return parent_class.__name__

    def get_content_type(self):
        return self.__get_parent_class_name()

    def can_edit_message(self) -> bool:
        message_date = self.date
        if isinstance(message_date, str):
            message_date = datetime.fromisoformat(message_date)
        # Определяем текущее время
        now = datetime.now(timezone.utc)
        # Рассчитываем разницу времени
        time_diff = now - message_date
        # Сообщение можно редактировать в течение 48 часов
        return time_diff < timedelta(hours=48)


def __check_message_copy(last_message: LastMessage,
                         text: str,
                         keyboard: tp.InlineKeyboardMarkup):
    return last_message.text == text and last_message.reply_markup == keyboard


