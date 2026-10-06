"""Проверка client metadata document ChatGPT (CIMD) без открытого fetch.

Сервер скачивает документ только после того, как URL прошёл allowlist хоста
OpenAI/ChatGPT и резолв в публичные адреса. Произвольный URL пользователя
не запрашивается. Метод token endpoint выбирается пересечением с методами
сервера (сейчас только ``none``), а не равенством единственного legacy-поля.
"""

from __future__ import annotations

import ipaddress
import json
import socket
from collections.abc import Awaitable, Callable
from typing import cast
from urllib.parse import urlsplit

from app.modules.wb_sky_mcp.errors import McpError

ALLOWED_CLIENT_HOSTS = frozenset({"chatgpt.com", "chat.openai.com"})
# Публичный PKCE-клиент. ``private_key_jwt`` в этом ремонте не реализуется.
SERVER_TOKEN_ENDPOINT_AUTH_METHODS = frozenset({"none"})
Fetcher = Callable[[str], Awaitable[bytes]]
Resolver = Callable[[str], list[str]]


def _host_allowed(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    return host in ALLOWED_CLIENT_HOSTS


def _reject(message: str) -> McpError:
    return McpError("INVALID_ARGUMENT", message)


def assert_public_resolution(hostname: str, resolver: Resolver) -> None:
    """Отклонить loopback, private, link-local и пустой DNS.

    Args:
        hostname: Уже allowlist-нутый хост.
        resolver: Возвращает список IP-строк.

    Raises:
        McpError: если адрес не публичный.
    """
    try:
        addresses = resolver(hostname)
    except OSError as exc:
        raise _reject("client metadata host did not resolve") from exc
    if not addresses:
        raise _reject("client metadata host did not resolve")
    for raw in addresses:
        try:
            addr = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise _reject("client metadata host did not resolve") from exc
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
            or addr.is_unspecified
        ):
            raise _reject("client metadata host is not a public address")


def default_resolver(hostname: str) -> list[str]:
    """Резолв A/AAAA через системный DNS."""
    infos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    found: list[str] = []
    for info in infos:
        sockaddr = info[4]
        ip = str(sockaddr[0])
        if ip not in found:
            found.append(ip)
    return found


def validate_metadata_url(raw_url: str) -> str:
    """Проверить, что URL — HTTPS-документ на хосте ChatGPT.

    Не выполняет сеть. Отклоняет userinfo, IP-литерал, нестандартный порт,
    query и чужой хост.

    Returns:
        Канонический URL без фрагмента (как его прислал клиент, если он валиден).

    Raises:
        McpError: URL нельзя даже рассматривать как CIMD.
    """
    parts = urlsplit(raw_url.strip())
    if parts.scheme != "https":
        raise _reject("client metadata document must be https")
    if parts.username or parts.password:
        raise _reject("client metadata document rejected")
    if parts.query or parts.fragment:
        raise _reject("client metadata document rejected")
    hostname = parts.hostname
    if hostname is None:
        raise _reject("client metadata document rejected")
    try:
        _ = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise _reject("client metadata document rejected")
    if parts.port not in (None, 443):
        raise _reject("client metadata document rejected")
    if not _host_allowed(hostname):
        raise _reject("client is not a supported ChatGPT identity")
    if not parts.path or parts.path == "/":
        raise _reject("client metadata document rejected")
    return raw_url.strip()


def _validate_redirect(uri: str) -> str:
    parts = urlsplit(uri)
    if parts.scheme != "https" or not parts.hostname:
        raise _reject("redirect_uri is not allowed")
    if parts.username or parts.password:
        raise _reject("redirect_uri is not allowed")
    if not _host_allowed(parts.hostname):
        raise _reject("redirect_uri is not allowed")
    return uri


