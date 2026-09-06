from aiogram import Router, types

router = Router()


@router.message()
async def _echo(message: types.Message):
    try:
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        await message.answer("Попробуйте еще раз!") 
