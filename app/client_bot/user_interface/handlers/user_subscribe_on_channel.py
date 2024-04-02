import aiogram
from aiogram import Router
from aiogram.filters import chat_member_updated, IS_NOT_MEMBER, IS_MEMBER
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberRestricted
from aiogram import F
from app.client_bot.user_interface.views import messages
from app.client_bot.const import SUPPORT_CHANNEL_ID
from app.client_bot.user_interface.views import callbacks


router = Router()


@router.chat_member(chat_member_updated.ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def catch_bot_adding_to_channel(event: chat_member_updated.ChatMemberUpdated):
    chat_id = event.chat.id
    if chat_id == SUPPORT_CHANNEL_ID:
        user_id = event.from_user.id
        await event.bot.send_message(user_id,
                                     text='Подписка подтверждена, для продолжения нажмите /start')

    return

# @router.callback_query(callbacks.CheckSubscribe.filter())
# async def catch_bot_adding_to_channel(callback: aiogram.types.CallbackQuery,
#                                       callback_data: callbacks.CheckSubscribe,
#                                       bot: aiogram.Bot, state: FSMContext):
#     chat_id = callback.message.chat.id
#
#     await bot.send_message(chat_id, text='Подписка подтверждена, для продолжения нажмите /start')
#
#
#     return



@router.chat_member(chat_member_updated.ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER ))
async def catch_bot_adding_to_channel(event: chat_member_updated.ChatMemberUpdated):
    chat_id = event.chat.id
    if chat_id == SUPPORT_CHANNEL_ID:
        user_id = event.from_user.id
        await messages.NeedSubscribe(event.bot, user_id)()

    return






