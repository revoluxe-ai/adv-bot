from abc import abstractmethod
from datetime import datetime, timedelta, timezone
from aiogram import types
import aiogram
import logging
from .base import Base

logger = logging.getLogger(__name__)

class LastMessage(types.Message):
    message_type: str





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

    async def __call__(self):
        # Отправка нового сообщения без попытки редактирования существующего
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

    async def __call__(self):
        # Отправка нового сообщения без попытки редактирования существующего
        last_message = await self.bot.send_photo(chat_id=self.chat_id,
                                                 photo=self.image,
                                                 caption=self.text,
                                                 reply_markup=self.keyboard)
        return last_message, self.get_content_type()