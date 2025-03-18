import re

from python_modules.path_setting_funcs import get_document_by_key_name, get_setting_path
import os
setting_path = get_setting_path()


class Settings:


    @property
    def postgres_replica_host(self) -> str:
        value = os.environ.get('POSTGRES_REPLICA_HOST')
        return value

    @property
    def postgres_master_host(self):
        value = os.environ.get('POSTGRES_MASTER_HOST')
        return value


    @property
    def postgres_user(self) -> str:
        value = os.environ.get('POSTGRES_USER')
        return value
    @property
    def postgres_password(self) -> str:
        value = os.environ.get('POSTGRES_PASSWORD')
        return value


    @property
    def postgres_dbname(self) -> str:
        value = os.environ.get('POSTGRES_DBNAME')
        return value

    @property
    def cv(self)->bool:
        value = os.environ.get('CV')
        if value is None:
            return False
        value = value.lower()
        if value == 'false':
            return False
        elif value == 'true':
            return True
        raise Exception('Не верное значение в CV')

    @property
    def test_mode(self)-> bool:
        value = os.environ.get('TEST_MODE')
        value = value.lower()
        if value == 'false':
            return False
        elif value == 'true':
            return True

    @property
    def polling_mode(self)-> bool:
        value = os.environ.get('POLLING_MODE')
        if value is None:
            return False
        value = value.lower()
        if value == 'false':
            return False
        elif value == 'true':
            return True
        raise Exception('Не верное значение в POLLING_MODE')


    @property
    def version(self) -> str:
        value = os.environ.get('VERSION')
        return value



    @property
    def WEBHOOK_URL(self):
        value = os.environ.get('WEBHOOK_URL')
        return value


    @property
    def COUNT_SEMAPHORE_TO_POSTGRES(self):
        value = os.environ.get('COUNT_SEMAPHORE_TO_POSTGRES')
        return int(value)


    @property
    def MAX_THREAD_FOR_PROXY(self):
        value = os.environ.get('MAX_THREAD_FOR_PROXY')
        return int(value)


    @property
    def COUNT_THREAD_SQL_KW_STAT_LOAD(self):
        value = os.environ.get('MAX_THREAD_PARSER')
        if value is None:
            return 30
        return int(value)


    @property
    def MAX_THREAD_PARSER(self):
        value = os.environ.get('MAX_THREAD_PARSER')
        return int(value)


    @property
    def MAX_MINUS_KW_THREAD(self):
        value = os.environ.get('MAX_MINUS_KW_THREAD')
        return int(value)

    @property
    def clickhouse_host(self):
        value = os.environ.get('CLICK_HOUSE_HOST')
        return value


    @property
    def clickhouse_user(self):
        value = os.environ.get('CLICK_HOUSE_USER')
        return value

    @property
    def clickhouse_password(self):
        value = os.environ.get('CLICK_HOUSE_PASSWORD')
        assert value
        assert isinstance(value, str)
        return value

    @property
    def WEBHOOK_PATH(self):
        value = os.environ.get('WEBHOOK_PATH')
        return value


    @property
    def TELEGRAM_WEB_PORT(self):
        value = os.environ.get('TELEGRAM_WEB_PORT')
        return int(value)

    @property
    def CH_MAX_THREAD(self):
        value = os.environ.get('CH_MAX_THREAD')
        return int(value)

    @property
    def BIDDER_STEP(self):
        value = os.environ.get('BIDDER_STEP_RUB')
        return int(value)


    @property
    def CLICKHOUSE_PORT(self):
        value  = os.environ.get('CLICKHOUSE_PORT')
        return int(value)


    @property
    def postgres_port(self):
        value  = os.environ.get('POSTGRES_PORT')
        return int(value)


    @property
    def ssl_mode(self):
        value  = os.environ.get('POSTGRES_SSL_MODE')
        return value

    @property
    def postgres_hosts(self):
        value = os.environ.get('POSTGRES_HOST')
        return value


    @property
    def CELERY_PREFIX(self)-> str:
        value  = os.environ.get('CELERY_PREFIX')
        return value

    @property
    def REDIS_MASTER_HOST(self):
        value = os.environ.get('REDIS_MASTER_HOST')
        return value

    @property
    def REDIS_REPLICA_HOST(self):
       value = os.environ.get('REDIS_REPLICA_HOST')
       return value

    @property
    def YOOKASSA_TOKEN(self):
        value = os.environ.get('YOOKASSA_TOKEN')
        assert value
        return value

    @property
    def MIN_SUM(self):
        value = int(os.getenv('MIN_SUM'))
        return value

    @property
    def SHOP_FILTER_LIST(self):
        value = os.getenv('SHOP_FILTER_LIST')
        if value:
            shops_ids = value.split(',')
            shops_ids = [shop_id.strip() for shop_id in shops_ids]
            return shops_ids
        else:
            return []

    @property
    def PAUSE_AFTER_PARSING(self):
        value = os.getenv('PAUSE_AFTER_PARSING')
        if not value:
            return None
        return int(value)

    @property
    def TIME_OUT_FOR_PARSER(self):
        value = os.getenv('TIME_OUT_FOR_PARSER')
        if not value:
            return None
        return int(value)





settings = Settings()
