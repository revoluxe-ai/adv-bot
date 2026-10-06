"""Короткие OAuth-артефакты в Redis: транзакция, билет, код.

Все идентификаторы случайные. Снятие билета и кода — атомарный GETDEL.
Недоступный Redis — отказ, без запасного хранилища.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from typing import Any, Protocol, cast

from app.modules.wb_sky_mcp.errors import McpError, McpStorageError


class AsyncKv(Protocol):
    """Минимальный async Redis, который нужен OAuth-мосту."""

    async def get(self, key: str) -> bytes | str | None: ...

    async def set(self, key: str, value: str, ex: int) -> object: ...

    async def getdel(self, key: str) -> bytes | str | None: ...

    async def ttl(self, key: str) -> int: ...

    async def incr(self, key: str) -> int: ...

    async def expire(self, key: str, seconds: int) -> object: ...


def _decode(value: bytes | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def new_opaque_id() -> str:
    """Идентификатор, который вместе с префиксом ``mcp_`` умещается в 64 символа."""
    return secrets.token_urlsafe(32)


@dataclass(slots=True)
class OAuthTransaction:
    """Незавершённая авторизация. Не является bearer MCP."""

    txn_id: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    scopes: tuple[str, ...]
    resource: str
    status: str
    principal_id: int | None = None
    connection_id: str | None = None

    def to_json(self) -> str:
        """Сериализация для Redis."""
        return json.dumps(
            {
                "txn_id": self.txn_id,
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "state": self.state,
                "code_challenge": self.code_challenge,
                "scopes": list(self.scopes),
                "resource": self.resource,
                "status": self.status,
                "principal_id": self.principal_id,
                "connection_id": self.connection_id,
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, raw: str) -> OAuthTransaction:
        """Разобрать JSON транзакции."""
        payload_obj = json.loads(raw)
        if not isinstance(payload_obj, dict):
            raise McpError("INVALID_ARGUMENT", "oauth transaction is invalid")
        payload = cast(dict[str, Any], payload_obj)
        scopes_raw = payload["scopes"]
        if not isinstance(scopes_raw, list):
            raise McpError("INVALID_ARGUMENT", "oauth transaction is invalid")
        scopes = cast(list[object], scopes_raw)
        principal = payload.get("principal_id")
        return cls(
            txn_id=str(payload["txn_id"]),
            client_id=str(payload["client_id"]),
            redirect_uri=str(payload["redirect_uri"]),
            state=str(payload["state"]),
            code_challenge=str(payload["code_challenge"]),
            scopes=tuple(str(item) for item in scopes),
            resource=str(payload["resource"]),
            status=str(payload["status"]),
            principal_id=int(principal) if principal is not None else None,
            connection_id=(
                str(payload["connection_id"])
                if payload.get("connection_id") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class ReturnTicket:
    """Одноразовый билет возврата в браузер. Не bearer MCP."""

    txn_id: str
    kind: str

    def to_json(self) -> str:
        return json.dumps({"txn_id": self.txn_id, "kind": self.kind})

    @classmethod
    def from_json(cls, raw: str) -> ReturnTicket:
        payload = json.loads(raw)
        return cls(txn_id=str(payload["txn_id"]), kind=str(payload["kind"]))


@dataclass(frozen=True, slots=True)
class AuthorizationCode:
    """Одноразовый код обмена. Не bearer MCP."""

    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    scopes: tuple[str, ...]
    resource: str
    principal_id: int
    connection_id: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "state": self.state,
                "code_challenge": self.code_challenge,
                "scopes": list(self.scopes),
                "resource": self.resource,
                "principal_id": self.principal_id,
                "connection_id": self.connection_id,
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, raw: str) -> AuthorizationCode:
        payload_obj = json.loads(raw)
        if not isinstance(payload_obj, dict):
            raise McpError("INVALID_ARGUMENT", "authorization code is invalid")
        payload = cast(dict[str, Any], payload_obj)
        scopes_raw = payload["scopes"]
        if not isinstance(scopes_raw, list):
            raise McpError("INVALID_ARGUMENT", "authorization code is invalid")
        scopes = cast(list[object], scopes_raw)
        return cls(
            client_id=str(payload["client_id"]),
            redirect_uri=str(payload["redirect_uri"]),
            state=str(payload["state"]),
            code_challenge=str(payload["code_challenge"]),
            scopes=tuple(str(item) for item in scopes),
            resource=str(payload["resource"]),
            principal_id=int(payload["principal_id"]),
            connection_id=str(payload["connection_id"]),
        )


class OAuthRedisStore:
    """Redis-хранилище коротких OAuth-артефактов."""

    def __init__(self, redis: AsyncKv, *, txn_ttl: int, ticket_ttl: int, code_ttl: int) -> None:
        self._redis = redis
        self._txn_ttl = txn_ttl
        self._ticket_ttl = ticket_ttl
        self._code_ttl = code_ttl

    async def save_transaction(self, txn: OAuthTransaction) -> None:
        """Создать транзакцию с TTL. Повтор ключа не перезаписывает чужую сессию."""
        try:
            _ = await self._redis.set(
                f"mcp:txn:{txn.txn_id}",
                txn.to_json(),
                ex=self._txn_ttl,
            )
        except Exception as exc:
            raise McpStorageError("redis unavailable") from exc

    async def read_transaction(self, txn_id: str) -> OAuthTransaction | None:
        """Прочитать транзакцию, не меняя статус."""
        try:
            raw = _decode(await self._redis.get(f"mcp:txn:{txn_id}"))
        except Exception as exc:
            raise McpStorageError("redis unavailable") from exc
        if raw is None:
            return None
        return OAuthTransaction.from_json(raw)

    async def update_transaction(self, txn: OAuthTransaction) -> None:
        """Обновить транзакцию, сохранив оставшийся TTL."""
        key = f"mcp:txn:{txn.txn_id}"
        try:
            ttl = await self._redis.ttl(key)
            if ttl <= 0:
                raise McpError("INVALID_ARGUMENT", "oauth transaction expired")
            _ = await self._redis.set(key, txn.to_json(), ex=ttl)
        except McpError:
            raise
        except Exception as exc:
            raise McpStorageError("redis unavailable") from exc

    async def save_ticket(self, ticket: str, payload: ReturnTicket) -> None:
        """Положить одноразовый билет."""
        try:
            _ = await self._redis.set(
                f"mcp:ticket:{ticket}",
                payload.to_json(),
                ex=self._ticket_ttl,
            )
        except Exception as exc:
            raise McpStorageError("redis unavailable") from exc

    async def consume_ticket(self, ticket: str) -> ReturnTicket | None:
        """Атомарно снять билет. Второй вызов возвращает None."""
        try:
            raw = _decode(await self._redis.getdel(f"mcp:ticket:{ticket}"))
        except Exception as exc:
            raise McpStorageError("redis unavailable") from exc
        if raw is None:
            return None
        return ReturnTicket.from_json(raw)

    async def save_code(self, code: str, payload: AuthorizationCode) -> None:
        """Положить код авторизации с коротким TTL."""
        try:
            _ = await self._redis.set(
                f"mcp:code:{code}",
                payload.to_json(),
                ex=self._code_ttl,
            )
        except Exception as exc:
            raise McpStorageError("redis unavailable") from exc

    async def consume_code(self, code: str) -> AuthorizationCode | None:
        """Атомарно снять код. Повторное предъявление не возвращает payload."""
        try:
            raw = _decode(await self._redis.getdel(f"mcp:code:{code}"))
        except Exception as exc:
            raise McpStorageError("redis unavailable") from exc
        if raw is None:
            return None
        return AuthorizationCode.from_json(raw)
