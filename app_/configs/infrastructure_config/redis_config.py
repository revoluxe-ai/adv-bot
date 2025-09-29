from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    host: str
    port: int
    db: int = 0
    password: str | None = None

    model_config = {
        "env_prefix": "REDIS_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Добавляем эту строку для игнорирования лишних полей
    }
