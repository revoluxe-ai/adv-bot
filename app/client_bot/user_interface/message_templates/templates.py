import io
import logging
from abc import abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import TypeVar, Any, cast

import aiogram
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, Message

from app import file_handler
from app.client_bot.message_manager import LastMessage as ActualLastMessage

from .base import Base

logger = logging.getLogger(__name__)
MAX_TELEGRAM_CAPTION_LEN = 1024
_CAPTION_OVERFLOW_SUFFIX = "\n..."


T = TypeVar("T", bound=Message)


def manage_file_id(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> T | None:
        logger.debug("Вызов обертки manage_file_id")
        # Получение и изменение file_id перед вызовом основной функции
        old_image = self.image
        if old_image:
            logger.debug("Получение изображения")
            image: io.BytesIO | str | types.InputFile = (
                await file_handler.get_telegram_image(old_image, self.bot)
            )

            if isinstance(image, io.BytesIO):
                new_image = BufferedInputFile(image.getvalue(), filename="wbgram.png")
                self.image = new_image
            else:
                self.image = image
        else:
            image: io.BytesIO | str | types.InputFile | None = None

        # Вызов основной функции
        message: T = await func(self, *args, **kwargs)

        # Обработка результата выполнения основной функции для сохранения image_id
        image_id = message.photo[-1].file_id # type: ignore[index]
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

    async def __call__(self, *args, **kwargs) -> None:
        await super().__call__()
        text = self.text
        parse_mode = getattr(self, "parse_mode", None)
        if parse_mode == "Markdown":
            text = text.replace("_", r"\_")
        logger.debug(
            "TextWithKeyboard: sending class=%s chat_id=%s parse_mode=%s text_len=%s keyboard_rows=%s text_preview=%r",
            self.__class__.__name__,
            self.chat_id,
            parse_mode,
            len(text),
            len(self.keyboard.inline_keyboard),
            text[:80],
        )
        _ = await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            reply_markup=self.keyboard,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
        logger.debug(
            "TextWithKeyboard: sent class=%s chat_id=%s",
            self.__class__.__name__,
            self.chat_id,
        )
        return None


class TextWithImage(Base):
    @property
    @abstractmethod
    def text(self) -> str:
        pass

    @property
    @abstractmethod
    def image(self) -> io.BytesIO | str | BufferedInputFile | None:
        pass

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

    async def __call__(self, *args, **kwargs) -> Any:
        # Отправка нового сообщения без попытки редактирования существующего
        last_message = await self.bot.send_message(
            chat_id=self.chat_id,
            text=self.text,
            parse_mode=getattr(self, "parse_mode", None),
            disable_web_page_preview=getattr(self, "DISABLE_WEBPAGE_PREVIEW", None),
        )
        return last_message


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
    def on_page(self) -> int:
        pass

    async def __call__(self) -> None:
        _ = await self.bot.send_message(
            chat_id=self.chat_id,
            text=self.text,
            reply_markup=self.keyboard,
            parse_mode=getattr(self, "parse_mode", None),
        )
        return None


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
    def image(self) -> io.BytesIO | str | BufferedInputFile | None:
        return self._image

    @image.setter
    def image(self, value: io.BytesIO | str | BufferedInputFile | None) -> None:
        self._image = value

    @manage_file_id
    async def __call__(self) -> Message:
        logger.debug("Вызов метода send_photo")
        full_caption = self.text
        caption, overflow = self._split_caption(full_caption)
        photo = cast(types.InputFile | str, self.image)
        try:
            message = await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo,
                caption=caption,
                reply_markup=self.keyboard,
                parse_mode=getattr(self, "parse_mode", None),
            )
        except TelegramBadRequest as exc:
            error_text = (getattr(exc, "message", None) or str(exc)).lower()
            if "caption is too long" not in error_text:
                raise
            logger.warning(
                "Caption overflow in send_photo for chat_id=%s; applying fallback",
                self.chat_id,
            )
            caption, overflow = self._split_caption(
                full_caption,
                limit=MAX_TELEGRAM_CAPTION_LEN - 64,
            )
            message = await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo,
                caption=caption,
                reply_markup=self.keyboard,
                parse_mode=getattr(self, "parse_mode", None),
            )
        if overflow:
            _ = await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"Продолжение:\n{overflow}",
                parse_mode=getattr(self, "parse_mode", None),
                disable_web_page_preview=True,
            )
        logger.debug("Отправка сообщения завершена")
        return message

    @staticmethod
    def _split_caption(
        caption: str,
        limit: int = MAX_TELEGRAM_CAPTION_LEN,
    ) -> tuple[str, str]:
        if len(caption) <= limit:
            return caption, ""
        suffix = _CAPTION_OVERFLOW_SUFFIX
        suffix_len = len(suffix)
        if limit <= suffix_len + 12:
            return caption[:limit], caption[limit:]
        # One split index: tail must start exactly where the caption text in head ends,
        # so len(caption[:split_at] + suffix) <= limit and no gap/overlap with tail.
        split_at = limit - suffix_len
        head = caption[:split_at] + suffix
        tail = caption[split_at:]
        return head, tail
