import asyncio

from aiogram import Router, types, Bot
from aiogram import F
from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.client_bot import const

router = Router()

SAVE_PATH = 'app/modules/keywords_query/requests.csv'


class QueryFileFromAdmin(BaseFilter):
    user_id: int
    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id
        if user_id in const.ADMINS:
            if message.document:
                doc = message.document
                if doc.file_name == 'requests.csv':
                    return True




@router.message(QueryFileFromAdmin())
async def handle_document(message: types.Message, bot: Bot):
    document = message.document
    file = await bot.download(document)
    await message.answer('Файл сохранен')