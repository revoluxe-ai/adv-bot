import io
import logging
from abc import abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any, cast

import aiogram
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, Message

from app import file_handler
from app.client_bot.const import TELEGRAM_CAPTION_LIMIT

from .base import Base

logger = logging.getLogger(__name__)
_CAPTION_OVERFLOW_SUFFIX = "\n..."


def manage_file_id(func: Callable[..., Any]) -> Callable[..., Any]:
    """Подставляет Telegram file_id/InputFile перед send_photo и сохраняет новый id."""

    @wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Message | None:
        logger.debug("Вызов обертки manage_file_id")
        old_image = self.image
        source_bytes: io.BytesIO | None = (
            old_image if isinstance(old_image, io.BytesIO) else None
        )
        if old_image:
            logger.debug("Получение изображения")
            request: str | BufferedInputFile
            if isinstance(old_image, io.BytesIO):
                request = BufferedInputFile(
                    old_image.getvalue(), filename="wbgram.png"
                )
            else:
                request = old_image
            self.image = await file_handler.get_telegram_image(request, self.bot)

        message = await func(self, *args, **kwargs)
        if message is None or message.photo is None:
            return message
        image_id: str = message.photo[-1].file_id
        if source_bytes is not None:
            bot: aiogram.Bot = self.bot
            await file_handler.save_telegram_file(source_bytes, image_id, bot.id)
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

    async def __call__(self, *args: Any, **kwargs: Any) -> None:
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
        photo = self.image
        if photo is None:
            raise ValueError("TextWithImage.image is required for send_photo")
        if isinstance(photo, io.BytesIO):
            photo = BufferedInputFile(photo.getvalue(), filename="wbgram.png")
        last_message = await self.bot.send_photo(
            chat_id=self.chat_id,
            photo=photo,
            caption=self.text,
            parse_mode=parse_mode,
        )
        return last_message


class Text(Base):
    @property
    @abstractmethod
    def text(self) -> str:
        pass

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
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
                limit=TELEGRAM_CAPTION_LIMIT - 64,
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
        limit: int = TELEGRAM_CAPTION_LIMIT,
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
