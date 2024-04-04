from abc import abstractmethod
from datetime import datetime, timedelta, timezone
from functools import wraps

from aiogram import types
import aiogram
import logging

from aiogram.types import FSInputFile

from .base import Base
from app import file_handler



logger = logging.getLogger(__name__)

class LastMessage(types.Message):
    message_type: str


def manage_file_id(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        # Получение и изменение file_id перед вызовом основной функции
        image = self.image
        file_id = await file_handler.get_telegram_image(image, self.bot)
        if file_id:
            self.image = file_id
        else:
            self.image =  FSInputFile(self.image)

        # Вызов основной функции
        message = await func(self, *args, **kwargs)

        # Обработка результата выполнения основной функции для сохранения image_id
        image_id = message.photo[-1].file_id
        if isinstance(self.image, FSInputFile):
            bot: aiogram.Bot = self.bot
            bot_id = bot.id
            await file_handler.save_telegram_file(self.image, image_id, bot_id)
        return  message

    return wrapper



class TextWithKeyboard(Base):
    @property
    @abstractmethod
    def text(self):
        pass
    @property
    @abstractmethod
    def keyboard(self):
        pass



    async def __call__(self):

        last_message = await self.bot.send_message(chat_id=self.chat_id,
                                                    text=self.text,
                                                    reply_markup=self.keyboard)
        return last_message, self.get_content_type()



class TextWithImage(Base):


    @property
    @abstractmethod
    def text(self):
        pass

    @property
    @abstractmethod
    def image(self):
        pass

    @manage_file_id
    async def __call__(self):

        last_message = await self.bot.send_photo(chat_id=self.chat_id,
                                                 photo=self.image,
                                                 caption=self.text)
        return last_message



class Text(Base):

    @property
    @abstractmethod
    def text(self):
        pass


    async def __call__(self)-> (LastMessage, str):
        # Отправка нового сообщения без попытки редактирования существующего
        last_message = await self.bot.send_message(chat_id=self.chat_id,
                                                 text=self.text)
        return last_message, self.get_content_type()


class TextWithKeyboardPagination(Base):
    @property
    @abstractmethod
    def text(self):
        pass

    @property
    @abstractmethod
    def keyboard(self):
        pass

    @property
    @abstractmethod
    def on_page(self):
        pass

    async def __call__(self) -> (LastMessage, str):

        last_message = await self.bot.send_message(chat_id=self.chat_id,
                                                        text=self.text,
                                                        reply_markup=self.keyboard)
        return last_message, self.get_content_type()


class TextWithKeyboarAndImage(Base):
    @property
    @abstractmethod
    def text(self):
        pass

    @property
    @abstractmethod
    def keyboard(self):
        pass

    @property
    @abstractmethod
    def image(self):
        pass

    @manage_file_id
    async def __call__(self):


        last_message = await self.bot.send_photo(chat_id=self.chat_id,
                                                 photo=self.image,
                                                 caption=self.text,
                                                 reply_markup=self.keyboard)

        return last_message, self.get_content_type()