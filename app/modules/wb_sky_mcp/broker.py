"""OAuth-мост и вызовы read-only инструментов MCP.

Короткие артефакты живут в Redis. Подключение — в репозитории PostgreSQL.
Магазины читаются заново на каждом shop-bound вызове.
"""

from __future__ import annotations

import datetime
import logging
import secrets
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.modules.ai_package_v1.export.export_service import ExportService
from app.modules.wb_sky_mcp.access_token import (
    AccessClaims,
    decode_access_token,
    issue_access_token,
)
from app.modules.wb_sky_mcp.cimd import (
    Fetcher,
    Resolver,
    validate_cimd_client,
    validate_metadata_url,
)
from app.modules.wb_sky_mcp.config import McpConfig
from app.modules.wb_sky_mcp.connection_logic import (
    McpConnectionState,
    disconnect,
    hash_refresh_token,
    new_refresh_token,
    rotate_refresh,
    store_refresh,
)
from app.modules.wb_sky_mcp.connection_repository import ConnectionRepository
from app.modules.wb_sky_mcp.errors import (
    AuthorizationRedirectError,
    McpError,
    McpStorageError,
)
from app.modules.wb_sky_mcp.grants import ShopGrantReader, require_shop
from app.modules.wb_sky_mcp.oauth_pkce import (
    grants_refresh,
    parse_scopes,
    require_s256_challenge,
    scope_claim,
    verify_pkce,
)
from app.modules.wb_sky_mcp.oauth_store import (
    AuthorizationCode,
    OAuthRedisStore,
    OAuthTransaction,
    ReturnTicket,
    new_opaque_id,
)
from app.modules.wb_sky_mcp.presenter import export_ai_package, parse_period
from app.modules.wb_sky_mcp.rate_limit import RedisRateLimiter

logger = logging.getLogger("wb_sky_mcp.audit")

READ_TOOLS: tuple[str, ...] = (
    "get_profile",
    "list_shops",
    "get_capabilities",
    "get_ai_package",
)
UNSUPPORTED_CAPABILITIES: tuple[str, ...] = (
    "writes",
    "changeset",
    "apply",
    "campaign_create",
)

PrincipalBinder = Callable[[int, str | None], Awaitable[int]]


class Clock(Protocol):
    """Часы для TTL и сроков токенов."""

    def now(self) -> datetime.datetime: ...


class SystemClock:
    """UTC-часы процесса."""

    def now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc)


@dataclass(frozen=True, slots=True)
class AuthorizeRedirect:
    """Куда отправить браузер: только глубокая ссылка бота."""

    location: str
    txn_id: str


@dataclass(frozen=True, slots=True)
class BrowserRedirect:
    """Редирект обратно в OAuth-клиент. Всегда содержит точный iss."""

    location: str


@dataclass(frozen=True, slots=True)
class TokenBundle:
    """Ответ token endpoint. Refresh есть только при offline_access."""

    access_token: str
    expires_in: int
    scope: str
    refresh_token: str | None


@dataclass(frozen=True, slots=True)
class ConsentView:
    """Экран согласия. Открытие ссылки само по себе статус не меняет."""

    txn_id: str
    status: str


@dataclass(frozen=True, slots=True)
class ConfirmView:
    """После подтверждения: ссылка возврата с одноразовым билетом."""

    complete_url: str
    connection_id: str
    principal_id: int


def _redirect(uri: str, params: dict[str, str]) -> str:
    parts = urlsplit(uri)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def _audit(**fields: object) -> None:
    """Аудит без секретов: только заранее перечисленные поля."""
    allowed = (
        "decision",
        "tool",
        "principal_id",
        "shop_id",
        "authorization_version",
        "correlation_id",
        "error_code",
    )
    payload = {key: fields[key] for key in allowed if key in fields}
    logger.info("mcp_audit %s", payload)


