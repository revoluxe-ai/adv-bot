from aiogram import Bot

from python_modules import path_setting_funcs

path_setting = path_setting_funcs.get_setting_path()

token = path_setting_funcs.get_document_by_key_name(path_setting,
                                                        'client_bot_token',)
bot = Bot(token=token)
