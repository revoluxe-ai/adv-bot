import aiogram
from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
import logging

from app.client_bot import utils
from app.client_bot.user_interface.views import messages

from .. import states
from ..views import callbacks

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(callbacks.RefProgram.filter(F.action == "return"))
async def ref_program_return(callback: types.CallbackQuery, bot: aiogram.Bot) -> None:
    if callback.message is None: return
    assert callback.message.chat is not None
    await messages.RefProgram(bot, callback.message.chat.id)()
    return


@router.message(Command("ref_program"))
async def ref_program(message: types.Message, bot: aiogram.Bot) -> None:
    if message.chat is None: return
    await messages.RefProgram(bot, message.chat.id)()
    return


@router.callback_query(callbacks.RefProgram.filter(F.action == "new"))
async def ref_program_new(callback: types.CallbackQuery, bot: aiogram.Bot, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(states.RefProgram.getting_name)
    message = callback.message
    if message is None: return
    assert message.chat is not None
    await messages.RefLinkGetName(bot, message.chat.id)()
    return


@router.message(StateFilter(states.RefProgram.getting_name))
async def ref_program_getting_name(message: types.Message, bot: aiogram.Bot, state: FSMContext) -> None:
    text = message.text
    if message.chat is None: return
    if message.from_user is None: return
    if text is None or len(text) > 30:
        await messages.RefLinkNameTooLong(bot, message.chat.id)()
        return
    ref_link_name = text
    assert message.from_user is not None
    user_telegram_id = message.from_user.id
    assert ref_link_name is not None
    ref_link = await utils.create_ref_link(ref_link_name, user_telegram_id)
    if not ref_link:
        await messages.RefLinkNameAlreadyExists(bot, message.chat.id)()
        return
    await state.set_state(state=None)
    await messages.RefLinkCreated(bot, message.chat.id, ref_link)()


@router.callback_query(callbacks.RefProgram.filter(F.action == "select"))
async def ref_program_select(callback: types.CallbackQuery, bot: aiogram.Bot) -> None:
    if callback.message and not isinstance(callback.message, aiogram.types.InaccessibleMessage):
        await messages.RefProgramSelect(bot, callback.message.chat.id)()
    else:
        # Обработка случая, когда message отсутствует или недоступно
        # Здесь можно отправить сообщение пользователю, если есть доступ к chat_id из callback.from_user.id
        if callback.from_user:
            await bot.send_message(callback.from_user.id, "Не удалось отобразить реферальную программу.")
        else:
            logger.error("Не удалось получить chat_id для отправки сообщения.")
    return


@router.callback_query(callbacks.RefProgram.filter(F.action == "show_ref_program"))
async def show_ref_program(
    callback: types.CallbackQuery,
    bot: aiogram.Bot,
) -> None:
    if callback.message is None: return
    assert callback.message.chat is not None
    await messages.RefProgram(bot, callback.message.chat.id)()
    return