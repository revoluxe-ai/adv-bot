from python_modules.path_setting_funcs import get_document_by_key_name, get_setting_path

setting_path = get_setting_path()


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

    @property
    def MAX_THREAD_FOR_PROXY(self):
        return get_document_by_key_name(setting_path, 'MAX_THREAD_FOR_PROXY')


    @property
    def COUNT_THREAD_SQL_KW_STAT_LOAD(self):
        try:
            return get_document_by_key_name(setting_path, 'COUNT_THREAD_SQL_KW_STAT_LOAD')
        except:
            return 30


    @property
    def MAX_THREAD_PARSER(self):
        return get_document_by_key_name(setting_path, 'MAX_THREAD_PARSER')


    @property
    def MAX_MINUS_KW_THREAD(self):
        return get_document_by_key_name(setting_path, 'MAX_MINUS_KW_THREAD')


    @property
    def clickhouse_host(self):
        return get_document_by_key_name(setting_path, 'click-house-host')
    @property
    def clickhouse_user(self):
        return get_document_by_key_name(setting_path, 'click-house-user')

    @property
    def clickhouse_password(self):
        return get_document_by_key_name(setting_path, 'click-house-password')

    @property
    def WEBHOOK_PATH(self):
        return get_document_by_key_name(setting_path, 'WEBHOOK_PATH')



    @property
    def TELEGRAM_WEB_PORT(self):
        return get_document_by_key_name(setting_path, 'TELEGRAM_WEB_PORT')

    @property
    def CH_MAX_THREAD(self):
        return get_document_by_key_name(setting_path, 'CH_MAX_THREAD')


    @property
    def BIDDER_STEP(self):
        return get_document_by_key_name(setting_path, 'BIDDER_STEP_RUB')

    @property
    def CLICKHOUSE_PORT(self):
        return get_document_by_key_name(setting_path, 'CLICKHOUSE_PORT')


settings = Settings()
