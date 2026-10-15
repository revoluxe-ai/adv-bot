"""Runtime configuration for the MCP read-only channel.

Хост не зашит в продуктовый код маршрутов: issuer, public origin и resource
читаются из окружения. Пустые значения дают канонический публичный origin
``https://mcp.skyline.ru``. Боевое включение — только явный ``MCP_ENABLED=true``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


_DEFAULT_PUBLIC_BASE = "https://mcp.skyline.ru"
_DEFAULT_BOT = "wb_adv_master_bot"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    value = str(raw).strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{name} must be true or false")


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return int(str(raw).strip())


@dataclass(frozen=True, slots=True)
class McpConfig:
    """Снимок настроек MCP на момент запроса.

    ``issuer`` возвращается клиенту без нормализации (без добавления слэша
    и без смены регистра). ``resource`` — audience access token.
    """

    enabled: bool
    public_base_url: str
    issuer: str
    resource: str
    telegram_bot_username: str
    signing_secret: str | None
    transaction_ttl_seconds: int = 600
    ticket_ttl_seconds: int = 300
    code_ttl_seconds: int = 60
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 30 * 24 * 3600
    authorize_limit_per_hour: int = 10
    token_limit_per_hour: int = 30
    tool_limit_per_minute: int = 60
    package_limit_per_hour: int = 6
    inline_file_max_bytes: int = 256 * 1024
    inline_total_max_bytes: int = 1024 * 1024

    @property
    def authorize_endpoint(self) -> str:
        """Абсолютный authorization endpoint из public base."""
        return self.public_base_url.rstrip("/") + "/oauth/authorize"

    @property
    def token_endpoint(self) -> str:
        """Абсолютный token endpoint из public base."""
        return self.public_base_url.rstrip("/") + "/oauth/token"

    @property
    def complete_endpoint(self) -> str:
        """Абсолютный complete endpoint (без query)."""
        return self.public_base_url.rstrip("/") + "/oauth/complete"


def load_mcp_config() -> McpConfig:
    """Собрать конфиг из окружения. ``MCP_ENABLED`` по умолчанию false.

    Returns:
        Снимок настроек. Секрет подписи может быть ``None``: выдача токена
        тогда завершается отказом, процесс бота не падает на импорте.
    """
    public_base = _env_str("MCP_PUBLIC_BASE_URL", _DEFAULT_PUBLIC_BASE)
    issuer = _env_str("MCP_OAUTH_ISSUER", _DEFAULT_PUBLIC_BASE)
    resource_raw = os.environ.get("MCP_RESOURCE_URL")
    if resource_raw is not None and str(resource_raw).strip():
        resource = str(resource_raw).strip()
    else:
        resource = public_base.rstrip("/") + "/mcp"
    secret = os.environ.get("MCP_TOKEN_SIGNING_SECRET")
    signing = str(secret).strip() if secret is not None and str(secret).strip() else None
    return McpConfig(
        enabled=_env_bool("MCP_ENABLED", False),
        public_base_url=public_base,
        issuer=issuer,
        resource=resource,
        telegram_bot_username=_env_str(
            "MCP_TELEGRAM_BOT_USERNAME", _DEFAULT_BOT
        ),
        signing_secret=signing,
        transaction_ttl_seconds=_env_int("MCP_TRANSACTION_TTL_SECONDS", 600),
        ticket_ttl_seconds=_env_int("MCP_TICKET_TTL_SECONDS", 300),
        code_ttl_seconds=_env_int("MCP_CODE_TTL_SECONDS", 60),
        access_token_ttl_seconds=_env_int("MCP_ACCESS_TOKEN_TTL_SECONDS", 900),
        refresh_token_ttl_seconds=_env_int(
            "MCP_REFRESH_TOKEN_TTL_SECONDS", 30 * 24 * 3600
        ),
    )
