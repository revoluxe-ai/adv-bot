from aiogram import Router
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, chat_member_updated

router = Router()


@router.chat_member(chat_member_updated.ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def catch_bot_adding_to_channel(event: chat_member_updated.ChatMemberUpdated):
    chat_id = event.chat.id
    print(chat_id)

