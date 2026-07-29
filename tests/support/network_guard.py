"""Fail-closed outbound network guard для pytest-сессии.

По умолчанию запрещает TCP connect вне loopback. DNS lookup внешних имён
блокируется до резолва. Proxy env очищаются, чтобы не обойти guard.

Патчи:

* ``socket.create_connection``
* ``socket.socket.connect``
* ``socket.socket.connect_ex``
* ``socket.getaddrinfo``
* ``asyncio.BaseEventLoop.sock_connect`` (если доступен)

Разрешено только:

* ``localhost``
* ``127.0.0.1``
* ``::1``
* прочие loopback IP (``ipaddress.is_loopback``)

Production-домены в allowlist добавлять запрещено.
Решение allow/deny принимается **до** вызова оригинального primitive.
"""

from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
import traceback
from collections.abc import Callable
from typing import Any

ALLOWED_HOSTNAMES: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})
_PROXY_ENV_KEYS: tuple[str, ...] = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
)

_guard_installed: bool = False
_original_create_connection: Callable[..., Any] | None = None
_original_connect: Callable[..., Any] | None = None
_original_connect_ex: Callable[..., Any] | None = None
_original_getaddrinfo: Callable[..., Any] | None = None
_original_sock_connect: Callable[..., Any] | None = None
_sock_connect_restore: list[tuple[Any, Callable[..., Any]]] = []


class NetworkGuardError(RuntimeError):
    """Исходящее соединение заблокировано test network guard."""


def _is_loopback_host(host: str) -> bool:
    """True для hostname allowlist или loopback IP."""
    h = host.strip().lower().strip("[]")
    if h in ALLOWED_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def _extract_host(address: Any) -> str | None:
    """Достать hostname из аргумента connect/create_connection."""
    if isinstance(address, tuple) and address:
        host = address[0]
        if isinstance(host, bytes):
            return host.decode(errors="replace")
        return str(host)
    if isinstance(address, str):
        # AF_UNIX path — не TCP; разрешаем только явные loopback string forms.
        return address
    return None


def assert_host_allowed(host: str, *, context: str) -> None:
    """Поднять NetworkGuardError если host не loopback.

    Сообщение содержит host + context + stack, без credentials/DSN.
    """
    if not _is_loopback_host(host):
        stack = "".join(traceback.format_stack(limit=20))
        raise NetworkGuardError(
            f"Outbound network blocked by test guard: host={host!r} "
            f"context={context}\nCall stack:\n{stack}"
        )


def clear_proxy_environment(
    *,
    environ: dict[str, str] | None = None,
) -> dict[str, str]:
    """Удалить proxy env, чтобы они не обходили guard. Возвращает снятые значения."""
    env = environ if environ is not None else os.environ
    removed: dict[str, str] = {}
    for key in _PROXY_ENV_KEYS:
        if key in env:
            removed[key] = env.pop(key)
    return removed


