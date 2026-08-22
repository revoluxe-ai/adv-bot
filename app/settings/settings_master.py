import dotenv

# TODO: Доделать рассылку по боту, сделать оффер и разослать

# TODO: Решить ошибку при ручном обновлении позиций:  сделать допнастройки, проверять более медленно, желательно через arq, как долгосрочную задачу, чтобы не терялась

# TODO: Сделать встроенную в бот ИИ поддержку, и для моих чатов, и для юзеров

# TODO Сделать CI с прогоном тестов и линтеров, поправить инструкции для Копилота в Git Hub

# TODO: Придумать более надежный способ проверки ключей на индексацию, сейчас хромает, если по запросу бренд + ключ очень много предложений

# TODO: Поменять ссылку на старый канал в боте на видео

# TODO: Сделать уведомлятор об исправлении ошибок в боте

_ = dotenv.load_dotenv()
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
    def run_local(self) -> bool:
        """Флаг локального режима (legacy env RUN_LOCAL).

        Локальная разработка: канон — публичный IP + NodePort из .env
        (см. k8s/network/local-dev-external-access.md). In-app kubectl port-forward
        удалён; DEV_TUNNELS_ENABLED остаётся только denylist для destructive tests.
        """
        value = os.environ.get("RUN_LOCAL")
        if value is None:
            return False
        value = value.strip().lower()
        if value == "false":
            return False
        if value == "true":
            return True
        raise ValueError("Не верное значение в RUN_LOCAL")

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
    def invite_gate(self) -> bool:
        """По умолчанию True: гейт по инвайту включён, если в .env не задано иначе.

        Явно выключить: INVITE_GATE=false
        """
        value = os.environ.get("INVITE_GATE")
        if value is None or not str(value).strip():
            return True
        value = str(value).strip().lower()
        if value == "false":
            return False
        elif value == "true":
            return True
        raise Exception("Не верное значение в INVITE_GATE")

    @property
    def presentation_only(self) -> bool:
        """Режим «только презентация»: минимальный UX, инвайт для заявки, без полного доступа к боту.

        По умолчанию True, если переменная не задана или пустая.
        Полный клиентский бот: PRESENTATION_ONLY_MODE=false
        """
        value = os.environ.get("PRESENTATION_ONLY_MODE")
        if value is None or not str(value).strip():
            return True
        value = str(value).strip().lower()
        if value == "false":
            return False
        elif value == "true":
            return True
        raise Exception("Не верное значение в PRESENTATION_ONLY_MODE")

    @property
    def presentation_notify_telegram_id(self) -> int | None:
        """Telegram ID для уведомлений о заявке на презентацию (иначе const.MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID)."""
        raw = os.environ.get("PRESENTATION_NOTIFY_TELEGRAM_ID")
        if raw is None or not str(raw).strip():
            return None
        return int(str(raw).strip())

    @property
    def extra_admin_telegram_ids(self) -> list[int]:
        """Дополнительные Telegram ID админов (переменная EXTRA_ADMIN_TELEGRAM_IDS, через запятую)."""
        raw = os.environ.get("EXTRA_ADMIN_TELEGRAM_IDS", "")
        if not raw.strip():
            return []
        out: list[int] = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                out.append(int(part))
        return out

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
    def BILLING_TZ(self) -> str:
        value = os.environ.get("BILLING_TZ")
        if value is None:
            return "Europe/Moscow"
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
        """Процент бонуса при пополнении баланса через Telegram (по умолчанию 100%)."""
        value = os.getenv("BALANCE_TOPUP_BONUS_PERCENT")
        if value is None:
            return 100.0
        return float(value)

    @staticmethod
    def _parse_comma_separated_shop_ids(env_var: str) -> list[str]:
        value = os.getenv(env_var)
        if not value:
            return []
        return [
            shop_id.strip()
            for shop_id in value.split(",")
            if shop_id.strip()
        ]

    @property
    def SHOP_FILTER_LIST(self) -> list[str]:
        """Whitelist shop_id для shop-runner: только перечисленные магазины в постановке."""
        return self._parse_comma_separated_shop_ids("SHOP_FILTER_LIST")

    @property
    def SHOP_EXCLUDE_LIST(self) -> list[str]:
        """Blacklist shop_id для shop-runner: исключить из постановки (legacy и воркеры)."""
        return self._parse_comma_separated_shop_ids("SHOP_EXCLUDE_LIST")

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
            return 30
        else:
            return int(value)

    @property
    def PG_MAX_OVERFLOW(self) -> int:
        value = os.getenv("PG_MAX_OVERFLOW")
        if not value:
            return 50
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
            return 60
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

    @property
    def AUTO_BUDGET_TOPUP_AMOUNT(self) -> int:
        value = os.getenv("AUTO_BUDGET_TOPUP_AMOUNT")
        if not value:
            return 1000
        return int(value)

    @property
    def AUTO_BUDGET_MIN_BALANCE(self) -> int:
        value = os.getenv("AUTO_BUDGET_MIN_BALANCE")
        if not value:
            return 500
        return int(value)

    @property
    def AUTO_BUDGET_LOCK_TTL_SEC(self) -> int:
        value = os.getenv("AUTO_BUDGET_LOCK_TTL_SEC")
        if not value:
            return 120
        return int(value)

    @property
    def AUTO_BUDGET_MAX_SINGLE_TOPUP_RATIO(self) -> float:
        value = os.getenv("AUTO_BUDGET_MAX_SINGLE_TOPUP_RATIO")
        if not value:
            return 0.3
        return float(value)

    @property
    def AUTO_BUDGET_VERIFICATION_ATTEMPTS(self) -> int:
        value = os.getenv("AUTO_BUDGET_VERIFICATION_ATTEMPTS")
        if not value:
            return 2
        return int(value)

    @property
    def AUTO_BUDGET_VERIFICATION_DELAY_SEC(self) -> float:
        value = os.getenv("AUTO_BUDGET_VERIFICATION_DELAY_SEC")
        if not value:
            return 2.0
        return float(value)


    @property
    def DEFAULT_MAX_CPM(self) -> int:
        value = os.getenv("DEFAULT_MAX_CPM")
        if not value:
            return 5000
        else:
            return int(value)

    @property
    def TG_TOKENS_FOR_SENDING(self) -> list[str]:
        value: str | None = os.getenv("TG_TOKENS_FOR_SENDING")
        if value is None:
            raise ValueError('not set TG_TOKENS_FOR_SENDING')
        return [token.strip() for token in value.split(',') if token.strip() != '']


    @property
    def MAX_TASKS(self) -> int:
        value = os.getenv("MAX_TASKS")
        if not value:
            return 7
        return int(value)

    @property
    def PROMOTION_HTTP_CONCURRENCY_LIMIT(self) -> int:
        """Макс. одновременных in-flight PROMOTION HTTP запросов (process-wide)."""
        value = os.getenv("PROMOTION_HTTP_CONCURRENCY_LIMIT")
        if not value:
            return 80
        return int(value)


    @property
    def UPDATE_FULL_ADV_STAT_PERIOD(self) -> int:
        value = os.getenv("UPDATE_FULL_ADV_STAT_PERIOD")
        if not value:
            return 60 * 60
        return int(value)


    @property
    def AUTO_SETTING_ACTIVE(self) -> bool:
        value = os.getenv("AUTO_SETTING_ACTIVE")
        if not value:
            return True
        value = value.lower()
        if value == "true":
            return True
        return False

    @property
    def STATS_FRESHNESS_GUARD_ENABLED(self) -> bool:
        """Guard Redis-фильтрации свежести статы в корутинах shop_runner.

        При ``False`` ``_split_advs_by_stats_freshness`` возвращает все РК как fresh
        без обращения к Redis.
        """
        value = os.getenv("STATS_FRESHNESS_GUARD_ENABLED")
        if value is None:
            return True
        value = value.strip().lower()
        if value == "true":
            return True
        if value == "false":
            return False
        raise Exception("STATS_FRESHNESS_GUARD_ENABLED env var is not bool")

    @property
    def V3_PAY_FOR_ORDER_GAP_ENABLE_PLAN_HEADROOM_RATIO(self) -> float:
        """Доля ``plan.max_pay_for_order`` для skip ``PayForOrderGapEnableExecutor``.

        Зона «1 от MAX плана»: при ``fact >= ratio × plan.max`` enable не выполняется.
        По умолчанию ``1`` (порог = plan.max).
        """
        value = os.getenv("V3_PAY_FOR_ORDER_GAP_ENABLE_PLAN_HEADROOM_RATIO")
        if not value:
            return 1
        return float(value)

    @property
    def V3_PAY_FOR_ORDER_OFF_PLAN_HEADROOM_RATIO(self) -> float:
        """Доля ``plan.max_pay_for_order`` для gate ``PayForOrderOverMaxOffOnDeepOverspend``.

        При ``fact >= ratio × plan.max`` — OFF ключей с ``keyword.pay_for_order > max``.
        По умолчанию ``1``.
        """
        value = os.getenv("V3_PAY_FOR_ORDER_OFF_PLAN_HEADROOM_RATIO")
        if not value:
            return 1
        return float(value)

    @property
    def include_synthetic_position_profile(self) -> bool:
        """M/O/C V3: учитывать синтетические позиции ``_fill_positions`` (``ch_observed=False``).

        По умолчанию True. Выключить (только buckets ``bid_decision_log``):
        ``INCLUDE_SYNTHETIC_POSITION_PROFILE=false``
        """
        value = os.environ.get("INCLUDE_SYNTHETIC_POSITION_PROFILE")
        if value is None or not str(value).strip():
            return True
        value = str(value).strip().lower()
        if value == "false":
            return False
        if value == "true":
            return True
        raise ValueError(
            "Не верное значение в INCLUDE_SYNTHETIC_POSITION_PROFILE"
        )

    @property
    def AUTO_SHELF_BID_CONTROL_DRY_RUN(self) -> bool:
        """Dry-run для control-модуля полок.

        Важно:
            - если env-переменная отсутствует, возвращаем False (real mode fallback);
            - явное значение `true|false` обязательно валидируется.
        """
        value = os.getenv("AUTO_SHELF_BID_CONTROL_DRY_RUN")
        if value is None:
            return False
        value = value.strip().lower()
        if value == "true":
            return True
        if value == "false":
            return False
        raise Exception("AUTO_SHELF_BID_CONTROL_DRY_RUN env var is not bool")

    @property
    def PROXY(self) -> str | None:
        """URL прокси для aiogram (Telegram API).

        Явный ``PROXY`` имеет приоритет; иначе берётся ``HTTPS_PROXY`` / ``HTTP_PROXY``
        (как у деплоев с xray, где заданы только стандартные переменные).
        """
        for key in ("PROXY", "HTTPS_PROXY", "HTTP_PROXY"):
            value = os.getenv(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    @property
    def unisender_go_api_key(self) -> str | None:
        value = os.environ.get("UNISENDER_GO_API_KEY")
        if value is None or not str(value).strip():
            return None
        return str(value).strip()

    @property
    def unisender_go_api_base(self) -> str:
        value = os.environ.get("UNISENDER_GO_API_BASE")
        if value is None or not str(value).strip():
            return "https://goapi.unisender.ru/ru/transactional/api/v1"
        return str(value).strip().rstrip("/")

    @property
    def unisender_go_request_timeout_sec(self) -> float:
        value = os.environ.get("UNISENDER_GO_REQUEST_TIMEOUT_SEC")
        if value is None or not str(value).strip():
            return 30.0
        return float(str(value).strip())

    @property
    def unisender_go_default_from_email(self) -> str | None:
        value = os.environ.get("UNISENDER_GO_DEFAULT_FROM_EMAIL")
        if value is None or not str(value).strip():
            return None
        return str(value).strip()

    @property
    def unisender_go_default_global_language(self) -> str | None:
        value = os.environ.get("UNISENDER_GO_DEFAULT_GLOBAL_LANGUAGE")
        if value is None or not str(value).strip():
            return None
        return str(value).strip()

    @property
    def unisender_go_integration_test_recipient(self) -> str | None:
        value = os.environ.get("UNISENDER_GO_INTEGRATION_TEST_RECIPIENT")
        if value is None or not str(value).strip():
            return None
        return str(value).strip()

    @property
    def MIN_BID_AUTO_DEFAULT(self) -> int:
        """Мин. CPM (руб.) для авто/полок при cache miss и в расчётах fallback.

        Env: ``MIN_BID_AUTO_DEFAULT``. Пустое или отсутствующее значение → **100** (руб.).
        Не используется при refresh/backfill min_bids в Redis (там raw miss).
        """
        value = os.environ.get("MIN_BID_AUTO_DEFAULT")
        if value is None or not str(value).strip():
            return 100  # значение в рублях
        return int(str(value).strip())

    @property
    def MIN_BID_SEARCH_DEFAULT(self) -> int:
        """Мин. CPM (руб.) для поиска/аукциона при cache miss и в расчётах fallback.

        Env: ``MIN_BID_SEARCH_DEFAULT``. Пустое или отсутствующее значение → **300** (руб.).
        Пути: cluster bids, stats_stale emergency, UI/cooldown. Не подставляется при
        ``read_min_bids_cache_only`` / backfill (``apply_defaults=False``).
        """
        value = os.environ.get("MIN_BID_SEARCH_DEFAULT")
        if value is None or not str(value).strip():
            return 300  # значение в рублях
        return int(str(value).strip())
    @property
    def AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED(self) -> bool:
        value = os.environ.get("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED")
        if value is None:
            return False
        value = value.strip().lower()
        if value == "true":
            return True
        if value == "false":
            return False
        else:
            raise ValueError(': AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED must be true or false')

    @property
    def CAN_NOT_CACHE_DATA(self) -> bool:
        value = os.environ.get("CAN_NOT_CACHE_DATA")
        if value is None:
            return False
        value = value.strip().lower()
        if value == "true":
            return True
        if value == "false":
            return False
        else:
            raise ValueError(': CAN_MIN_BID_DEFAULT must be true or false')


# TODO: Внедрить полные прогоны Pyright, сначала только узнать надо ли

settings = Settings()
