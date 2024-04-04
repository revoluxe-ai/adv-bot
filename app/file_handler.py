import aiogram
from aiogram.types import FSInputFile

from app.utils.image_master import image_tools
from PIL import Image as PilImage
from app.admin_bot.sender.utils.db import db



async def get_telegram_image(image_path: str, bot: aiogram.Bot):
    file_id = await _get_telegram_file(image_path, bot)
    if file_id:
        return file_id
    else:
        return None




async def _get_telegram_file(image_path: str, bot: aiogram.Bot):
    pil_image = PilImage.open(image_path)
    dhash = image_tools.dhash(pil_image)
    file_id = await db.get_telegram_file(dhash, bot)
    if file_id:
        return file_id
    else:
        return None



async def save_telegram_file(image: FSInputFile, image_telegram_id: str, bot_id: int):
    pil_image = PilImage.open(image.path)
    dhash = image_tools.dhash(pil_image)
    await db.add_file(image_telegram_id, dhash, bot_id)










