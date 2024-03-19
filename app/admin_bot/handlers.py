import aiogram
from aiogram import Router
from aiogram import dispatcher
from aiogram.filters import CommandStart

router = Router()



@router.message(CommandStart())
async def start(message: aiogram.types.Message):
    chat_id = message.chat.id
    print(chat_id)


