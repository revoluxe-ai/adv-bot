from pydantic import Field
from pydantic_settings import BaseSettings


class Neo4jConfig(BaseSettings):
    uri: str = Field(default=..., description="Neo4j URI")
    name: str = Field(default=..., description="Neo4j user")
    password: str = Field(default=..., description="Neo4j password")
    port: int = Field(default=..., description="Neo4j port")

    model_config = {
        "env_prefix": "NEO4J_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Добавляем эту строку для игнорирования лишних полей
    }
