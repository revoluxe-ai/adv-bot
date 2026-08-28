"""Инфраструктурные настройки приложения (активные runtime-зависимости).

Neo4j убран из обязательного surface — см. decision
``neo4j-not-in-runtime-config-di`` / change ``drop-unused-neo4j-config``.
"""

__all__ = ["InfrastructureConfig"]

from collections.abc import Callable
from typing import cast

from pydantic import Field
from pydantic_settings import BaseSettings

from .redis_config import RedisConfig
from .wb_config import WBConfig


class InfrastructureConfig(BaseSettings):
    """Конфигурация инфраструктуры - централизованное место для всех внешних сервисов"""

    # BaseSettings читает REDIS_* из env; cast нужен, т.к. stub требует host/port.
    redis: RedisConfig = Field(
        default_factory=cast(Callable[[], RedisConfig], RedisConfig)
    )
    wb: WBConfig = Field(default_factory=lambda: WBConfig())

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
