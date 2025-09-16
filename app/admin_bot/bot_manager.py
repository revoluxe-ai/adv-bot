import aiogram

from python_modules import path_setting_funcs

__setting_path = path_setting_funcs.get_setting_path()
__token = path_setting_funcs.get_document_by_key_name(
    __setting_path, "admin_telegram_bot_api"
)

bot = aiogram.Bot(token=__token)
