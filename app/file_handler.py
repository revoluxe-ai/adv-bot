import io
from io import BytesIO
from typing import Union

import aiofiles
import aiogram
from aiogram import Bot
from aiogram.client.session import aiohttp
from aiogram.types import BufferedInputFile, InputFile
from PIL import Image as PilImage

from app.admin_bot.sender.utils.db import db
from app.utils.image_master import image_tools



import logging

logger = logging.getLogger(__name__)




async def get_telegram_image(image_path: str, bot: aiogram.Bot) -> Union[InputFile, str]:
    result = await _get_telegram_file(image_path, bot)
    return result





async def _get_telegram_file(image_path: Union[str, None], bot: Bot) -> Union[str, InputFile]:
    logger.debug(f"Начало обработки файла: {image_path}")

    if isinstance(image_path, BytesIO):
        logger.debug("image_path является BytesIO объектом")
        return BufferedInputFile(image_path.getvalue(), filename='wbgram.png')

    try:
        if image_path.startswith('http'):
            logger.debug(f"Загрузка изображения по HTTP: {image_path}")
            # Загрузка изображения по HTTP
            async with aiohttp.ClientSession() as session:
                async with session.get(image_path) as response:
                    logger.debug(f"HTTP ответ: {response.status}")
                    if response.status == 200:
                        image_bytes = await response.read()
                        logger.debug("Изображение успешно загружено по HTTP")
                        buffered_image = BytesIO(image_bytes)
                        pil_image = PilImage.open(buffered_image)
                        logger.debug("Изображение открыто с помощью PIL")
                    else:
                        raise Exception(f"Ошибка загрузки изображения: HTTP {response.status}")
        else:
            logger.debug(f"Загрузка изображения из локального файла: {image_path}")
            async with aiofiles.open(image_path, 'rb') as f:
                content = await f.read()
                logger.debug("Изображение успешно прочитано из файла")
                buffered_image = io.BytesIO(content)
            pil_image = PilImage.open(buffered_image)
            logger.debug("Изображение открыто с помощью PIL")
    except Exception as e:
        logger.error(f"Ошибка загрузки изображения: {e}")
        try:
            async with aiofiles.open(image_path, 'rb') as f:
                content = await f.read()
                logger.debug("Повторное чтение изображения из файла после ошибки")
                buffered_image = io.BytesIO(content)
            pil_image = PilImage.open(buffered_image)
            logger.debug("Изображение открыто с помощью PIL после ошибки")
        except Exception as e_inner:
            logger.error(f"Ошибка при повторной попытке: {e_inner}")
            raise e_inner

    logger.debug("Начало вычисления хэша изображения")
    dhash = image_tools.dhash(pil_image)
    logger.debug(f"Хэш изображения: {dhash}")

    logger.debug("Попытка найти существующий идентификатор файла в Telegram")
    file_id = await db.get_telegram_file(dhash, bot)

    if file_id:
        logger.debug(f"Найден существующий файл: {file_id}")
        return file_id
    else:
        logger.debug("Файл не найден, создание нового BufferedInputFile")
        return BufferedInputFile(buffered_image.getvalue(), filename='wbgram.png')



async def save_telegram_file(image: io.BytesIO, image_telegram_id: str, bot_id: int):
    pil_image = PilImage.open(image)
    dhash = image_tools.dhash(pil_image)
    await db.add_file(image_telegram_id, dhash, bot_id)










