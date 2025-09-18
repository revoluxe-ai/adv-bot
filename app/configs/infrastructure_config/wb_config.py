from pydantic import Field
from pydantic_settings import BaseSettings


class WBConfig(BaseSettings):
    """Настройки, относящиеся к работе с WB API и токенами"""

    test_mode: bool = Field(
        default=False,
        description="Флаг тестового режима. Если True, используются тестовые токены и настройки.",
    )
    test_token: str = Field(
        default="test_token_value",
        description="Тестовый токен для использования в тестовом режиме.",
    )

    model_config = {
        "env_prefix": "WB_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
