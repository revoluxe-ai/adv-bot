import pytest
from aiogram_tests import MockedBot
from aiogram_tests.handler import CallbackQueryHandler, MessageHandler
from aiogram_tests.types.dataset import MESSAGE

from auto_adv_master.client_bot.user_interface.handlers.start import add_app_token
from auto_adv_master.client_bot.user_interface.views import callbacks

wb_user_cabinet_original_id = 36


@pytest.mark.asyncio
async def test_add_app_token():

    callback = callbacks.AddNewToken(wb_user_cabinet_original_id = wb_user_cabinet_original_id)
    callback_handler = CallbackQueryHandler(add_app_token, callback.filter())
    request = MockedBot(callback_handler)
    calls = await request.query(message=MESSAGE.as_object(text="Hello, Bot!"))
    answer_message = calls.send_messsage.fetchone()
    assert answer_message.text == "Hello, Bot!"

