__all__ = ["AppConfig"]

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .infrastructure_config import InfrastructureConfig


class AppConfig(BaseSettings):
    """Главная конфигурация приложения"""

    # Инфраструктурные настройки
    infrastructure: InfrastructureConfig = Field(default_factory=InfrastructureConfig)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="APP_"
    )

    @classmethod
    def create(cls) -> "AppConfig":
        """Фабричный метод для безопасного создания конфигурации"""
        return cls()
