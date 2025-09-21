from app.client_bot.const import SUPPORT_CHANNEL_ID


async def check_user_in_support_channel(bot, user_id: int):
    member = await bot.get_chat_member(SUPPORT_CHANNEL_ID, user_id)
    return member.status in ["member", "creator", "administrator"]
