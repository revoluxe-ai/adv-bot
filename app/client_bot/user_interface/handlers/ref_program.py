from aiogram.filters import StateFilter
from aiogram.filters.command import Command
from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from app.client_bot import utils
from app.client_bot.user_interface.views import messages
import aiogram

from .. import states
from ..views import callbacks
from aiogram import F


router = Router()

@router.callback_query(callbacks.RefProgram.filter(F.action == 'return'))
async def ref_program_return(callback: types.CallbackQuery, bot: aiogram.Bot):
    await messages.RefProgram(bot, callback.message.chat.id)()
    return

@router.message(Command('ref_program'))
async def ref_program(message: types.Message, bot: aiogram.Bot):
    await messages.RefProgram(bot, message.chat.id)()
    return


@router.callback_query(callbacks.RefProgram.filter(F.action == 'new'))
async def ref_program_new(callback: types.CallbackQuery, bot: aiogram.Bot,state: FSMContext):
    await state.set_state(states.RefProgram.getting_name)
    message = callback.message
    await messages.RefLinkGetName(bot, message.chat.id)()
    return


@router.message(StateFilter(states.RefProgram.getting_name))
async def ref_program_getting_name(message: types.Message, bot: aiogram.Bot, state: FSMContext):
    text = message.text
    if len(text) > 30:
        await messages.RefLinkNameTooLong(bot, message.chat.id)()
        return
    ref_link_name = text
    user_telegram_id = message.from_user.id
    ref_link = await utils.create_ref_link(ref_link_name, user_telegram_id)
    if not ref_link:
        await messages.RefLinkNameAlreadyExists(bot, message.chat.id)()
        return
    await state.clear()
    await messages.RefLinkCreated(bot, message.chat.id, ref_link)()



@router.callback_query(callbacks.RefProgram.filter(F.action == 'select'))
async def ref_program_select(callback: types.CallbackQuery, bot: aiogram.Bot):
    await messages.RefProgramSelect(bot, callback.message.chat.id)()
    return














