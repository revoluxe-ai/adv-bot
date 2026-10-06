"""PKCE S256 и разбор scope. Метод ``plain`` не принимается."""

from __future__ import annotations

import base64
import hashlib
import re

from app.modules.wb_sky_mcp.errors import McpError

_VERIFIER_RE = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")
_DATA_SCOPE = "wbsky:read"
_REFRESH_SCOPE = "offline_access"
_ALLOWED = frozenset({_DATA_SCOPE, _REFRESH_SCOPE})


def s256_challenge(verifier: str) -> str:
    """Вернуть base64url(SHA256(verifier)) без padding.

    Args:
        verifier: PKCE code verifier.

    Returns:
        Challenge в кодировке S256.
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def require_s256_challenge(method: str | None, challenge: str | None) -> str:
    """Принять только PKCE S256.

    Raises:
        McpError: если метод не S256 или challenge пуст.
    """
    if method != "S256" or not challenge or not challenge.strip():
        raise McpError("INVALID_ARGUMENT", "PKCE S256 is required")
    return challenge.strip()


def verify_pkce(verifier: str | None, challenge: str) -> None:
    """Сравнить verifier с сохранённым S256 challenge.

    Raises:
        McpError: при отсутствии verifier или несовпадении.
    """
    if verifier is None or not _VERIFIER_RE.fullmatch(verifier):
        raise McpError("INVALID_ARGUMENT", "PKCE verifier is invalid")
    if s256_challenge(verifier) != challenge:
        raise McpError("INVALID_ARGUMENT", "PKCE verifier does not match")


def parse_scopes(raw: str | None) -> tuple[str, ...]:
    """Разобрать scope. Обязателен ``wbsky:read``.

    ``offline_access`` допустим только как технический refresh и не даёт
    прав на данные. Любой другой scope — отказ.

    Raises:
        McpError: если нет scope чтения или есть чужой scope.
    """
    if raw is None or not raw.strip():
        raise McpError("FORBIDDEN_SCOPE", "scope wbsky:read is required")
    parts = tuple(raw.split())
    if _DATA_SCOPE not in parts:
        raise McpError("FORBIDDEN_SCOPE", "scope wbsky:read is required")
    if any(part not in _ALLOWED for part in parts):
        raise McpError("FORBIDDEN_SCOPE", "only wbsky:read and offline_access")
    ordered: list[str] = []
    for part in parts:
        if part not in ordered:
            ordered.append(part)
    return tuple(ordered)


def scope_claim(scopes: tuple[str, ...]) -> str:
    """Строка scope для access token (пробел-разделитель)."""
    return " ".join(scopes)


def grants_refresh(scopes: tuple[str, ...]) -> bool:
    """True, если выдан технический refresh scope."""
    return _REFRESH_SCOPE in scopes
