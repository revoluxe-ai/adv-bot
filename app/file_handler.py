import io
from io import BytesIO
from typing import Union
import PIL
import aiofiles
import aiogram
from aiogram import Bot
from aiogram.client.session import aiohttp
from aiogram.types import FSInputFile, InputFile, BufferedInputFile, URLInputFile

from app.utils.image_master import image_tools
from PIL import Image as PilImage
from app.admin_bot.sender.utils.db import db



async def get_telegram_image(image_path: str, bot: aiogram.Bot) -> Union[InputFile, str]:
    result = await _get_telegram_file(image_path, bot)
    return result





async def _get_telegram_file(image_path: str, bot: Bot) -> Union[str, InputFile]:
    if image_path.startswith('http'):
        # Загрузка изображения по HTTP
        async with aiohttp.ClientSession() as session:
            async with session.get(image_path) as response:
                if response.status == 200:
                    image_bytes = await response.read()
                    buffered_image = BytesIO(image_bytes)
                    pil_image = PilImage.open(buffered_image)
                else:
                    raise Exception(f"Ошибка загрузки изображения: HTTP {response.status}")
    else:
        async with aiofiles.open(image_path, 'rb') as f:
            content = await f.read()
            buffered_image = io.BytesIO(content)
        pil_image = PilImage.open(buffered_image)

    # Вычисление хэша изображения
    dhash = image_tools.dhash(pil_image)

    # Попытка найти существующий идентификатор файла в Telegram
    file_id = await db.get_telegram_file(dhash, bot)

    if file_id:
        return file_id
    else:
        return BufferedInputFile(buffered_image.getvalue(), filename='wbgram.png')


async def save_telegram_file(image: io.BytesIO, image_telegram_id: str, bot_id: int):
    pil_image = PilImage.open(image)
    dhash = image_tools.dhash(pil_image)
    await db.add_file(image_telegram_id, dhash, bot_id)










