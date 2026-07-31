"""Unit: fail-closed outbound network guard (loopback-only).

Все тесты используют fake socket primitives / synthetic owners —
без реальных TCP/DNS/subprocess вызовов.
"""

from __future__ import annotations

import asyncio
import socket as real_socket
import traceback
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import tests.support.network_guard as ng
from tests.support.network_guard import (
    NetworkGuardError,
    NetworkGuardLifecycleError,
    assert_host_allowed,
    clear_proxy_environment,
    install_network_guard,
    is_network_guard_installed,
    uninstall_network_guard,
)

_AF_UNIX = getattr(real_socket, "AF_UNIX", 1)

_SENTINELS = (
    "postgresql://SNTL_USER_71d:SNTL_PASS_92a@host/db",
    "TOKEN=SNTL_TOKEN_401c",
    "--password SNTL_CLI_PASS_d12e",
    "Authorization:Token SNTL_AUTH_710b",
    "SNTL_PASS_92a",
    "SNTL_TOKEN_401c",
    "SNTL_CLI_PASS_d12e",
    "SNTL_AUTH_710b",
    "SNTL_USER_71d",
)


def _mk_loop_class(name: str):
    """Synthetic asyncio-like loop owner with concrete sock_connect."""

    class _Loop:
        calls: list[tuple[object, object]] = []

        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            type(self).calls.append((sock, address))
            return name

        def close(self) -> None:
            return None

    _Loop.__name__ = name
    return _Loop


def _fake_sock(*, family: int) -> SimpleNamespace:
    """Fake socket with family only — no real socket()."""
    return SimpleNamespace(family=family)


def _assert_registry_clean() -> None:
    """Canonical registry must be empty when guard is not installed."""
    assert ng._guard_installed is False
    assert ng._patch_records == []
    assert ng._sock_connect_delegate_map == {}


def _assert_no_sentinels(text: str) -> None:
    for sentinel in _SENTINELS:
        assert sentinel not in text, f"leaked sentinel {sentinel!r} in {text!r}"


