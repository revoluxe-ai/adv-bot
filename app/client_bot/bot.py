import os

from aiogram import Bot

from python_modules import path_setting_funcs
import os
from dotenv import load_dotenv
load_dotenv()


token = os.environ.get('TELEGRAM_BOT_TOKEN')

bot = Bot(token=token)

# token = path_setting_funcs.get_document_by_key_name(path_setting,
#                                                         'client_bot_token',)




def get_bot():
    bot = Bot(token=token)
    return bot


