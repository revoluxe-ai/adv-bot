from python_modules.path_setting_funcs import get_document_by_key_name

setting_path = 'setting.yaml'


class Settings:

    @property
    def cv(self):
        return get_document_by_key_name(setting_path, 'cv')

    @property
    def test_mode(self):
        return get_document_by_key_name(setting_path, 'test_mode')


    @property
    def polling_mode(self):
        return get_document_by_key_name(setting_path, 'polling_mode')

    @property
    def WEBHOOK_URL(self):
        return get_document_by_key_name(setting_path, 'WEBHOOK_URL')

    @property
    def COUNT_SEMAPHORE_TO_POSTGRES(self):
        return get_document_by_key_name(setting_path, 'COUNT_SEMAPHORE_TO_POSTGRES')



settings = Settings()
