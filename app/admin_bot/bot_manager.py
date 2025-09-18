import aiogram

from python_modules import path_setting_funcs

# TODO: LEGACY: Чтение токена из файла настроек при импорте модуля.
# Переезжаем на загрузку из окружения через .venv; этот код мешает запуску,
# т.к. тянет файл setting.yaml при импорте. Рассмотреть удаление/рефакторинг под ленивую
# инициализацию с env-first и fallback к файлу только при необходимости.
__setting_path = path_setting_funcs.get_setting_path()
__token = path_setting_funcs.get_document_by_key_name(__setting_path, "admin_telegram_bot_api")

bot = aiogram.Bot(token=__token)
