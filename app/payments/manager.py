from yookassa import Configuration

from python_modules import path_setting_funcs

path_settings = path_setting_funcs.get_setting_path()

AccountId = path_setting_funcs.get_document_by_key_name(path_settings, "AccountId")

SecretKey = ...

Configuration.configure("<Account Id>", "<Secret Key>")
