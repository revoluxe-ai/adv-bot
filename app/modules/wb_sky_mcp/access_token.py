"""Подпись и проверка access token. Секрет только из runtime-конфига."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import jwt

from app.modules.wb_sky_mcp.config import McpConfig
from app.modules.wb_sky_mcp.errors import McpError

_ALGORITHM = "HS256"


@dataclass(frozen=True, slots=True)
class AccessClaims:
    """Проверенные claims access token. Списка магазинов здесь нет."""

    principal_id: int
    connection_id: str
    scope: str
    authorization_version: int
    issuer: str
    audience: str
    jti: str


def issue_access_token(
    config: McpConfig,
    *,
    principal_id: int,
    connection_id: str,
    scope: str,
    authorization_version: int,
    now: int | None = None,
) -> str:
    """Подписать bearer на 15 минут (или TTL из конфига).

    Raises:
        McpError: если секрет подписи не задан.
    """
    if not config.signing_secret:
        raise McpError("AUTH_BACKEND_UNAVAILABLE", "signing secret is not configured")
    issued = int(time.time()) if now is None else now
    payload = {
        "iss": config.issuer,
        "sub": str(principal_id),
        "aud": config.resource,
        "exp": issued + config.access_token_ttl_seconds,
        "iat": issued,
        "scope": scope,
        "authorization_version": authorization_version,
        "jti": str(uuid.uuid4()),
        "connection_id": connection_id,
    }
    token = jwt.encode(payload, config.signing_secret, algorithm=_ALGORITHM)
    if isinstance(token, bytes):
        return token.decode("ascii")
    return token


def decode_access_token(config: McpConfig, token: str) -> AccessClaims:
    """Проверить подпись, issuer, audience, срок и обязательные claims.

    Issuer сравнивается с конфигом как есть, без нормализации.

    Raises:
        McpError: токен недействителен.
    """
    if not config.signing_secret:
        raise McpError("UNAUTHENTICATED", "signing secret is not configured")
    try:
        payload = jwt.decode(
            token,
            config.signing_secret,
            algorithms=[_ALGORITHM],
            audience=config.resource,
            issuer=config.issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise McpError("UNAUTHENTICATED", "access token expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise McpError("UNAUTHENTICATED", "issuer mismatch") from exc
    except jwt.InvalidAudienceError as exc:
        raise McpError("UNAUTHENTICATED", "audience mismatch") from exc
    except jwt.PyJWTError as exc:
        raise McpError("UNAUTHENTICATED", "access token rejected") from exc
    if payload.get("iss") != config.issuer:
        raise McpError("UNAUTHENTICATED", "issuer mismatch")
    audience = payload.get("aud")
    if audience != config.resource:
        raise McpError("UNAUTHENTICATED", "audience mismatch")
    scope = payload.get("scope")
    if not isinstance(scope, str) or "wbsky:read" not in scope.split():
        raise McpError("FORBIDDEN_SCOPE", "scope wbsky:read is required")
    if any(
        item in scope.split()
        for item in ("write", "changeset", "apply", "admin")
    ):
        raise McpError("FORBIDDEN_SCOPE", "scope is not allowed")
    version = payload.get("authorization_version")
    connection_id = payload.get("connection_id")
    if not isinstance(version, int) or not isinstance(connection_id, str):
        raise McpError("UNAUTHENTICATED", "access token rejected")
    try:
        principal_id = int(str(payload["sub"]))
    except (TypeError, ValueError) as exc:
        raise McpError("UNAUTHENTICATED", "access token rejected") from exc
    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise McpError("UNAUTHENTICATED", "access token rejected")
    return AccessClaims(
        principal_id=principal_id,
        connection_id=connection_id,
        scope=scope,
        authorization_version=version,
        issuer=str(payload["iss"]),
        audience=str(audience),
        jti=jti,
    )
