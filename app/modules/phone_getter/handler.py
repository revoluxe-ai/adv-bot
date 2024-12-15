import asyncio
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from .data_manager import DataManager
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


data_manager = DataManager()


@router.message(F.contact)
async def contact_handler(message: types.Message, bot: Bot, state: FSMContext):
    contact: types.Contact = message.contact
    phone_number = contact.phone_number
    user_telegram_id = message.from_user.id

    try:
        state = await state.get_data()
        message_id_for_delete = state['message_id_for_delete']
        await bot.delete_message(user_telegram_id, message_id_for_delete)
    except KeyError:
        pass
    await data_manager.save_phone(user_telegram_id, phone_number)
    await bot.delete_message(message.chat.id, message.message_id)
    message = await bot.send_message(user_telegram_id, "Спасибо за предоставленный контакт! "
                                                       "Мы свяжемся с вами в ближайшее время. "
                                                       "Вы можете продолжить работу с ботом. "
                                                       "Это сообщение исчезнет через несколько секунд. "
                                                       "Повторно выполните желаемое действие в боте")
    await asyncio.sleep(8)
    await bot.delete_message(user_telegram_id, message.message_id)
