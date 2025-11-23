from aiogram import Bot, Router
from aiogram.types import CallbackQuery

from .buttons import UpdatePositionsForActivePhrase

router = Router()


@router.callback_query(UpdatePositionsForActivePhrase.filter())
async def update_positions_for_active_phrase(
    callback_query: CallbackQuery,
    bot: Bot,
) -> None:
    assert callback_query.message
    chat_id = callback_query.message.chat.id
    await bot.send_message(
        chat_id,
        (
           "Данная функция больше не поддерживается со стороны Wildberries"
        ),
    )
    return None