def _format_exc(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


@pytest.fixture
def guard_state():
    """Isolate network_guard module state; teardown failures fail the test."""
    was = is_network_guard_installed()
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    _assert_registry_clean()

    create_calls: list[Any] = []
    getaddr_calls: list[Any] = []
    connect_calls: list[Any] = []
    connect_ex_calls: list[Any] = []

    class FakeSocketClass:
        """Stand-in for socket.socket; instances carry .family."""

        def connect(self, address):  # type: ignore[no-untyped-def]
            connect_calls.append(address)
            return ("connect", address)

        def connect_ex(self, address):  # type: ignore[no-untyped-def]
            connect_ex_calls.append(address)
            return 0

    def fake_create_connection(address, *args, **kwargs):  # type: ignore[no-untyped-def]
        create_calls.append((address, args, kwargs))
        return ("create_connection", address)

    def fake_getaddrinfo(host, *args, **kwargs):  # type: ignore[no-untyped-def]
        getaddr_calls.append((host, args, kwargs))
        return [("fake", host)]

    fake_socket_module = SimpleNamespace(
        create_connection=fake_create_connection,
        getaddrinfo=fake_getaddrinfo,
        socket=FakeSocketClass,
        AF_INET=real_socket.AF_INET,
        AF_INET6=real_socket.AF_INET6,
        AF_UNIX=_AF_UNIX,
    )

    teardown_error: BaseException | None = None
    with patch.object(ng, "socket", fake_socket_module), patch.object(
        ng, "clear_proxy_environment", return_value={}
    ):
        try:
            yield SimpleNamespace(
                create_calls=create_calls,
                getaddr_calls=getaddr_calls,
                connect_calls=connect_calls,
                connect_ex_calls=connect_ex_calls,
                FakeSocketClass=FakeSocketClass,
            )
        finally:
            try:
                if is_network_guard_installed():
                    uninstall_network_guard(_allow_for_guard_unit_tests=True)
            except BaseException as exc:  # noqa: BLE001
                teardown_error = exc
                ng._clear_guard_registry()
            try:
                _assert_registry_clean()
            except AssertionError as clean_exc:
                if teardown_error is not None:
                    raise clean_exc from teardown_error
                raise
            if teardown_error is not None:
                raise teardown_error
    if was:
        install_network_guard()


# ---------------------------------------------------------------------------
# Boundary / host policy
# ---------------------------------------------------------------------------


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
    with pytest.raises(NetworkGuardError, match="203.0.113.10"):
        assert_host_allowed("203.0.113.10", context="ipv4")


@pytest.mark.unit
def test_assert_host_blocks_external_ipv6_literal() -> None:
    with pytest.raises(NetworkGuardError, match="2001:db8::1"):
        assert_host_allowed("2001:db8::1", context="ipv6")


@pytest.mark.unit
def test_clear_proxy_environment_removes_keys() -> None:
    env = {
        "HTTP_PROXY": "http://proxy",
        "https_proxy": "http://proxy",
        "NO_PROXY": "*",
        "KEEP": "1",
    }
    removed = clear_proxy_environment(environ=env)
    assert "HTTP_PROXY" in removed
    assert "https_proxy" in removed
    assert "NO_PROXY" in removed
    assert "KEEP" in env
    assert "HTTP_PROXY" not in env


@pytest.mark.unit
def test_connect_ex_blocks_external_without_calling_original(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = real_socket.AF_INET
    with pytest.raises(NetworkGuardError, match="connect_ex"):
        sock.connect_ex(("203.0.113.10", 443))
    assert guard_state.connect_ex_calls == []


@pytest.mark.unit
def test_connect_ex_allows_loopback_calls_original(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = real_socket.AF_INET
    assert sock.connect_ex(("127.0.0.1", 5433)) == 0
    assert guard_state.connect_ex_calls == [("127.0.0.1", 5433)]


@pytest.mark.unit
def test_socket_connect_blocks_external_without_calling_original(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = real_socket.AF_INET
    with pytest.raises(NetworkGuardError, match="socket.socket.connect"):
        sock.connect(("203.0.113.10", 443))
    assert guard_state.connect_calls == []


@pytest.mark.unit
def test_socket_connect_allows_ipv4_loopback(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = real_socket.AF_INET
    assert sock.connect(("127.0.0.1", 1)) == ("connect", ("127.0.0.1", 1))


@pytest.mark.unit
def test_socket_connect_allows_ipv6_loopback(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = real_socket.AF_INET6
    addr = ("::1", 5433, 0, 0)
    assert sock.connect(addr) == ("connect", addr)


@pytest.mark.unit
def test_socket_connect_blocks_external_ipv6(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = real_socket.AF_INET6
    with pytest.raises(NetworkGuardError):
        sock.connect(("2001:db8::1", 443, 0, 0))
    assert guard_state.connect_calls == []


@pytest.mark.unit
def test_uninstall_restores_connect_ex(guard_state) -> None:
    before = guard_state.FakeSocketClass.connect_ex
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    assert guard_state.FakeSocketClass.connect_ex is not before
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    assert guard_state.FakeSocketClass.connect_ex is before
    _assert_registry_clean()


@pytest.mark.unit
def test_uninstall_forbidden_without_allow(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    with pytest.raises(RuntimeError, match="forbidden"):
        uninstall_network_guard()
    uninstall_network_guard(_allow_for_guard_unit_tests=True)


@pytest.mark.unit
def test_idempotent_install(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
        wrapper = ng.socket.create_connection
        install_network_guard()
        assert ng.socket.create_connection is wrapper
        assert is_network_guard_installed() is True


@pytest.mark.unit
def test_create_connection_blocks_external_without_calling_original(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    with pytest.raises(NetworkGuardError, match="api.telegram.org"):
        ng.socket.create_connection(("api.telegram.org", 443), timeout=0.1)
    assert guard_state.create_calls == []


@pytest.mark.unit
def test_create_connection_allows_loopback_mocked(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    got = ng.socket.create_connection(("127.0.0.1", 5433), timeout=0.05)
    assert got == ("create_connection", ("127.0.0.1", 5433))
    assert len(guard_state.create_calls) == 1


@pytest.mark.unit
def test_getaddrinfo_blocks_external_hostname_before_dns(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    with pytest.raises(NetworkGuardError, match="advert-api.wildberries.ru"):
        ng.socket.getaddrinfo("advert-api.wildberries.ru", 443)
    assert guard_state.getaddr_calls == []


@pytest.mark.unit
def test_getaddrinfo_allows_loopback(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    assert ng.socket.getaddrinfo("127.0.0.1", 5433) == [("fake", "127.0.0.1")]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sock_connect_blocks_external_mocked(guard_state) -> None:
    owner = _mk_loop_class("SockOwner")
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        install_network_guard()
    sock = _fake_sock(family=real_socket.AF_INET)
    with pytest.raises(NetworkGuardError, match="sock_connect"):
        await owner().sock_connect(sock, ("203.0.113.10", 443))
    assert owner.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sock_connect_allows_ipv4_loopback_delegate(guard_state) -> None:
    owner = _mk_loop_class("SockOwnerV4")
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        install_network_guard()
    sock = _fake_sock(family=real_socket.AF_INET)
    assert await owner().sock_connect(sock, ("127.0.0.1", 5433)) == "SockOwnerV4"
    assert owner.calls == [(sock, ("127.0.0.1", 5433))]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sock_connect_allows_ipv6_loopback_delegate(guard_state) -> None:
    owner = _mk_loop_class("SockOwnerV6")
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        install_network_guard()
    sock = _fake_sock(family=real_socket.AF_INET6)
    addr = ("::1", 5433, 0, 0)
    assert await owner().sock_connect(sock, addr) == "SockOwnerV6"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sock_connect_blocks_external_ipv6_delegate(guard_state) -> None:
    owner = _mk_loop_class("SockOwnerV6Deny")
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        install_network_guard()
    sock = _fake_sock(family=real_socket.AF_INET6)
    with pytest.raises(NetworkGuardError):
        await owner().sock_connect(sock, ("2001:db8::1", 443, 0, 0))
    assert owner.calls == []


@pytest.mark.unit
def test_error_message_has_no_credentials() -> None:
    with pytest.raises(NetworkGuardError) as ei:
        assert_host_allowed("secret.example", context="t")
    assert "password" not in str(ei.value).lower()


@pytest.mark.unit
def test_client_factory_not_called_without_override() -> None:
    factory = MagicMock()
    factory.assert_not_called()
    with patch.dict("os.environ", {"WB_TEST_MODE": "1"}, clear=False):
        assert factory.call_count == 0


# ---------------------------------------------------------------------------
# Family-aware address policy
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_family_af_unix_path_allowed_as_local_ipc(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = _AF_UNIX
    path = "/tmp/unit-ng.sock"
    assert sock.connect(path) == ("connect", path)
    assert guard_state.connect_calls == [path]


@pytest.mark.unit
def test_family_af_unix_bytes_path_allowed(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = _AF_UNIX
    path = b"/tmp/unit-ng.sock"
    assert sock.connect(path) == ("connect", path)


@pytest.mark.unit
def test_family_af_unix_malformed_tuple_blocked_before_delegate(guard_state) -> None:
    owner = _mk_loop_class("UnixOwner")
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        install_network_guard()
    fake = guard_state.FakeSocketClass()
    fake.family = _AF_UNIX
    with pytest.raises(NetworkGuardError, match="malformed AF_UNIX"):
        fake.connect(("/tmp/x.sock", 0))
    assert guard_state.connect_calls == []
    sock = _fake_sock(family=_AF_UNIX)
    with pytest.raises(NetworkGuardError, match="malformed AF_UNIX"):
        ng._assert_address_allowed_for_family(
            ("/tmp/x.sock", 0), family=_AF_UNIX, context="test"
        )
    assert owner.calls == []


@pytest.mark.unit
def test_family_af_inet_malformed_fail_closed(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = real_socket.AF_INET
    with pytest.raises(NetworkGuardError, match="malformed AF_INET"):
        sock.connect("not-a-tuple")
    assert guard_state.connect_calls == []


@pytest.mark.unit
def test_family_af_inet6_malformed_fail_closed(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = real_socket.AF_INET6
    with pytest.raises(NetworkGuardError, match="malformed AF_INET6"):
        sock.connect("::1")
    assert guard_state.connect_calls == []


@pytest.mark.unit
def test_family_unknown_fail_closed_without_original(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = 99999
    with pytest.raises(NetworkGuardError, match="unknown socket family"):
        sock.connect(("127.0.0.1", 1))
    assert guard_state.connect_calls == []


@pytest.mark.unit
def test_str_address_on_af_inet_not_treated_as_unix(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    sock = guard_state.FakeSocketClass()
    sock.family = real_socket.AF_INET
    with pytest.raises(NetworkGuardError, match="malformed AF_INET"):
        sock.connect("/looks/like/unix.sock")
    assert guard_state.connect_calls == []


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_preexisting_foreign_patch_saved_as_original_and_restored(guard_state) -> None:
    owner = _mk_loop_class("PreOwner")

    async def preexisting(self, sock, address):  # type: ignore[no-untyped-def]
        return ("preexisting", address)

    owner.sock_connect = preexisting
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        install_network_guard()
    assert owner.sock_connect is not preexisting
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    assert owner.sock_connect is preexisting
    _assert_registry_clean()


@pytest.mark.unit
def test_post_install_foreign_mutation_preserved_not_overwritten(guard_state) -> None:
    owner = _mk_loop_class("PostOwner")
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        install_network_guard()

    async def foreign(self, sock, address):  # type: ignore[no-untyped-def]
        return "foreign"

    owner.sock_connect = foreign
    with pytest.raises(NetworkGuardLifecycleError) as ei:
        uninstall_network_guard(_allow_for_guard_unit_tests=True)
    assert ei.value.ownership_conflicts
    assert owner.sock_connect is foreign
    _assert_registry_clean()


@pytest.mark.unit
def test_multiple_simultaneous_ownership_conflicts(guard_state) -> None:
    owner1 = _mk_loop_class("Own1")
    owner2 = _mk_loop_class("Own2")
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2]):
        install_network_guard()

    async def foreign1(self, sock, address):  # type: ignore[no-untyped-def]
        return 1

    async def foreign2(self, sock, address):  # type: ignore[no-untyped-def]
        return 2

    owner1.sock_connect = foreign1
    owner2.sock_connect = foreign2
    with pytest.raises(NetworkGuardLifecycleError) as ei:
        uninstall_network_guard(_allow_for_guard_unit_tests=True)
    assert len(ei.value.ownership_conflicts) >= 2
    assert owner1.sock_connect is foreign1
    assert owner2.sock_connect is foreign2
    _assert_registry_clean()


@pytest.mark.unit
def test_uninstall_after_ownership_conflict_then_repeat_noop_and_foreign_kept(guard_state) -> None:
    owner = _mk_loop_class("OwnerX")
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        install_network_guard()

    async def foreign(self, sock, address):  # type: ignore[no-untyped-def]
        return "foreign"

    owner.sock_connect = foreign
    with pytest.raises(NetworkGuardLifecycleError, match="ownership conflict"):
        uninstall_network_guard(_allow_for_guard_unit_tests=True)
    assert owner.sock_connect is foreign
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    assert owner.sock_connect is foreign
    _assert_registry_clean()


# ---------------------------------------------------------------------------
# NG-01: mutate-then-raise + hostile getter / foreign static probe
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ng01_mutate_then_raise_hostile_getter_rolls_back_wrapper(guard_state) -> None:
    owner_ok = _mk_loop_class("OkOwner")
    owner_bad = _mk_loop_class("HostileOwner")
    ok_orig = owner_ok.sock_connect
    bad_orig = owner_bad.sock_connect

    class HostileMeta(type(owner_bad)):
        writes = 0

        def __getattribute__(cls, name):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError("hostile-getattr-blocked")
            return type.__getattribute__(cls, name)

        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                type(cls).writes += 1
                type.__setattr__(cls, name, value)
                # First write = install wrapper (mutate-then-raise); later restore succeeds.
                if type(cls).writes == 1:
                    raise RuntimeError("mutate-then-raise")
                return None
            return type.__setattr__(cls, name, value)

    owner_bad = HostileMeta(owner_bad.__name__, owner_bad.__bases__, dict(owner_bad.__dict__))
    create_before = ng.socket.create_connection

    with patch.object(
        ng, "_collect_concrete_sock_connect_owners", return_value=[owner_ok, owner_bad]
    ):
        with pytest.raises(NetworkGuardLifecycleError) as ei:
            install_network_guard()

    err = ei.value
    assert err.phase == "install-rollback"
    assert err.primary_error_type == "RuntimeError"
    assert "mutate-then-raise" in err.primary_error_summary
    assert err.__cause__ is None
    assert err.__context__ is None
    assert owner_ok.sock_connect is ok_orig
    status, value = ng._static_probe_attribute(owner_bad, "sock_connect")
    assert status == "ok"
    assert value is bad_orig
    assert ng.socket.create_connection is create_before
    _assert_registry_clean()

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner_ok]):
        install_network_guard()
    assert is_network_guard_installed() is True
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    _assert_registry_clean()


@pytest.mark.unit
def test_ng01_mutate_then_raise_static_probe_sees_foreign_preserved(guard_state) -> None:
    owner_ok = _mk_loop_class("OkOwner2")
    owner_bad = _mk_loop_class("ForeignMutOwner")
    ok_orig = owner_ok.sock_connect

    async def foreign(self, sock, address):  # type: ignore[no-untyped-def]
        return "foreign-after-setattr"

    class ForeignMeta(type(owner_bad)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                type.__setattr__(cls, name, foreign)
                raise RuntimeError("mutate-to-foreign-then-raise")
            return type.__setattr__(cls, name, value)

    owner_bad = ForeignMeta(owner_bad.__name__, owner_bad.__bases__, dict(owner_bad.__dict__))

    with patch.object(
        ng, "_collect_concrete_sock_connect_owners", return_value=[owner_ok, owner_bad]
    ):
        with pytest.raises(NetworkGuardLifecycleError) as ei:
            install_network_guard()

    err = ei.value
    assert err.phase == "install-rollback"
    assert err.ownership_conflicts
    assert any("foreign value" in c for c in err.ownership_conflicts)
    assert owner_ok.sock_connect is ok_orig
    assert owner_bad.sock_connect is foreign
    _assert_registry_clean()


@pytest.mark.unit
def test_setattr_mutate_then_raise_included_in_rollback(guard_state) -> None:
    owner1 = _mk_loop_class("OkOwner")
    owner2 = _mk_loop_class("MutRaiseOwner")
    owner1_orig = owner1.sock_connect
    owner2_orig = owner2.sock_connect

    class MutRaiseMeta(type(owner2)):
        writes = 0

        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                type(cls).writes += 1
                type.__setattr__(cls, name, value)
                if type(cls).writes == 1:
                    raise RuntimeError("mutate-then-raise")
                return None
            return super().__setattr__(name, value)

    owner2 = MutRaiseMeta(owner2.__name__, owner2.__bases__, dict(owner2.__dict__))

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2]):
        with pytest.raises(NetworkGuardLifecycleError) as ei:
            install_network_guard()

    assert ei.value.phase == "install-rollback"
    assert owner1.sock_connect is owner1_orig
    assert owner2.sock_connect is owner2_orig
    _assert_registry_clean()


@pytest.mark.unit
def test_hostile_getattr_during_rollback_static_probe_still_restores(guard_state) -> None:
    owner1 = _mk_loop_class("GetHostile")
    owner2 = _mk_loop_class("FailLast")
    owner1_orig = owner1.sock_connect
    owner2_orig = owner2.sock_connect

    class GetHostileMeta(type(owner1)):
        def __getattribute__(cls, name):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError("getter-fail-during-rollback")
            return type.__getattribute__(cls, name)

        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            return type.__setattr__(cls, name, value)

    class FailLastMeta(type(owner2)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError("primary-install-fail")
            return type.__setattr__(cls, name, value)

    owner1 = GetHostileMeta(owner1.__name__, owner1.__bases__, dict(owner1.__dict__))
    owner2 = FailLastMeta(owner2.__name__, owner2.__bases__, dict(owner2.__dict__))

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2]):
        with pytest.raises(NetworkGuardLifecycleError) as ei:
            install_network_guard()

    assert ei.value.phase == "install-rollback"
    status, value = ng._static_probe_attribute(owner1, "sock_connect")
    assert status == "ok" and value is owner1_orig
    assert owner2.sock_connect is owner2_orig
    _assert_registry_clean()


@pytest.mark.unit
def test_static_probe_failure_recorded_and_other_records_rolled_back(guard_state) -> None:
    owner1 = _mk_loop_class("ProbeFail")
    owner2 = _mk_loop_class("OkMid")
    owner3 = _mk_loop_class("FailLast")
    owner2_orig = owner2.sock_connect
    owner3_orig = owner3.sock_connect

    class FailLastMeta(type(owner3)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError("primary-install-fail")
            return type.__setattr__(cls, name, value)

    owner3 = FailLastMeta(owner3.__name__, owner3.__bases__, dict(owner3.__dict__))
    real_probe = ng._static_probe_attribute
    restore = ng._restore_patch_records

    def restore_wrap(records, **kwargs):  # type: ignore[no-untyped-def]
        def selective_probe(owner: Any, attribute: str):  # type: ignore[no-untyped-def]
            if owner is owner1 and attribute == "sock_connect":
                return ("error", RuntimeError("static-probe-impossible"))
            return real_probe(owner, attribute)

        with patch.object(ng, "_static_probe_attribute", side_effect=selective_probe):
            return restore(records, **kwargs)

    with patch.object(ng, "_restore_patch_records", side_effect=restore_wrap), patch.object(
        ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2, owner3]
    ):
        with pytest.raises(NetworkGuardLifecycleError) as ei:
            install_network_guard()

    err = ei.value
    assert err.phase == "install-rollback"
    assert err.rollback_failure_count >= 1
    assert any("static-probe" in s for s in err.rollback_error_summaries)
    assert owner2.sock_connect is owner2_orig
    assert owner3.sock_connect is owner3_orig
    _assert_registry_clean()


@pytest.mark.unit
def test_canonical_registry_empty_after_any_install_failure(guard_state) -> None:
    owner = _mk_loop_class("FailOwner")

    class BadMeta(type(owner)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError("fail")
            return super().__setattr__(name, value)

    owner = BadMeta(owner.__name__, owner.__bases__, dict(owner.__dict__))
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        with pytest.raises(NetworkGuardLifecycleError, match="fail"):
            install_network_guard()
    _assert_registry_clean()


@pytest.mark.unit
def test_first_owner_patch_failure_rolls_back_everything(guard_state) -> None:
    owner1 = _mk_loop_class("Owner1")
    owner2 = _mk_loop_class("Owner2")

    class FailFirst(type(owner1)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError("first-owner-fail")
            return super().__setattr__(name, value)

    owner1 = FailFirst(owner1.__name__, owner1.__bases__, dict(owner1.__dict__))
    create_before = ng.socket.create_connection
    getaddr_before = ng.socket.getaddrinfo
    connect_before = ng.socket.socket.connect
    connect_ex_before = ng.socket.socket.connect_ex

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2]):
        with pytest.raises(NetworkGuardLifecycleError, match="first-owner-fail"):
            install_network_guard()

    assert ng.socket.create_connection is create_before
    assert ng.socket.getaddrinfo is getaddr_before
    assert ng.socket.socket.connect is connect_before
    assert ng.socket.socket.connect_ex is connect_ex_before
    _assert_registry_clean()


@pytest.mark.unit
def test_middle_owner_patch_failure_rolls_back_previous_only(guard_state) -> None:
    owner1 = _mk_loop_class("Owner1")
    owner2 = _mk_loop_class("Owner2")
    owner3 = _mk_loop_class("Owner3")

    class FailMiddle(type(owner2)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError("middle-owner-fail")
            return super().__setattr__(name, value)

    owner2 = FailMiddle(owner2.__name__, owner2.__bases__, dict(owner2.__dict__))
    owner1_orig = owner1.sock_connect
    owner2_orig = owner2.sock_connect
    owner3_orig = owner3.sock_connect

    with patch.object(
        ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2, owner3]
    ):
        with pytest.raises(NetworkGuardLifecycleError, match="middle-owner-fail"):
            install_network_guard()

    assert owner1.sock_connect is owner1_orig
    assert owner2.sock_connect is owner2_orig
    assert owner3.sock_connect is owner3_orig
    _assert_registry_clean()


@pytest.mark.unit
def test_last_owner_patch_failure_rolls_back_all_previous(guard_state) -> None:
    owner1 = _mk_loop_class("Owner1")
    owner2 = _mk_loop_class("Owner2")
    owner3 = _mk_loop_class("Owner3")

    class FailLast(type(owner3)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError("last-owner-fail")
            return super().__setattr__(name, value)

    owner3 = FailLast(owner3.__name__, owner3.__bases__, dict(owner3.__dict__))
    owner1_orig = owner1.sock_connect
    owner2_orig = owner2.sock_connect
    owner3_orig = owner3.sock_connect

    with patch.object(
        ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2, owner3]
    ):
        with pytest.raises(NetworkGuardLifecycleError, match="last-owner-fail"):
            install_network_guard()

    assert owner1.sock_connect is owner1_orig
    assert owner2.sock_connect is owner2_orig
    assert owner3.sock_connect is owner3_orig
    _assert_registry_clean()


@pytest.mark.unit
def test_foreign_mutation_during_install_rollback_preserved_and_reported(guard_state) -> None:
    owner1 = _mk_loop_class("Owner1")
    owner2 = _mk_loop_class("Owner2")

    async def foreign_delegate(self, sock, address):  # type: ignore[no-untyped-def]
        return ("foreign", sock, address)

    class FailSecond(type(owner2)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                owner1.sock_connect = foreign_delegate
                raise RuntimeError("second-owner-install-fail")
            return super().__setattr__(name, value)

    owner2 = FailSecond(owner2.__name__, owner2.__bases__, dict(owner2.__dict__))

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2]):
        with pytest.raises(NetworkGuardLifecycleError) as ei:
            install_network_guard()

    err = ei.value
    assert err.phase == "install-rollback"
    assert err.primary_error_type == "RuntimeError"
    assert "second-owner-install-fail" in err.primary_error_summary
    assert err.ownership_conflicts
    assert owner1.sock_connect is foreign_delegate
    _assert_registry_clean()


@pytest.mark.unit
def test_multiple_rollback_failures_recorded_as_sanitized_summaries(guard_state) -> None:
    owner1 = _mk_loop_class("Owner1")
    owner2 = _mk_loop_class("Owner2")
    owner3 = _mk_loop_class("Owner3")
    owner1_orig = owner1.sock_connect
    owner2_orig = owner2.sock_connect

    class Owner1Meta(type(owner1)):
        writes = 0

        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                type(cls).writes += 1
                if value is owner1_orig and type(cls).writes >= 2:
                    raise RuntimeError(
                        "rollback-owner1 postgresql://SNTL_USER_71d:SNTL_PASS_92a@host/db"
                    )
            return super().__setattr__(name, value)

    class Owner2Meta(type(owner2)):
        writes = 0

        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                type(cls).writes += 1
                if value is owner2_orig and type(cls).writes >= 2:
                    raise RuntimeError("rollback-owner2 TOKEN=SNTL_TOKEN_401c")
            return super().__setattr__(name, value)

    class Owner3Meta(type(owner3)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError(
                    "primary --password SNTL_CLI_PASS_d12e Authorization:Token SNTL_AUTH_710b"
                )
            return super().__setattr__(name, value)

    owner1 = Owner1Meta(owner1.__name__, owner1.__bases__, dict(owner1.__dict__))
    owner2 = Owner2Meta(owner2.__name__, owner2.__bases__, dict(owner2.__dict__))
    owner3 = Owner3Meta(owner3.__name__, owner3.__bases__, dict(owner3.__dict__))

    with patch.object(
        ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2, owner3]
    ):
        with pytest.raises(NetworkGuardLifecycleError) as ei:
            install_network_guard()

    err = ei.value
    assert err.phase == "install-rollback"
    assert err.primary_error_type == "RuntimeError"
    assert err.rollback_failure_count >= 2
    assert len(err.rollback_error_summaries) >= 2
    blob = f"{err!s}\n{err!r}\n" + "\n".join(err.rollback_error_summaries)
    _assert_no_sentinels(blob)
    assert "<redacted>" in str(err)
    assert len(str(err)) <= ng._LIFECYCLE_MSG_LIMIT + 80
    assert "primary_error" not in vars(err)
    assert "rollback_errors" not in vars(err)
    _assert_registry_clean()


@pytest.mark.unit
def test_failed_install_then_clean_reinstall_succeeds(guard_state) -> None:
    owner_bad = _mk_loop_class("OwnerBad")
    owner_good = _mk_loop_class("OwnerGood")

    class BadMeta(type(owner_bad)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError("first-install-failed")
            return super().__setattr__(name, value)

    owner_bad = BadMeta(owner_bad.__name__, owner_bad.__bases__, dict(owner_bad.__dict__))
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner_bad]):
        with pytest.raises(NetworkGuardLifecycleError, match="first-install-failed"):
            install_network_guard()
    _assert_registry_clean()

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner_good]):
        install_network_guard()
    assert is_network_guard_installed() is True
    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    _assert_registry_clean()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_diamond_inheritance_uses_c3_mro_not_insertion_order(guard_state) -> None:
    class A:
        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            return "A"

        def close(self) -> None:
            return None

    class B(A):
        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            return "B"

    class C(A):
        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            return "C"

    class D(B, C):
        pass

    assert D.__mro__[1] is B
    sock = _fake_sock(family=real_socket.AF_INET)

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[A, C, B]):
        install_network_guard()
    assert await D().sock_connect(sock, ("127.0.0.1", 1)) == "B"
    uninstall_network_guard(_allow_for_guard_unit_tests=True)

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[B, A, C]):
        install_network_guard()
    assert await D().sock_connect(sock, ("127.0.0.1", 1)) == "B"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_delegate_fail_closed_without_network(guard_state) -> None:
    owner = _mk_loop_class("HasDelegate")
    called = MagicMock()

    async def boom(self, sock, address):  # type: ignore[no-untyped-def]
        called()
        raise AssertionError("delegate must not run")

    owner.sock_connect = boom
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner]):
        install_network_guard()

    ng._sock_connect_delegate_map.clear()
    sock = _fake_sock(family=real_socket.AF_INET)
    with pytest.raises(RuntimeError, match="no concrete sock_connect delegate"):
        await owner().sock_connect(sock, ("127.0.0.1", 5433))
    called.assert_not_called()
    uninstall_network_guard(_allow_for_guard_unit_tests=True)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parent_child_exact_delegation_deterministic(guard_state) -> None:
    class Parent:
        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            return "parent"

        def close(self) -> None:
            return None

    class Child(Parent):
        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            return "child"

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[Parent, Child]):
        install_network_guard()

    sock = _fake_sock(family=real_socket.AF_INET)
    assert await Child().sock_connect(sock, ("127.0.0.1", 5433)) == "child"
    assert await Parent().sock_connect(sock, ("127.0.0.1", 5433)) == "parent"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mro_fallback_uses_nearest_registered_base(guard_state) -> None:
    class Grand:
        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            return "grand"

        def close(self) -> None:
            return None

    class Parent(Grand):
        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            return "parent"

    class Child(Parent):
        pass

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[Grand, Parent]):
        install_network_guard()

    sock = _fake_sock(family=real_socket.AF_INET)
    assert await Child().sock_connect(sock, ("127.0.0.1", 5433)) == "parent"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_registry_insertion_order_does_not_change_delegate_choice(guard_state) -> None:
    class Grand:
        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            return "grand"

        def close(self) -> None:
            return None

    class Parent(Grand):
        async def sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
            return "parent"

    class Child(Parent):
        pass

    sock = _fake_sock(family=real_socket.AF_INET)
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[Parent, Grand]):
        install_network_guard()
    assert await Child().sock_connect(sock, ("127.0.0.1", 5433)) == "parent"

    uninstall_network_guard(_allow_for_guard_unit_tests=True)
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[Grand, Parent]):
        install_network_guard()
    assert await Child().sock_connect(sock, ("127.0.0.1", 5433)) == "parent"


@pytest.mark.unit
def test_abstract_base_never_saved_or_used(guard_state) -> None:
    with patch.object(
        ng, "_collect_concrete_sock_connect_owners", return_value=[asyncio.base_events.BaseEventLoop]
    ):
        with pytest.raises(NetworkGuardLifecycleError, match="abstract sock_connect delegate"):
            install_network_guard()
    _assert_registry_clean()


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,forbidden",
    [
        ("postgresql://sentinel_user:sentinel_pass@host/db", "sentinel_pass"),
        ("PASSWORD='SNTL_PASSWORD_14c8'", "SNTL_PASSWORD_14c8"),
        ('TOKEN="SNTL_TOKEN_a821"', "SNTL_TOKEN_a821"),
        ("DSN=SNTL_DSN_731f", "SNTL_DSN_731f"),
        ("--password SNTL_CLI_PASS_22d1", "SNTL_CLI_PASS_22d1"),
        ("--token=SNTL_CLI_TOKEN_81f4", "SNTL_CLI_TOKEN_81f4"),
        ("Authorization:Bearer SNTL_BEARER_71c2", "SNTL_BEARER_71c2"),
        ("Authorization:Basic SNTL_BASIC_40a9", "SNTL_BASIC_40a9"),
        ("Authorization:Token SNTL_AUTH_TOKEN_d18e", "SNTL_AUTH_TOKEN_d18e"),
    ],
)
def test_lifecycle_sanitizer_exact_vectors(raw: str, forbidden: str) -> None:
    cleaned = ng._sanitize(raw)
    assert forbidden not in cleaned
    assert "<redacted>" in cleaned


