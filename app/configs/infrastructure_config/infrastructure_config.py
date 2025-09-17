__all__ = ["InfrastructureConfig"]

from pydantic import Field
from pydantic_settings import BaseSettings

from .neo4j_config import Neo4jConfig
from .redis_config import RedisConfig


class InfrastructureConfig(BaseSettings):
    """Конфигурация инфраструктуры - централизованное место для всех внешних сервисов"""

    neo4j: Neo4jConfig = Field(default_factory=lambda: Neo4jConfig.model_construct())
    redis: RedisConfig = Field(default_factory=lambda: RedisConfig.model_construct())

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
