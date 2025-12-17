import dotenv

# TODO: Доделать рассылку по боту, сделать оффер и разослать

# TODO: Решить ошибку при ручном обновлении позиций:  сделать допнастройки, проверять более медленно, желательно через arq, как долгосрочную задачу, чтобы не терялась

# TODO: Сделать встроенную в бот ИИ поддержку, и для моих чатов, и для юзеров

# TODO Сделать CI с прогоном тестов и линтеров, поправить инструкции для Копилота в Git Hub

# TODO: Придумать более надежный способ проверки ключей на индексацию, сейчас хромает, если по запросу бренд + ключ очень много предложений

# TODO: Поменять ссылку на старый канал в боте на видео

# TODO: Сделать уведомлятор об исправлении ошибок в боте

dotenv.load_dotenv()
import os


class Settings:
    @property
    def PARSING_KEYWORDS_DELAY_BETWEEN_TASKS(self) -> int:
        value = os.environ.get("PARSING_KEYWORDS_DELAY_BETWEEN_TASKS")
        if value is None:
            return 1
        return int(value)

    @property
    def postgres_replica_host(self) -> str | None:
        value = os.environ.get("POSTGRES_REPLICA_HOST")
        return value

    @property
    def postgres_master_host(self) -> str | None:
        value = os.environ.get("POSTGRES_MASTER_HOST")
        return value

    @property
    def postgres_user(self) -> str | None:
        value = os.environ.get("POSTGRES_USER")
        return value

    @property
    def postgres_password(self) -> str | None:
        value = os.environ.get("POSTGRES_PASSWORD")
        return value

    @property
    def postgres_dbname(self) -> str | None:
        value = os.environ.get("POSTGRES_DBNAME")
        return value

    @property
    def cv(self) -> bool | None:
        value = os.environ.get("CV")
        if value is None:
            return False
        value = value.lower()
        if value == "false":
            return False
        elif value == "true":
            return True
        raise Exception("Не верное значение в CV")

    @property
    def test_mode(self) -> bool:
        value = os.environ.get("TEST_MODE")
        if value is None:
            return False
        value = value.lower()
        if value == "false":
            return False
        elif value == "true":
            return True
        raise Exception("Не верное значение в TEST_MODE")

    @property
    def polling_mode(self) -> bool:
        value = os.environ.get("POLLING_MODE")
        if value is None:
            return False
        value = value.lower()
        if value == "false":
            return False
        elif value == "true":
            return True
        raise Exception("Не верное значение в POLLING_MODE")

    @property
    def version(self) -> str | None:
        value = os.environ.get("VERSION")
        return value

    @property
    def WEBHOOK_URL(self) -> str | None:
        value = os.environ.get("WEBHOOK_URL")
        return value

    @property
    def COUNT_SEMAPHORE_TO_POSTGRES(self) -> int:
        value = os.environ.get("COUNT_SEMAPHORE_TO_POSTGRES")
        if value is None:
            return 10
        return int(value)

    @property
    def MAX_THREAD_FOR_PROXY(self) -> int:
        value = os.environ.get("MAX_THREAD_FOR_PROXY")
        if value is None:
            return 10
        return int(value)

    @property
    def COUNT_THREAD_SQL_KW_STAT_LOAD(self) -> int:
        value = os.environ.get("MAX_THREAD_PARSER")
        if value is None:
            return 30
        return int(value)

    @property
    def MAX_THREAD_PARSER(self) -> int:
        value = os.environ.get("MAX_THREAD_PARSER")
        if value is None:
            return 30
        return int(value)

    @property
    def MAX_MINUS_KW_THREAD(self) -> int:
        value = os.environ.get("MAX_MINUS_KW_THREAD")
        if value is None:
            return 30
        return int(value)

    @property
    def clickhouse_host(self) -> str | None:
        value = os.environ.get("CLICK_HOUSE_HOST")
        return value

    @property
    def clickhouse_user(self) -> str | None:
        value = os.environ.get("CLICK_HOUSE_USER")
        return value

    @property
    def clickhouse_password(self) -> str | None:
        value = os.environ.get("CLICK_HOUSE_PASSWORD")
        assert value
        assert isinstance(value, str)
        return value

    @property
    def WEBHOOK_PATH(self) -> str | None:
        value = os.environ.get("WEBHOOK_PATH")
        return value

    @property
    def TELEGRAM_WEB_PORT(self) -> int:
        value = os.environ.get("TELEGRAM_WEB_PORT")
        if value is None:
            raise ValueError("TELEGRAM_WEB_PORT is not set")
        return int(value)

    @property
    def CH_MAX_THREAD(self) -> int:
        value = os.environ.get("CH_MAX_THREAD")
        if value is None:
            raise ValueError("CH_MAX_THREAD is not set")
        return int(value)

    @property
    def BIDDER_STEP(self) -> int:
        value = os.environ.get("BIDDER_STEP_RUB")
        if value is None:
            raise ValueError("BIDDER_STEP_RUB is not set")
        return int(value)

    @property
    def CLICKHOUSE_PORT(self) -> int:
        value = os.environ.get("CLICKHOUSE_PORT")
        if value is None:
            raise ValueError("CLICKHOUSE_PORT is not set")
        return int(value)

    @property
    def postgres_port(self) -> int:
        value = os.environ.get("POSTGRES_PORT")
        if value is None:
            raise ValueError("POSTGRES_PORT is not set")
        return int(value)

    @property
    def POSTGRES_SSL_CA(self) -> str | None:
        """Путь к CA для проверки серверного сертификата Postgres (опционально)."""
        value = os.environ.get("POSTGRES_SSL_CA")
        return value

    @property
    def POSTGRES_SSL_INSECURE(self) -> bool:
        """Флаг для временной отладки: отключить проверку сертификата (не использовать в проде)."""
        value = os.environ.get("POSTGRES_SSL_INSECURE")
        if value is None:
            return False
        value = value.lower()
        if value == "false":
            return False
        elif value == "true":
            return True
        raise ValueError("Не верное значение в POSTGRES_SSL_INSECURE")

    # TODO: Внедрить STAGE- тесты бота

    # TODO: Понаблюдать за ручным обновлением позиций в клиентской части

    # TODO: Внедрить получение и учет важных новостей от WB, а то теряю, многое случайно узнаю. Также можно внедрить автообработку новостей от блоггеров

    # TODO: Вот такая новость пришла https://seller.wildberries.ru/news-v2/news-details?id=9398

    # TODO Промониторить что там нового в API

    # TODO: Стать авторизованным партнером WB

    # Сделать собиралку телефонов пользователей  бота: для поддержки, для клиентской базы

    # Внедрить автообновление образов при коммитах
    @property
    def POSTGRES_MASTER_HOST(self) -> str | None:
        return os.environ.get("POSTGRES_MASTER_HOST")

    @property
    def POSTGRES_REPLICA_HOST(self) -> str | None:
        return os.environ.get("POSTGRES_REPLICA_HOST")

    @property
    def POSTGRES_DB(self) -> str | None:
        return os.environ.get("POSTGRES_DBNAME")

    @property
    def POSTGRES_USER(self) -> str | None:
        return os.environ.get("POSTGRES_USER")

    @property
    def POSTGRES_PASSWORD(self) -> str | None:
        return os.environ.get("POSTGRES_PASSWORD")

    @property
    def ssl_mode(self) -> str | None:
        # TODO: Тут работало и с None, но Copilot ругался, что будет Рантайм эррор, Smoke-тест прошел
        value = os.environ.get("POSTGRES_SSL_MODE")
        if value is None:
            return "disable"
        return value

    @property
    def postgres_hosts(self) -> str | None:
        value = os.environ.get("POSTGRES_HOST")
        if value is None:
            raise ValueError("POSTGRES_HOST is not set")
        return value

    @property
    def CELERY_PREFIX(self) -> str | None:
        value = os.environ.get("CELERY_PREFIX")
        return value

    @property
    def REDIS_MASTER_HOST(self) -> str | None:
        value = os.environ.get("REDIS_MASTER_HOST")
        if value is None:
            raise ValueError("REDIS_MASTER_HOST environment variable is not set")
        return value

    @property
    def REDIS_REPLICA_HOST(self) -> str | None:
        value = os.environ.get("REDIS_REPLICA_HOST")
        if value is None:
            raise ValueError("REDIS_REPLICA_HOST environment variable is not set")
        return value

    @property
    def YOOKASSA_TOKEN(self) -> str:
        value = os.environ.get("YOOKASSA_TOKEN")
        if value is None:
            raise ValueError("YOOKASSA_TOKEN environment variable is not set")
        return value

    @property
    def MIN_SUM(self) -> int:
        result = os.getenv("MIN_SUM")
        if result is None:
            raise ValueError("MIN_SUM environment variable is not set")
        assert result is not None
        value = int(result)
        return value

    @property
    def BALANCE_TOPUP_BONUS_PERCENT(self) -> float:
        """Процент бонуса при пополнении баланса через Telegram (по умолчанию 200%)."""
        value = os.getenv("BALANCE_TOPUP_BONUS_PERCENT")
        if value is None:
            return 100.0
        return float(value)

    @property
    def SHOP_FILTER_LIST(self) -> list[str]:
        value = os.getenv("SHOP_FILTER_LIST")
        if value:
            shops_ids = value.split(",")
            shops_ids = [shop_id.strip() for shop_id in shops_ids]
            return shops_ids
        else:
            return []

    @property
    def PAUSE_AFTER_PARSING(self) -> int | None:
        value = os.getenv("PAUSE_AFTER_PARSING")
        if not value:
            return None
        return int(value)

    @property
    def TIME_OUT_FOR_PARSER(self) -> int | None:
        value = os.getenv("TIME_OUT_FOR_PARSER")
        if not value:
            return None
        return int(value)

    @property
    def PARSING_TIMEOUT(self) -> int:
        value = os.getenv("PARSING_TIMEOUT")
        if not value:
            return 60 * 60 * 4
        return int(value)

    @property
    def WB_RATE_LIMIT_BASE_DELAY_SEC(self) -> float:
        value = os.getenv("WB_RATE_LIMIT_BASE_DELAY_SEC")
        if not value:
            return 0.1
        return float(value)

    @property
    def WB_RATE_LIMIT_MAX_DELAY_SEC(self) -> float:
        value = os.getenv("WB_RATE_LIMIT_MAX_DELAY_SEC")
        if not value:
            return 300.0
        return float(value)

    @property
    def WB_RATE_LIMIT_MULTIPLIER(self) -> float:
        value = os.getenv("WB_RATE_LIMIT_MULTIPLIER")
        if not value:
            return 2.0
        return float(value)

    @property
    def WB_RATE_LIMIT_SUCCESS_THRESHOLD(self) -> int:
        """Количество успехов подряд для уменьшения задержки."""
        value = os.getenv("WB_RATE_LIMIT_SUCCESS_THRESHOLD")
        if not value:
            return 5
        return int(value)

    @property
    def WB_RATE_LIMIT_DECREASE_FACTOR(self) -> float:
        """Фактор уменьшения задержки при успехах (аддитивное уменьшение)."""
        value = os.getenv("WB_RATE_LIMIT_DECREASE_FACTOR")
        if not value:
            return 0.05  # Уменьшаем на 50ms
        return float(value)

    @property
    def MAX_PARSING_PARALLEL_JOBS(self) -> int:
        value = os.getenv("MAX_PARSING_PARALLEL_JOBS")
        if not value:
            return 10
        return int(value)

    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        value = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not value:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
        return value

    @property
    def WEBHOOK_SECRET(self) -> str:
        value = os.environ.get("WEBHOOK_SECRET")
        if not value:
            raise ValueError("WEBHOOK_SECRET environment variable is not set")
        return value

    @property
    def PARALLER_PARSE_TASKS(self) -> int:
        value = os.environ.get("PARALLER_PARSE_TASKS")
        if not value:
            return 50
        return int(value)

    @property
    def MAX_HOURS_PERIOD_FOR_PARSING_KEYWORDS(self) -> int:
        value = os.getenv("MAX_HOURS_PERIOD_FOR_PARSING_KEYWORDS")
        if not value:
            return 1
        return int(value)

    @property
    def MAX_PAGE_LIMIT_PARSER_WORKER(self) -> int:
        value = os.getenv("MAX_PAGE_LIMIT_PARSER_WORKER")
        if not value:
            return 60
        return int(value)

    @property
    def MIN_DIFF_VIEWS_FOR_PARSING_KEYWORDS(self) -> int:
        value = os.getenv("MIN_DIFF_VIEWS_FOR_PARSING_KEYWORDS")
        if not value:
            return 10
        return int(value)

    @property
    def FULL_STAT_THRESHOLD_DATES(self) -> int:
        value = os.getenv("FULL_STAT_THRESHOLD_DATES")
        if not value:
            return 30
        return int(value)

    @property
    def LOG_LEVEL(self) -> str:
        value = os.getenv("LOG_LEVEL")
        if not value:
            return "ERROR"
        return value

    @property
    def PG_POOL_SIZE(self) -> int:
        value = os.getenv("PG_POOL_SIZE")
        if not value:
            return 5
        else:
            return int(value)

    @property
    def PG_MAX_OVERFLOW(self) -> int:
        value = os.getenv("PG_MAX_OVERFLOW")
        if not value:
            return 10
        else:
            return int(value)

    @property
    def FULL_AUTO_UPDATE_PRICE(self) -> int:
        value = os.getenv("FULL_AUTO_UPDATE_PRICE")
        if not value:
            return 5000
        else:
            return int(value)

    @property
    def WHITE_LIST_AUTO_UPDATER_MONTH_TARIFF(self) -> int:
        value = os.getenv("WHITE_LIST_AUTO_UPDATER_MONTH_TARIFF")
        if not value:
            return int(self.FULL_AUTO_UPDATE_PRICE / 3)
        return int(value)

    @property
    def AUTO_UPDATE_TARGET_PLACE_MONTH_TARIFF(self) -> int:
        value = os.getenv("AUTO_UPDATE_TARGET_PLACE_MONTH_TARIFF")
        if not value:
            return int(self.FULL_AUTO_UPDATE_PRICE / 3)
        return int(value)

    @property
    def AUTO_UPDATE_EXPONENT_MONTH_TARIFF(self) -> int:
        value = os.getenv("AUTO_UPDATE_EXPONENT_MONTH_TARIFF")
        if not value:
            return int(self.FULL_AUTO_UPDATE_PRICE / 3)
        return int(value)

    @property
    def SHOP_UPDATE_TIMEOUT_MINUTES(self) -> int:
        value = os.getenv("SHOP_UPDATE_TIMEOUT_MINUTES")
        if not value:
            return 60
        return int(value)

    @property
    def SHOPS_WORKS_TLL(self) -> int:
        value = os.getenv("SHOPS_WORKS_TLL")
        if not value:
            return 60 * 5
        else:
            return int(value)

    @property
    def DEFAULT_CTR_EXPONENTA(self) -> int:
        value = os.getenv("MAX_HOURS_PERIOD_FOR_PARSING_KEYWORDS")
        if not value:
            return 20
        return int(value)

    @property
    def DEFAULT_MIN_CTR(self) -> float:
        value = os.getenv("DEFAULT_MIN_CTR")
        if not value:
            return 0.1
        return float(value)

    @property
    def START_AUCTION_ON_CREATING_ADV(self) -> bool:
        value = os.environ.get("START_AUCTION_ON_CREATING_ADV")
        if value is None:
            return False
        value = value.lower()
        if value == "false":
            return False
        elif value == "true":
            return True
        raise ValueError("Не верное значение")

    @property
    def REDIS_PORT(self) -> int:
        value = os.environ.get("REDIS_PORT")
        if not value:
            return 6379
        return int(value)

    @property
    def PREDICT_CTR_HOST(self) -> str:
        value = os.environ.get("PREDICT_CTR_HOST")
        if not value:
            return "localhost"
        return value

    @property
    def PREDICT_CTR_PORT(self) -> int:
        value = os.environ.get("PREDICT_CTR_PORT")
        if not value:
            return 50053
        return int(value)

    @property
    def PARSING_LIMITER_DELAY(self) -> float:
        value = os.getenv("PARSING_LIMITER_DELAY")
        if not value:
            return 0.1
        return float(value)


# TODO: Внедрить полные прогоны Pyright, сначала только узнать надо ли
settings = Settings()
