import os

class Settings:
    @property
    def clickhouse_host(self) -> str | None:
        return os.environ.get("CLICK_HOUSE_HOST")

    @property
    def clickhouse_user(self) -> str | None:
        return os.environ.get("CLICK_HOUSE_USER")

    @property
    def clickhouse_password(self) -> str | None:
        value = os.environ.get("CLICK_HOUSE_PASSWORD")
        assert value
        assert isinstance(value, str)
        return value

    @property
    def CH_MAX_THREAD(self) -> int:
        value = os.environ.get("CH_MAX_THREAD")
        if value is None:
            return 10
        return int(value)

    @property
    def CLICKHOUSE_PORT(self) -> int:
        value = os.environ.get("CLICKHOUSE_PORT")
        if value is None:
            return 9000
        return int(value)

    # Настройки, скопированные из legacy shared_lib/settings_master.py
    @property
    def PG_POOL_SIZE(self) -> int:
        value = os.getenv("PG_POOL_SIZE")
        if not value:
            return 200
        else:
            return int(value)

    @property
    def PG_MAX_OVERFLOW(self) -> int:
        value = os.getenv("PG_MAX_OVERFLOW")
        if not value:
            return 250
        else:
            return int(value)

    @property
    def COUNT_SEMAPHORE_TO_POSTGRES(self) -> int:
        value = os.environ.get("COUNT_SEMAPHORE_TO_POSTGRES")
        if value is None:
            return 10
        return int(value)

    # Postgres settings (copied behavior from legacy: raise if missing)
    @property
    def postgres_port(self) -> int:
        value = os.environ.get("POSTGRES_PORT")
        if value is None:
            raise ValueError("POSTGRES_PORT is not set")
        return int(value)

    @property
    def postgres_dbname(self) -> str:
        value = os.environ.get("POSTGRES_DBNAME")
        if value is None:
            raise ValueError("POSTGRES_DBNAME is not set")
        return value

    @property
    def postgres_password(self) -> str:
        value = os.environ.get("POSTGRES_PASSWORD")
        if value is None:
            raise ValueError("POSTGRES_PASSWORD is not set")
        return value

    @property
    def postgres_user(self) -> str:
        value = os.environ.get("POSTGRES_USER")
        if value is None:
            raise ValueError("POSTGRES_USER is not set")
        return value

    @property
    def postgres_master_host(self) -> str:
        value = os.environ.get("POSTGRES_MASTER_HOST")
        if value is None:
            raise ValueError("POSTGRES_MASTER_HOST is not set")
        return value

    @property
    def postgres_replica_host(self) -> str:
        value = os.environ.get("POSTGRES_REPLICA_HOST")
        if value is None:
            raise ValueError("POSTGRES_REPLICA_HOST is not set")
        return value

    @property
    def ssl_mode(self) -> str | None:
        value = os.environ.get("POSTGRES_SSL_MODE")
        if value is None:
            return None
        return value

    @property
    def LOG_LEVEL(self) -> str:
        value = os.environ.get("LOG_LEVEL")
        if value is None:
            return "INFO"
        return value



settings = Settings()
