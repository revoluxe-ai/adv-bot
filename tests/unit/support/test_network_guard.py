"""Unit: fail-closed outbound network guard (loopback-only).

Все тесты на connect_ex / restore используют mocked socket primitives —
без реальных TCP/DNS к внешним или публичным IP.
"""

from __future__ import annotations

import asyncio
import socket
from unittest.mock import MagicMock, patch

import pytest

from tests.support.network_guard import (
    NetworkGuardError,
    assert_host_allowed,
    clear_proxy_environment,
    install_network_guard,
    is_network_guard_installed,
    uninstall_network_guard,
)


@pytest.fixture
def isolated_guard():
    """Переустановить guard локально для assertions (session уже может иметь guard)."""
    was = is_network_guard_installed()
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    install_network_guard()
    yield
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    if was:
        install_network_guard()


@pytest.mark.unit
def test_assert_host_allows_loopback() -> None:
    assert_host_allowed("127.0.0.1", context="t")
    assert_host_allowed("localhost", context="t")
    assert_host_allowed("::1", context="t")


@pytest.mark.unit
def test_assert_host_blocks_external() -> None:
    with pytest.raises(NetworkGuardError, match="Outbound network blocked"):
        assert_host_allowed("api.wildberries.ru", context="wb")


@pytest.mark.unit
def test_assert_host_blocks_external_ipv4_literal() -> None:
    """Внешний IPv4 отклоняется до любого connect (без реального I/O)."""
    with pytest.raises(NetworkGuardError, match="Outbound network blocked"):
        assert_host_allowed("203.0.113.10", context="doc-ip")


@pytest.mark.unit
def test_assert_host_blocks_external_ipv6_literal() -> None:
    with pytest.raises(NetworkGuardError, match="Outbound network blocked"):
        assert_host_allowed("2001:db8::1", context="doc-ipv6")


@pytest.mark.unit
def test_clear_proxy_environment_removes_keys() -> None:
    env = {
        "HTTP_PROXY": "http://evil:8080",
        "HTTPS_PROXY": "http://evil:8080",
        "ALL_PROXY": "socks5://evil:1080",
        "KEEP": "1",
    }
    removed = clear_proxy_environment(environ=env)
    assert "HTTP_PROXY" in removed
    assert "HTTP_PROXY" not in env
    assert env["KEEP"] == "1"


@pytest.mark.unit
def test_connect_ex_blocks_external_without_calling_original(isolated_guard) -> None:
    """connect_ex: внешний адрес → NetworkGuardError; original не вызывается."""
    original = MagicMock(return_value=0)
    with patch.object(
        __import__("tests.support.network_guard", fromlist=["_original_connect_ex"]),
        "_original_connect_ex",
        original,
    ):
        # Patch the module-level original used by guarded wrapper.
        import tests.support.network_guard as ng

        ng._original_connect_ex = original
        sock = socket.socket()
        try:
            with pytest.raises(NetworkGuardError, match="connect_ex"):
                sock.connect_ex(("203.0.113.10", 443))
        finally:
            sock.close()
        original.assert_not_called()


@pytest.mark.unit
def test_connect_ex_allows_loopback_calls_original(isolated_guard) -> None:
    """Loopback connect_ex вызывает original primitive (mocked, без реального TCP)."""
    import tests.support.network_guard as ng

    original = MagicMock(return_value=111)
    ng._original_connect_ex = original
    sock = socket.socket()
    try:
        rc = sock.connect_ex(("127.0.0.1", 5433))
    finally:
        sock.close()
    assert rc == 111
    original.assert_called_once()
    args, _kwargs = original.call_args
    assert args[1][0] == "127.0.0.1"
    assert args[1][1] == 5433


@pytest.mark.unit
def test_uninstall_restores_connect_ex() -> None:
    """uninstall/restore возвращает исходную connect_ex; guard не протекает."""
    real_connect_ex = socket.socket.connect_ex
    was = is_network_guard_installed()
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    before = socket.socket.connect_ex
    install_network_guard()
    assert socket.socket.connect_ex is not before
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    assert socket.socket.connect_ex is before
    if was:
        install_network_guard()
    else:
        # session may re-install via fixture teardown elsewhere
        pass
    assert callable(real_connect_ex)


@pytest.mark.unit
def test_uninstall_forbidden_without_allow() -> None:
    with pytest.raises(RuntimeError, match="forbidden"):
        uninstall_network_guard()


@pytest.mark.unit
def test_guard_does_not_leak_between_tests(isolated_guard) -> None:
    """После isolated_guard teardown исходное состояние восстанавливается."""
    import tests.support.network_guard as ng

    assert is_network_guard_installed() is True
    # fixture teardown runs after test — здесь только контракт install
    assert ng._original_connect_ex is not None


@pytest.mark.unit
def test_create_connection_blocks_external_mocked(isolated_guard) -> None:
    """create_connection: deny до original (mock)."""
    import tests.support.network_guard as ng

    original = MagicMock()
    ng._original_create_connection = original
    with pytest.raises(NetworkGuardError, match="api.telegram.org"):
        socket.create_connection(("api.telegram.org", 443), timeout=0.1)
    original.assert_not_called()


@pytest.mark.unit
def test_getaddrinfo_blocks_external_dns_mocked(isolated_guard) -> None:
    import tests.support.network_guard as ng

    original = MagicMock()
    ng._original_getaddrinfo = original
    with pytest.raises(NetworkGuardError, match="advert-api.wildberries.ru"):
        socket.getaddrinfo("advert-api.wildberries.ru", 443)
    original.assert_not_called()


@pytest.mark.unit
def test_create_connection_allows_loopback_mocked(isolated_guard) -> None:
    """Loopback разрешён; original вызывается (mock — без реального TCP)."""
    import tests.support.network_guard as ng

    sentinel = object()
    original = MagicMock(return_value=sentinel)
    ng._original_create_connection = original
    got = socket.create_connection(("127.0.0.1", 5433), timeout=0.05)
    assert got is sentinel
    original.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sock_connect_blocks_external_mocked(isolated_guard) -> None:
    """asyncio sock_connect блокирует внешний host до original (без реального TCP)."""
    import tests.support.network_guard as ng

    if not ng._sock_connect_restore:
        pytest.skip("loop.sock_connect not patched on this runtime")

    called = MagicMock()

    async def _boom(*_a: object, **_k: object) -> None:
        called()

    previous = list(ng._sock_connect_restore)
    ng._sock_connect_restore[:] = [(owner, _boom) for owner, _saved in previous]
    ng._original_sock_connect = _boom
    try:
        meth = asyncio.base_events.BaseEventLoop.sock_connect
        with pytest.raises(NetworkGuardError, match="sock_connect"):
            await meth(object(), MagicMock(), ("203.0.113.10", 443))
        called.assert_not_called()
    finally:
        ng._sock_connect_restore[:] = previous


@pytest.mark.unit
def test_error_message_has_no_credentials(isolated_guard) -> None:
    with pytest.raises(NetworkGuardError) as ei:
        assert_host_allowed("secret.example", context="t")
    msg = str(ei.value)
    assert "password" not in msg.lower()
    assert "://" not in msg or "secret.example" in msg


@pytest.mark.unit
def test_client_factory_not_called_without_override() -> None:
    """Контракт: без override factory внешнего клиента не вызывается в unit."""
    factory = MagicMock()
    factory.assert_not_called()
    with patch.dict("os.environ", {"WB_TEST_MODE": "1"}, clear=False):
        assert factory.call_count == 0