class McpBroker:
    """Сценарии authorize → consent → token → read tool."""

    def __init__(
        self,
        *,
        config: McpConfig,
        store: OAuthRedisStore,
        limiter: RedisRateLimiter,
        connections: ConnectionRepository,
        grants: ShopGrantReader,
        export_service: ExportService,
        fetcher: Fetcher,
        resolver: Resolver,
        clock: Clock | None = None,
    ) -> None:
        self.config = config
        self._store = store
        self._limiter = limiter
        self._connections = connections
        self._grants = grants
        self._export_service = export_service
        self._fetcher = fetcher
        self._resolver = resolver
        self._clock = clock if clock is not None else SystemClock()
        self.product_mutations = 0

    def _now(self) -> datetime.datetime:
        return self._clock.now()

    def _authorization_redirect(
        self,
        redirect_uri: str,
        state: str | None,
        exc: McpError,
    ) -> AuthorizationRedirectError:
        """Собрать OAuth error redirect на уже проверенный адрес клиента."""
        if exc.code == "FORBIDDEN_SCOPE":
            error = "invalid_scope"
        elif exc.code == "RATE_LIMITED":
            error = "temporarily_unavailable"
        else:
            error = "invalid_request"
        params = {
            "error": error,
            "error_description": exc.message,
            "iss": self.config.issuer,
        }
        if state:
            params["state"] = state
        return AuthorizationRedirectError(_redirect(redirect_uri, params))

    async def authorize(
        self,
        *,
        client_id: str | None,
        redirect_uri: str | None,
        state: str | None,
        scope: str | None,
        code_challenge: str | None,
        code_challenge_method: str | None,
        resource: str | None,
        client_ip: str,
    ) -> AuthorizeRedirect:
        """Создать Redis-транзакцию и вернуть только deep link бота.

        Ошибки до проверки CIMD остаются ``McpError`` и не редиректятся.
        После доверенных ``client_id`` и ``redirect_uri`` ошибки запроса
        становятся ``AuthorizationRedirectError`` с ``error``, ``state`` и
        точным ``iss``. Код авторизации при этом не выдаётся.

        Raises:
            McpError: клиент или redirect ещё не доверены.
            AuthorizationRedirectError: клиент доверен, но запрос некорректен.
            McpStorageError: Redis недоступен (транзакция не создаётся).
        """
        redirect = await validate_cimd_client(
            client_id,
            redirect_uri,
            fetcher=self._fetcher,
            resolver=self._resolver,
        )
        try:
            if not state:
                raise McpError("INVALID_ARGUMENT", "state is required")
            if resource != self.config.resource:
                raise McpError("INVALID_ARGUMENT", "resource is not accepted")
            challenge = require_s256_challenge(code_challenge_method, code_challenge)
            scopes = parse_scopes(scope)
            identity = f"{client_id}|{client_ip}"
            await self._limiter.hit(
                "authorize",
                identity,
                limit=self.config.authorize_limit_per_hour,
                window_seconds=3600,
            )
        except McpStorageError:
            raise
        except McpError as exc:
            raise self._authorization_redirect(redirect, state, exc) from exc
        txn_id = new_opaque_id()
        txn = OAuthTransaction(
            txn_id=txn_id,
            client_id=str(client_id),
            redirect_uri=redirect,
            state=state,
            code_challenge=challenge,
            scopes=scopes,
            resource=self.config.resource,
            status="pending",
        )
        await self._store.save_transaction(txn)
        username = self.config.telegram_bot_username
        location = f"https://t.me/{username}?start=mcp_{txn_id}"
        _audit(decision="authorize", correlation_id=str(uuid.uuid4()))
        return AuthorizeRedirect(location=location, txn_id=txn_id)

    async def inspect_start(self, txn_id: str) -> ConsentView:
        """Показать согласие. Статус транзакции не становится approved."""
        txn = await self._require_txn(txn_id)
        return ConsentView(txn_id=txn.txn_id, status=txn.status)

    async def confirm(
        self,
        txn_id: str,
        *,
        telegram_user_id: int,
        username: str | None,
        bind_principal: PrincipalBinder,
    ) -> ConfirmView:
        """Явное подтверждение связывает сессию с ``User.id``.

        ``telegram_user_id`` не записывается как субъект токена.
        """
        txn = await self._require_txn(txn_id)
        if txn.status != "pending":
            raise McpError("INVALID_ARGUMENT", "oauth transaction is not pending")
        principal_id = await bind_principal(telegram_user_id, username)
        now = self._now()
        state = McpConnectionState.create(principal_id, now=now)
        await self._connections.add(state)
        txn.status = "approved"
        txn.principal_id = principal_id
        txn.connection_id = state.public_id
        await self._store.update_transaction(txn)
        ticket = secrets.token_urlsafe(32)
        await self._store.save_ticket(
            ticket, ReturnTicket(txn_id=txn.txn_id, kind="allow")
        )
        complete_url = f"{self.config.complete_endpoint}?ticket={ticket}"
        _audit(
            decision="confirm",
            principal_id=principal_id,
            correlation_id=str(uuid.uuid4()),
        )
        return ConfirmView(
            complete_url=complete_url,
            connection_id=state.public_id,
            principal_id=principal_id,
        )

    async def cancel(self, txn_id: str) -> str:
        """Отмена. Возвращает одноразовую ссылку с ошибкой для клиента OAuth."""
        txn = await self._require_txn(txn_id)
        if txn.status != "pending":
            raise McpError("INVALID_ARGUMENT", "oauth transaction is not pending")
        txn.status = "cancelled"
        await self._store.update_transaction(txn)
        ticket = secrets.token_urlsafe(32)
        await self._store.save_ticket(
            ticket, ReturnTicket(txn_id=txn.txn_id, kind="deny")
        )
        return f"{self.config.complete_endpoint}?ticket={ticket}"

    async def complete(self, ticket: str | None) -> BrowserRedirect:
        """Снять билет и либо выдать code, либо вернуть access_denied.

        Повтор билета отклоняется. Адрес берётся только из транзакции.
        """
        if not ticket:
            raise McpError("INVALID_ARGUMENT", "ticket is required")
        payload = await self._store.consume_ticket(ticket)
        if payload is None:
            raise McpError("INVALID_ARGUMENT", "ticket rejected")
        txn = await self._require_txn(payload.txn_id)
        iss = self.config.issuer
        if payload.kind == "deny" or txn.status == "cancelled":
            location = _redirect(
                txn.redirect_uri,
                {"error": "access_denied", "state": txn.state, "iss": iss},
            )
            return BrowserRedirect(location=location)
        if (
            txn.status != "approved"
            or txn.principal_id is None
            or txn.connection_id is None
        ):
            raise McpError("INVALID_ARGUMENT", "oauth transaction is not approved")
        code = secrets.token_urlsafe(32)
        await self._store.save_code(
            code,
            AuthorizationCode(
                client_id=txn.client_id,
                redirect_uri=txn.redirect_uri,
                state=txn.state,
                code_challenge=txn.code_challenge,
                scopes=txn.scopes,
                resource=txn.resource,
                principal_id=txn.principal_id,
                connection_id=txn.connection_id,
            ),
        )
        location = _redirect(
            txn.redirect_uri,
            {"code": code, "state": txn.state, "iss": iss},
        )
        return BrowserRedirect(location=location)

    async def exchange_token(
        self,
        form: dict[str, str],
        *,
        client_ip: str,
    ) -> TokenBundle:
        """Обменять код или refresh. Resource обязателен и должен совпасть.

        ``client_ip`` зарезервирован для лимита token, ключ которого — клиент
        и принципал, когда они уже известны.
        """
        _ = client_ip
        grant = form.get("grant_type")
        resource = form.get("resource")
        if resource != self.config.resource:
            raise McpError("INVALID_ARGUMENT", "resource is not accepted")
        if grant == "authorization_code":
            return await self._exchange_code(form)
        if grant == "refresh_token":
            return await self._exchange_refresh(form)
        raise McpError("INVALID_ARGUMENT", "grant_type is not supported")

    async def _exchange_code(self, form: dict[str, str]) -> TokenBundle:
        code = form.get("code")
        if not code:
            raise McpError("INVALID_ARGUMENT", "code is required")
        payload = await self._store.consume_code(code)
        if payload is None:
            raise McpError("INVALID_ARGUMENT", "authorization code rejected")
        if form.get("redirect_uri") != payload.redirect_uri:
            raise McpError("INVALID_ARGUMENT", "redirect_uri mismatch")
        if form.get("client_id") != payload.client_id:
            raise McpError("INVALID_ARGUMENT", "client_id mismatch")
        if form.get("resource") != payload.resource:
            raise McpError("INVALID_ARGUMENT", "resource is not accepted")
        verify_pkce(form.get("code_verifier"), payload.code_challenge)
        await self._limiter.hit(
            "token",
            f"{payload.client_id}|{payload.principal_id}",
            limit=self.config.token_limit_per_hour,
            window_seconds=3600,
        )
        state = await self._connections.get(payload.connection_id)
        if state is None or state.revoked_at is not None:
            raise McpError("UNAUTHENTICATED", "connection revoked")
        if state.user_id != payload.principal_id:
            raise McpError("UNAUTHENTICATED", "principal mismatch")
        refresh_token: str | None = None
        scope = scope_claim(payload.scopes)
        if grants_refresh(payload.scopes):
            raw = new_refresh_token()
            _ = store_refresh(
                state,
                raw,
                now=self._now(),
                ttl_seconds=self.config.refresh_token_ttl_seconds,
            )
            await self._connections.save(state)
            refresh_token = raw
        access = issue_access_token(
            self.config,
            principal_id=payload.principal_id,
            connection_id=payload.connection_id,
            scope=scope,
            authorization_version=state.authorization_version,
            now=int(self._now().timestamp()),
        )
        _audit(
            decision="token",
            principal_id=payload.principal_id,
            authorization_version=state.authorization_version,
            correlation_id=str(uuid.uuid4()),
        )
        return TokenBundle(
            access_token=access,
            expires_in=self.config.access_token_ttl_seconds,
            scope=scope,
            refresh_token=refresh_token,
        )

    async def _exchange_refresh(self, form: dict[str, str]) -> TokenBundle:
        """Обменять refresh под блокировкой строки. Клиент — allowlist CIMD URL.

        Повтор того же refresh, отзыв и несовпадение версии не выпускают
        второй токен. Срок access и refresh берётся из текущего конфига.
        """
        presented = form.get("refresh_token")
        client_id = form.get("client_id")
        if not presented or not client_id:
            raise McpError("INVALID_ARGUMENT", "refresh token rejected")
        _ = validate_metadata_url(client_id)
        presented_hash = hash_refresh_token(presented)
        preview = await self._connections.find_by_refresh_hash(presented_hash)
        if preview is None:
            raise McpError("UNAUTHENTICATED", "refresh token rejected")
        await self._limiter.hit(
            "token",
            f"{client_id}|{preview.user_id}",
            limit=self.config.token_limit_per_hour,
            window_seconds=3600,
        )

        def _apply(state: McpConnectionState) -> str:
            if state.revoked_at is not None:
                raise McpError("UNAUTHENTICATED", "connection revoked")
            if state.authorization_version < 1:
                raise McpError("UNAUTHENTICATED", "stale authorization_version")
            return rotate_refresh(
                state,
                presented,
                now=self._now(),
                ttl_seconds=self.config.refresh_token_ttl_seconds,
            )

        try:
            rotated = await self._connections.apply_refresh_rotation(
                presented_hash, _apply
            )
        except McpError:
            _audit(
                decision="deny",
                principal_id=preview.user_id,
                authorization_version=preview.authorization_version,
                error_code="UNAUTHENTICATED",
                correlation_id=str(uuid.uuid4()),
            )
            raise
        if rotated is None:
            raise McpError("UNAUTHENTICATED", "refresh token rejected")
        state, fresh = rotated
        access = issue_access_token(
            self.config,
            principal_id=state.user_id,
            connection_id=state.public_id,
            scope="wbsky:read",
            authorization_version=state.authorization_version,
            now=int(self._now().timestamp()),
        )
        return TokenBundle(
            access_token=access,
            expires_in=self.config.access_token_ttl_seconds,
            scope="wbsky:read",
            refresh_token=fresh,
        )

    async def disconnect(self, *, user_id: int, connection_id: str) -> McpConnectionState:
        """Отключить подключение этого пользователя. Чужое не трогает."""
        state = await self._connections.get(connection_id)
        if state is None or state.user_id != user_id:
            raise McpError("INVALID_ARGUMENT", "connection not found")
        disconnect(state, now=self._now())
        await self._connections.save(state)
        _audit(
            decision="disconnect",
            principal_id=user_id,
            authorization_version=state.authorization_version,
            correlation_id=str(uuid.uuid4()),
        )
        return state

    async def list_connections(self, user_id: int) -> list[McpConnectionState]:
        """Активные и отозванные подключения пользователя, без секретов."""
        return await self._connections.list_for_user(user_id)

    async def authenticate(self, token: str | None) -> tuple[AccessClaims, McpConnectionState]:
        """Проверить bearer и живую строку подключения. Запись не делает."""
        if not token:
            raise McpError("UNAUTHENTICATED", "bearer required")
        claims = decode_access_token(self.config, token)
        try:
            state = await self._connections.get(claims.connection_id)
        except McpStorageError:
            raise
        if state is None or state.user_id != claims.principal_id:
            reason = "connection rejected"
        elif state.revoked_at is not None:
            reason = "connection revoked"
        elif state.authorization_version != claims.authorization_version:
            reason = "stale authorization_version"
        else:
            return claims, state
        _audit(
            decision="deny",
            tool="authenticate",
            principal_id=claims.principal_id,
            authorization_version=claims.authorization_version,
            error_code="UNAUTHENTICATED",
            correlation_id=str(uuid.uuid4()),
        )
        raise McpError("UNAUTHENTICATED", reason)

    async def call_tool(
        self,
        *,
        bearer: str | None,
        name: str,
        arguments: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Вызвать один из четырёх read tools. Иное имя не доходит до экспорта."""
        claims, _state = await self.authenticate(bearer)
        args = arguments or {}
        if name not in READ_TOOLS:
            _audit(
                decision="deny",
                tool=name,
                principal_id=claims.principal_id,
                error_code="UNSUPPORTED",
                correlation_id=str(uuid.uuid4()),
            )
            raise McpError("UNSUPPORTED", "tool is not available")
        await self._limiter.hit(
            "tool",
            str(claims.principal_id),
            limit=self.config.tool_limit_per_minute,
            window_seconds=60,
        )
        if name == "get_profile":
            return self._profile(claims)
        if name == "list_shops":
            shops = await self._grants.list_shops(claims.principal_id)
            return {
                "shops": [
                    {
                        "shop_id": shop.shop_id,
                        "name": shop.name,
                        "active": shop.active,
                    }
                    for shop in shops
                ]
            }
        shop_id = args.get("shop_id")
        try:
            grants = await self._grants.list_shops(claims.principal_id)
        except McpStorageError:
            _audit(
                decision="deny",
                tool=name,
                principal_id=claims.principal_id,
                error_code="AUTH_BACKEND_UNAVAILABLE",
                correlation_id=str(uuid.uuid4()),
            )
            raise
        grant = require_shop(grants, shop_id)
        if name == "get_capabilities":
            return {
                "shop_id": grant.shop_id,
                "read_only": True,
                "supported": list(READ_TOOLS),
                "unsupported": list(UNSUPPORTED_CAPABILITIES),
            }
        await self._limiter.hit(
            "package",
            f"{claims.principal_id}|{grant.shop_id}",
            limit=self.config.package_limit_per_hour,
            window_seconds=3600,
        )
        period = parse_period(args.get("period_start"), args.get("period_end"))
        _audit(
            decision="allow",
            tool=name,
            principal_id=claims.principal_id,
            shop_id=grant.shop_id,
            authorization_version=claims.authorization_version,
            correlation_id=str(uuid.uuid4()),
        )
        return await export_ai_package(
            self._export_service,
            shop_id=grant.shop_id,
            period=period,
            config=self.config,
        )

    def _profile(self, claims: AccessClaims) -> dict[str, Any]:
        return {
            "principal_id": claims.principal_id,
            "connection_id": claims.connection_id,
            "scope": claims.scope,
            "authorization_version": claims.authorization_version,
        }

    async def _require_txn(self, txn_id: str) -> OAuthTransaction:
        txn = await self._store.read_transaction(txn_id)
        if txn is None:
            raise McpError("INVALID_ARGUMENT", "oauth transaction expired")
        return txn
