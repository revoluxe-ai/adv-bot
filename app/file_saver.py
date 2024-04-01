from app.utils.image_master import image_tools
from PIL import Image as PilImage
from app.admin_bot.sender import db


async def _get_telegram_file(image_path: str):
    pil_image = PilImage.open(image_path)
    dhash = image_tools.dhash(pil_image)
    file_id = await db.get_telegram_file(dhash)
    if file_id:
        return file_id
    else:
        return None



async def save_telegram_file(image_path: str, image_id: int):
    pil_image = PilImage.open(image_path)
    dhash = image_tools.dhash(pil_image)
    await db.add_file(image_id, dhash)










