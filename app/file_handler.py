"""Подготовка изображений для отправки в Telegram (URL, диск, BufferedInputFile)."""

import hashlib
import io
import logging
import os
from io import BytesIO

import aiofiles
import aiogram
from PIL import Image as PilImage
from aiogram import Bot
from aiogram.client.session import aiohttp
from aiogram.types import BufferedInputFile, InputFile

from app.admin_bot.sender.utils.db import db
from app.utils.image_master import image_tools

logger = logging.getLogger(__name__)


async def get_telegram_image(
    image_path: str | BufferedInputFile, bot: aiogram.Bot
) -> InputFile | str:
    """Вернуть InputFile или file_id для передачи в Telegram send_* API.

    Args:
        image_path: URL/локальный путь (str) либо уже готовый BufferedInputFile.
        bot: экземпляр aiogram Bot (нужен для lookup file_id в БД).

    Returns:
        BufferedInputFile / InputFile либо строковый telegram file_id.
    """
    result = await _get_telegram_file(image_path, bot)
    return result


def get_image_from_disc_path(image_path: str) -> str:
    home_path = os.path.expanduser("~")
    wb_cards_image_folder = os.path.join(home_path, "wb_cards_images")
    image_path_hash = hashlib.md5(image_path.encode()).hexdigest()
    image_path = os.path.join(wb_cards_image_folder, f"{image_path_hash}.png")
    return image_path


async def get_image_from_disc(image_path: str) -> BytesIO | None:
    image_path = get_image_from_disc_path(image_path)
    if os.path.exists(image_path):
        async with aiofiles.open(image_path, "rb") as f:
            content = await f.read()
            return BytesIO(content)
    return None


async def save_image_to_disc(url: str, image: BytesIO):
    image_path = get_image_from_disc_path(url)
    image_path_dir = os.path.dirname(image_path)
    if not os.path.exists(image_path_dir):
        os.makedirs(image_path_dir)
    async with aiofiles.open(image_path, "wb") as f:
        await f.write(image.getvalue())


async def _get_telegram_file(
    image_path: str | BytesIO | BufferedInputFile | None, bot: Bot
) -> str | InputFile | int:
    """Подготовить изображение к отправке в Telegram.

    BufferedInputFile возвращается без изменений (passthrough).
    BytesIO оборачивается в BufferedInputFile.
    Для str: HTTP URL загружается (с дисковым кэшем), локальный путь читается
    с диска; при возможности возвращается уже известный telegram file_id.

    Args:
        image_path: URL/путь, BytesIO, BufferedInputFile или None.
        bot: экземпляр Bot для lookup file_id.

    Returns:
        file_id (str/int) либо InputFile/BufferedInputFile для upload.

    Raises:
        Exception: ошибки HTTP/IO при загрузке изображения по str-пути.
    """
    logger.debug(f"Начало обработки файла: {image_path}")

    if isinstance(image_path, BufferedInputFile):
        logger.debug("image_path является BufferedInputFile — passthrough")
        return image_path

    if isinstance(image_path, BytesIO):
        logger.debug("image_path является BytesIO объектом")
        return BufferedInputFile(image_path.getvalue(), filename="wbgram.png")

    try:
        if image_path is not None and image_path.startswith("http"):
            buffered_image = await get_image_from_disc(image_path)
            if buffered_image:
                return BufferedInputFile(buffered_image.getvalue(), filename="wbgram")
            logger.debug(f"Загрузка изображения по HTTP: {image_path}")
            async with aiohttp.ClientSession() as session:
                async with session.get(image_path) as response:
                    logger.debug(f"HTTP ответ: {response.status}")
                    if response.status == 200:
                        image_bytes = await response.read()
                        logger.debug("Изображение успешно загружено по HTTP")
                        buffered_image = BytesIO(image_bytes)
                        await save_image_to_disc(image_path, buffered_image)
                    else:
                        raise Exception(
                            f"Ошибка загрузки изображения: HTTP {response.status}"
                        )
        else:
            logger.debug(f"Загрузка изображения из локального файла: {image_path}")
            async with aiofiles.open(image_path, "rb") as f:  # type: ignore[call-overload]
                content = await f.read()
                logger.debug("Изображение успешно прочитано из файла")
                buffered_image = io.BytesIO(content)

        pil_image = PilImage.open(buffered_image)
        logger.debug(f"Изображение открыто с помощью PIL в формате: {pil_image.format}")

        if pil_image.format == "WEBP":
            logger.debug("Изображение в формате WebP")
            pil_image = pil_image.convert("RGB")
            logger.debug("Изображение WebP конвертировано в RGB")

    except Exception as e:
        logger.error(f"Ошибка загрузки изображения: {e}")
        raise e

    logger.debug("Начало вычисления хэша изображения")
    dhash = image_tools.dhash(pil_image)
    logger.debug(f"Хэш изображения: {dhash}")

    logger.debug("Попытка найти существующий идентификатор файла в Telegram")
    file_id = await db.get_telegram_file(dhash, bot)

    if file_id:
        logger.debug(f"Найден существующий файл: {file_id}")
        return file_id
    else:
        # TODO: Кажется не сохраняет в базе telegram_file_id после загрузки
        logger.debug("Файл не найден, создание нового BufferedInputFile")
        buffered_image.seek(0)
        return BufferedInputFile(buffered_image.getvalue(), filename="wbgram.png")


async def save_telegram_file(image: io.BytesIO, image_telegram_id: str, bot_id: int):
    pil_image = PilImage.open(image)
    dhash = image_tools.dhash(pil_image)
    await db.add_file(image_telegram_id, dhash, bot_id)


# TODO: Сделать расчет максимальной ставки

# TODO: Сделать сравнения похожих товаров, но с большой разницей по результативности

# TODO: Сделать, чтобы грузилась только 1 РК
