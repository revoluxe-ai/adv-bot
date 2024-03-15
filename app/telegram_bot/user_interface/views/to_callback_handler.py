import aiogram
import json

from aiogram.fsm.context import FSMContext

from app.my_types import LastMessage
from app.telegram_bot.user_interface.views import callbacks
from app.telegram_bot.user_interface.handlers.adv_setting import choice_adv_paginator, adv


async def to_shop(bot: aiogram.Bot, last_message: LastMessage, wb_user_cabinet_original_id: int,
                  state: FSMContext):
    user = aiogram.types.User(id=last_message.from_user.id,
                              is_bot=False, first_name=last_message.from_user.first_name)
    chat_instance = json.dumps(last_message.chat.__dict__)
    callback_data = callbacks.ChoiceAdvPaginator(page=1,
                                                 wb_user_cabinet_original_id =wb_user_cabinet_original_id)
    # Создание callback_data в соответствии с ожиданиями вашего обработчика
    callback_data_packed = callback_data.pack() # Пример создания данных
    fake_callback_query = aiogram.types.CallbackQuery(
        id="fake_id",
        from_user=user,
        data=callback_data_packed,  # Используем данные напрямую без дополнительной сериализации
        message=last_message,
        bot=bot,
        chat_instance=chat_instance) # Десериализация данных в словарь

    last_message, message_type = await choice_adv_paginator(fake_callback_query,
                                                            callback_data,
                                                            bot,
                                                            state,
                                                            last_message)

    return last_message, message_type


async def to_adv_setting(bot: aiogram.Bot,
                   last_message: LastMessage, wb_user_cabinet_original_id: int,
                   adv_original_id:int):
    user = aiogram.types.User(id=last_message.from_user.id,
                              is_bot=False, first_name=last_message.from_user.first_name)
    chat_instance = json.dumps(last_message.chat.__dict__)
    callback_data = callbacks.Adv(
    action = 'select',
    adv_original_id = adv_original_id,
    wb_user_cabinet_original_id = wb_user_cabinet_original_id


    )
    # Создание callback_data в соответствии с ожиданиями вашего обработчика
    callback_data_packed = callback_data.pack()  # Пример создания данных
    fake_callback_query = aiogram.types.CallbackQuery(
        id="fake_id",
        from_user=user,
        data=callback_data_packed,  # Используем данные напрямую без дополнительной сериализации
        message=last_message,
        bot=bot,
        chat_instance=chat_instance)  # Десериализация данных в словарь

    last_message, message_type = await adv (fake_callback_query,
                                                            callback_data,
                                                            bot,
                                                            last_message)

    return last_message, message_type