from aiogram.filters.command import Command
from aiogram import types, Router
from app.client_bot.user_interface.views import messages
import aiogram


router = Router()


@router.message(Command('ref_program'))
async def ref_program(message: types.Message, bot: aiogram.Bot):

    await messages.RefProgram(bot, message.chat.id)()