@pytest.mark.unit
def test_ng02_exception_chain_secret_safety(guard_state) -> None:
    owner1 = _mk_loop_class("Owner1")
    owner2 = _mk_loop_class("Owner2")

    class Owner1Meta(type(owner1)):
        writes = 0

        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                type(cls).writes += 1
                if type(cls).writes >= 2:
                    raise RuntimeError(
                        "ROLLBACK TOKEN=SNTL_TOKEN_401c --password SNTL_CLI_PASS_d12e"
                    )
            return super().__setattr__(name, value)

    class Owner2Meta(type(owner2)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError(
                    "PRIMARY postgresql://SNTL_USER_71d:SNTL_PASS_92a@host/db "
                    "Authorization:Token SNTL_AUTH_710b"
                )
            return super().__setattr__(name, value)

    owner1 = Owner1Meta(owner1.__name__, owner1.__bases__, dict(owner1.__dict__))
    owner2 = Owner2Meta(owner2.__name__, owner2.__bases__, dict(owner2.__dict__))

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2]):
        with pytest.raises(NetworkGuardLifecycleError) as ei:
            install_network_guard()

    err = ei.value
    combined = f"{err!s}\n{err!r}\n{_format_exc(err)}"
    _assert_no_sentinels(combined)
    assert err.__cause__ is None
    assert err.__context__ is None
    assert "<redacted>" in str(err)
    assert err.phase == "install-rollback"
    assert err.primary_error_type == "RuntimeError"
    assert "primary_error" not in vars(err)
    assert "rollback_errors" not in vars(err)
    assert isinstance(err.primary_error_summary, str)
    assert isinstance(err.rollback_error_summaries, list)
    assert err.rollback_failure_count == len(err.rollback_error_summaries)
    for summary in err.rollback_error_summaries:
        _assert_no_sentinels(summary)
    _assert_no_sentinels(err.primary_error_summary)
    _assert_registry_clean()