def select_token_endpoint_auth_method(payload: dict[str, object]) -> str:
    """Выбрать метод token endpoint из пересечения с сервером.

    Плюральное поле клиента — множество методов, которые он умеет.
    Если его нет, совместимое единственное поле считается всем множеством.
    Единственное поле при наличии плюрального — только предпочтение, и
    только когда оно само входит в пересечение. Иначе берётся
    детерминированный метод пересечения (лексикографически первый).

    Returns:
        Выбранный метод. Сейчас это всегда ``none``, если пересечение непусто.

    Raises:
        McpError: пересечение пусто или поля имеют неверный тип.
    """
    legacy = payload.get("token_endpoint_auth_method")
    plural = payload.get("token_endpoint_auth_methods_supported")
    client_methods: set[str] = set()
    if plural is None:
        if not isinstance(legacy, str) or not legacy.strip():
            raise _reject("token endpoint auth method is not supported")
        client_methods.add(legacy)
    else:
        if not isinstance(plural, list) or not plural:
            raise _reject("token endpoint auth method is not supported")
        for item in cast(list[object], plural):
            if not isinstance(item, str) or not item.strip():
                raise _reject("token endpoint auth method is not supported")
            client_methods.add(item)
    intersection = client_methods & SERVER_TOKEN_ENDPOINT_AUTH_METHODS
    if not intersection:
        raise _reject("token endpoint auth method is not supported")
    if isinstance(legacy, str) and legacy in intersection:
        return legacy
    return sorted(intersection)[0]


def parse_client_metadata(document: bytes, client_id: str, redirect_uri: str) -> str:
    """Проверить JSON CIMD: личность, redirect и метод token endpoint.

    Returns:
        Выбранный метод token endpoint. Для текущего сервера это ``none``.

    Raises:
        McpError: документ не описывает совместимого публичного клиента ChatGPT.
    """
    try:
        payload_obj = json.loads(document.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise _reject("client metadata document is invalid") from exc
    if not isinstance(payload_obj, dict):
        raise _reject("client metadata document is invalid")
    payload = cast(dict[str, object], payload_obj)
    if payload.get("client_id") != client_id:
        raise _reject("client metadata identity mismatch")
    name = payload.get("client_name")
    if not isinstance(name, str):
        raise _reject("client metadata identity mismatch")
    lowered = name.lower()
    if "chatgpt" not in lowered and "openai" not in lowered:
        raise _reject("client metadata identity mismatch")
    redirects = payload.get("redirect_uris")
    if not isinstance(redirects, list) or redirect_uri not in redirects:
        raise _reject("redirect_uri is not registered")
    for item in cast(list[object], redirects):
        if not isinstance(item, str):
            raise _reject("redirect_uri is not allowed")
        _ = _validate_redirect(item)
    _ = _validate_redirect(redirect_uri)
    selected = select_token_endpoint_auth_method(payload)
    if selected not in SERVER_TOKEN_ENDPOINT_AUTH_METHODS:
        raise _reject("token endpoint auth method is not supported")
    grants = payload.get("grant_types")
    if not isinstance(grants, list) or "authorization_code" not in grants:
        raise _reject("client metadata document is invalid")
    return selected


async def validate_cimd_client(
    client_id: str | None,
    redirect_uri: str | None,
    *,
    fetcher: Fetcher,
    resolver: Resolver,
) -> str:
    """Полная проверка CIMD. Fetch вызывается только для allowlist-хоста.

    Returns:
        Точный ``redirect_uri``, который можно сохранить в транзакции.

    Raises:
        McpError: клиент, redirect или документ не прошли проверку.
    """
    if not client_id or not redirect_uri:
        raise _reject("client_id and redirect_uri are required")
    safe_url = validate_metadata_url(client_id)
    hostname = urlsplit(safe_url).hostname
    if hostname is None:
        raise _reject("client metadata document rejected")
    assert_public_resolution(hostname, resolver)
    try:
        body = await fetcher(safe_url)
    except McpError:
        raise
    except Exception as exc:
        raise _reject("client metadata document is unavailable") from exc
    if len(body) > 65536:
        raise _reject("client metadata document is invalid")
    _ = parse_client_metadata(body, safe_url, redirect_uri)
    return redirect_uri