def install_network_guard() -> None:
    """Патч socket + asyncio sock_connect. Идемпотентно. Без сетевых вызовов."""
    global _guard_installed
    global _original_create_connection
    global _original_connect
    global _original_connect_ex
    global _original_getaddrinfo
    global _original_sock_connect
    global _sock_connect_restore

    if _guard_installed:
        return

    clear_proxy_environment()

    _original_create_connection = socket.create_connection
    _original_getaddrinfo = socket.getaddrinfo
    _original_connect = socket.socket.connect
    _original_connect_ex = socket.socket.connect_ex
    _sock_connect_restore = []

    def guarded_create_connection(address, *args, **kwargs):  # type: ignore[no-untyped-def]
        host = _extract_host(address)
        if host is None:
            raise NetworkGuardError(
                f"Outbound network blocked: cannot parse address={address!r}"
            )
        assert_host_allowed(host, context="socket.create_connection")
        assert _original_create_connection is not None
        return _original_create_connection(address, *args, **kwargs)

    def guarded_connect(self, address):  # type: ignore[no-untyped-def]
        # AF_UNIX: address is str/bytes path — allow (local IPC only).
        if isinstance(address, (str, bytes)):
            assert _original_connect is not None
            return _original_connect(self, address)
        host = _extract_host(address)
        if host is None:
            raise NetworkGuardError(
                f"Outbound network blocked: cannot parse connect address={address!r}"
            )
        assert_host_allowed(host, context="socket.socket.connect")
        assert _original_connect is not None
        return _original_connect(self, address)

    def guarded_connect_ex(self, address):  # type: ignore[no-untyped-def]
        """Fail-closed: внешний host — NetworkGuardError до original connect_ex."""
        if isinstance(address, (str, bytes)):
            assert _original_connect_ex is not None
            return _original_connect_ex(self, address)
        host = _extract_host(address)
        if host is None:
            raise NetworkGuardError(
                f"Outbound network blocked: cannot parse connect_ex address={address!r}"
            )
        assert_host_allowed(host, context="socket.socket.connect_ex")
        assert _original_connect_ex is not None
        return _original_connect_ex(self, address)

    def guarded_getaddrinfo(host, *args, **kwargs):  # type: ignore[no-untyped-def]
        host_s = host.decode(errors="replace") if isinstance(host, bytes) else str(host)
        if host_s and not _is_loopback_host(host_s):
            assert_host_allowed(host_s, context="socket.getaddrinfo")
        assert _original_getaddrinfo is not None
        return _original_getaddrinfo(host, *args, **kwargs)

    socket.create_connection = guarded_create_connection  # type: ignore[assignment]
    socket.getaddrinfo = guarded_getaddrinfo  # type: ignore[assignment]
    socket.socket.connect = guarded_connect  # type: ignore[method-assign, assignment]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign, assignment]

    # asyncio: sock_connect на Windows (Proactor) может обходить BaseEventLoop.
    _sock_connect_targets: list[Any] = []
    for _owner in (
        getattr(asyncio.base_events, "BaseEventLoop", None),
        getattr(asyncio.events, "AbstractEventLoop", None),
    ):
        if _owner is not None and hasattr(_owner, "sock_connect"):
            _sock_connect_targets.append(_owner)
    try:
        from asyncio import windows_events as _we

        for _name in ("ProactorEventLoop", "BaseProactorEventLoop"):
            _owner = getattr(_we, _name, None)
            if _owner is not None and hasattr(_owner, "sock_connect"):
                _sock_connect_targets.append(_owner)
    except ImportError:
        pass

    # Deduplicate by id while preserving order.
    _seen: set[int] = set()
    _unique_owners: list[Any] = []
    for _owner in _sock_connect_targets:
        if id(_owner) not in _seen:
            _seen.add(id(_owner))
            _unique_owners.append(_owner)

    if _unique_owners:
        _original_sock_connect = _unique_owners[0].sock_connect

        async def guarded_sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            if isinstance(address, (str, bytes)):
                # AF_UNIX-like — resolve original for this class.
                for owner, saved in _sock_connect_restore:
                    if type(self) is owner or isinstance(self, owner):
                        return await saved(self, sock, address)
                assert _original_sock_connect is not None
                return await _original_sock_connect(self, sock, address)
            host = _extract_host(address)
            if host is None:
                raise NetworkGuardError(
                    f"Outbound network blocked: cannot parse sock_connect "
                    f"address={address!r}"
                )
            # Deny BEFORE any original call — no real TCP.
            assert_host_allowed(host, context="asyncio.loop.sock_connect")
            for owner, saved in _sock_connect_restore:
                if type(self) is owner or isinstance(self, owner):
                    return await saved(self, sock, address)
            assert _original_sock_connect is not None
            return await _original_sock_connect(self, sock, address)

        for _owner in _unique_owners:
            _sock_connect_restore.append((_owner, _owner.sock_connect))
            setattr(_owner, "sock_connect", guarded_sock_connect)

    _guard_installed = True


def uninstall_network_guard(*, _allow_for_guard_unit_tests: bool = False) -> None:
    """Восстановить оригинальные socket/asyncio API.

    Обычным тестам запрещено. Unit-тесты guard передают
    ``_allow_for_guard_unit_tests=True`` либо ``ALLOW_TEST_GUARD_UNINSTALL=1``.
    """
    global _guard_installed
    global _original_create_connection
    global _original_connect
    global _original_connect_ex
    global _original_getaddrinfo
    global _original_sock_connect

    if not _allow_for_guard_unit_tests:
        allow = os.environ.get("ALLOW_TEST_GUARD_UNINSTALL", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not allow:
            raise RuntimeError(
                "uninstall_network_guard is forbidden outside guard unit tests "
                "(pass _allow_for_guard_unit_tests=True or set "
                "ALLOW_TEST_GUARD_UNINSTALL=1)"
            )

    if not _guard_installed:
        return
    if _original_create_connection is not None:
        socket.create_connection = _original_create_connection  # type: ignore[assignment]
    if _original_getaddrinfo is not None:
        socket.getaddrinfo = _original_getaddrinfo  # type: ignore[assignment]
    if _original_connect is not None:
        socket.socket.connect = _original_connect  # type: ignore[method-assign, assignment]
    if _original_connect_ex is not None:
        socket.socket.connect_ex = _original_connect_ex  # type: ignore[method-assign, assignment]
    if _sock_connect_restore:
        for owner, saved in _sock_connect_restore:
            setattr(owner, "sock_connect", saved)
        _sock_connect_restore.clear()
    _original_create_connection = None
    _original_getaddrinfo = None
    _original_connect = None
    _original_connect_ex = None
    _original_sock_connect = None
    _guard_installed = False


def is_network_guard_installed() -> bool:
    """Установлен ли guard в текущем процессе."""
    return _guard_installed