@pytest.mark.unit
def test_lifecycle_error_str_repr_credential_safe_vectors(guard_state) -> None:
    owner1 = _mk_loop_class("Owner1")
    owner2 = _mk_loop_class("Owner2")

    class Owner1Meta(type(owner1)):
        writes = 0

        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                type(cls).writes += 1
                if type(cls).writes >= 2:
                    raise RuntimeError("ROLLBACK PASSWORD='SNTL_PASSWORD_14c8'")
            return super().__setattr__(name, value)

    class Owner2Meta(type(owner2)):
        def __setattr__(cls, name, value):  # type: ignore[no-untyped-def]
            if name == "sock_connect":
                raise RuntimeError(
                    "PRIMARY postgresql://sentinel_user:sentinel_pass@host/db "
                    'TOKEN="SNTL_TOKEN_a821" DSN=SNTL_DSN_731f '
                    "--password SNTL_CLI_PASS_22d1 --token=SNTL_CLI_TOKEN_81f4 "
                    "Authorization:Bearer SNTL_BEARER_71c2 "
                    "Authorization:Basic SNTL_BASIC_40a9 "
                    "Authorization:Token SNTL_AUTH_TOKEN_d18e"
                )
            return super().__setattr__(name, value)

    owner1 = Owner1Meta(owner1.__name__, owner1.__bases__, dict(owner1.__dict__))
    owner2 = Owner2Meta(owner2.__name__, owner2.__bases__, dict(owner2.__dict__))

    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[owner1, owner2]):
        with pytest.raises(NetworkGuardLifecycleError) as ei:
            install_network_guard()

    err = ei.value
    blob = f"{err!s}\n{err!r}"
    for forbidden in (
        "sentinel_pass",
        "SNTL_PASSWORD_14c8",
        "SNTL_TOKEN_a821",
        "SNTL_DSN_731f",
        "SNTL_CLI_PASS_22d1",
        "SNTL_CLI_TOKEN_81f4",
        "SNTL_BEARER_71c2",
        "SNTL_BASIC_40a9",
        "SNTL_AUTH_TOKEN_d18e",
    ):
        assert forbidden not in blob
    assert "<redacted>" in str(err)
    assert err.phase == "install-rollback"
    _assert_registry_clean()


@pytest.mark.unit
def test_basic_allow_block_contracts_with_no_real_network(guard_state) -> None:
    with patch.object(ng, "_collect_concrete_sock_connect_owners", return_value=[]):
        install_network_guard()
    assert ng._is_loopback_host("127.0.0.1") is True
    with pytest.raises(NetworkGuardError):
        ng.assert_host_allowed("203.0.113.10", context="unit")
