__all__ = ["InfrastructureConfig"]

from pydantic import Field
from pydantic_settings import BaseSettings

from .neo4j_config import Neo4jConfig
from .redis_config import RedisConfig
from .wb_config import WBConfig


class InfrastructureConfig(BaseSettings):
    """Конфигурация инфраструктуры - централизованное место для всех внешних сервисов"""

    neo4j: Neo4jConfig = Field(default_factory=lambda: Neo4jConfig())
    redis: RedisConfig = Field(default_factory=lambda: RedisConfig())
    wb: WBConfig = Field(default_factory=lambda: WBConfig())

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
