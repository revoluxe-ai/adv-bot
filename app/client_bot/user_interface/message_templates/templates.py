import io
import logging
from abc import abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import TypeVar, Coroutine, Any, Tuple, Union, TYPE_CHECKING

import aiogram
from aiogram import types
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, Message, InputFile

from app import file_handler

from .base import Base

logger = logging.getLogger(__name__)


class LastMessage(types.Message):
    message_type: str


T = TypeVar("T", bound=Message)


def manage_file_id(func: Callable[..., Coroutine[Any, Any, Message]]) -> Callable[..., Coroutine[Any, Any, Union[Message, None]]]:
    @wraps(func)
    async def wrapper(self: Union["TextWithImage", "TextWithKeyboardAndImage"], *args: Any, **kwargs: Any) -> Message | None:
        logger.debug("Вызов обертки manage_file_id")
        # Получение и изменение file_id перед вызовом основной функции
        old_image: str | InputFile | None = self.image
        image: io.BytesIO | str | InputFile | None = None
        if old_image:
            logger.debug("Получение изображения")
            image = await file_handler.get_telegram_image(old_image, self.bot)

            if isinstance(image, io.BytesIO):
                new_image = BufferedInputFile(image.getvalue(), filename="wbgram.png")
                self.image = new_image
            else:
                self.image = image

        # Вызов основной функции
        message: Message = await func(self, *args, **kwargs)

        # Обработка результата выполнения основной функции для сохранения image_id
        if message.photo:
            image_id = message.photo[-1].file_id
            if isinstance(image, io.BytesIO):
                bot: aiogram.Bot = self.bot
                bot_id = bot.id
                await file_handler.save_telegram_file(image, image_id, bot_id)
        return message

    return wrapper


class TextWithKeyboard(Base):
    @property
    @abstractmethod
    def text(self) -> str:
        pass

    @property
    @abstractmethod
    def keyboard(self) -> InlineKeyboardMarkup:
        pass

    async def __call__(self) -> Tuple[Message, str]:
        await super().__call__()
        text = self.text
        parse_mode = getattr(self, "parse_mode", None)
        if parse_mode == "Markdown":
            text = text.replace("_", r"\_")
        last_message = await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            reply_markup=self.keyboard,
            parse_mode=self.parse_mode,
            disable_web_page_preview=True,
        )
        return (
            last_message,
            self.get_content_type(),
        )


class TextWithImage(Base):
    @property
    @abstractmethod
    def text(self) -> str:
        pass

    @property
    @abstractmethod
    def image(self) -> str | InputFile:
        pass

    @image.setter
    def image(self, value: str | InputFile) -> None:
        self._image = value

    @manage_file_id
    async def __call__(self) -> Message:
        parse_mode = getattr(self, "parse_mode", None)

        last_message = await self.bot.send_photo(
            chat_id=self.chat_id,
            photo=self.image,
            caption=self.text,
            parse_mode=parse_mode,
        )
        return last_message


class Text(Base):
    @property
    @abstractmethod
    def text(self) -> str:
        pass

    async def __call__(self) -> Tuple[Message, str]:
        # Отправка нового сообщения без попытки редактирования существующего
        last_message = await self.bot.send_message(
            chat_id=self.chat_id,
            text=self.text,
            parse_mode=getattr(self, "parse_mode", None),
            disable_web_page_preview=getattr(self, "DISABLE_WEBPAGE_PREVIEW", None),
        )
        return last_message, self.get_content_type()


class TextWithKeyboardPagination(Base):
    @property
    @abstractmethod
    def text(self) -> str:
        pass

    @property
    @abstractmethod
    def keyboard(self) -> InlineKeyboardMarkup:
        pass

    @property
    @abstractmethod
    def on_page(self) -> Any:
        pass

    async def __call__(self) -> Tuple[Message, str]:
        last_message = await self.bot.send_message(
            chat_id=self.chat_id,
            text=self.text,
            reply_markup=self.keyboard,
            parse_mode=getattr(self, "parse_mode", None),
        )
        return last_message, self.get_content_type()


class TextWithKeyboardAndImage(Base):
    @property
    @abstractmethod
    def text(self) -> str:
        pass

    @property
    @abstractmethod
    def keyboard(self) -> InlineKeyboardMarkup:
        pass

    @property
    def image(self) -> str:
        return self._image

    @image.setter
    def image(self, value: str) -> None:
        self._image = value

    @manage_file_id
    async def __call__(self) -> Message:
        logger.debug("Вызов метода send_photo")
        last_message = await self.bot.send_photo(
            chat_id=self.chat_id,
            photo=self.image,
            caption=self.text,
            reply_markup=self.keyboard,
            parse_mode=getattr(self, "parse_mode", None),
        )
        logger.debug("Отправка сообщения завершена")
        return last_message
