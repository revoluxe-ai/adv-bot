"""Fail-closed outbound network guard for pytest session.

Blocks non-loopback outbound socket/DNS paths and patches asyncio loop
``sock_connect`` delegates in a transactional, ownership-safe way.

Canonical runtime state (authoritative):

* ``_patch_records``
* ``_sock_connect_delegate_map``
* ``_guard_installed``

Restore and sock_connect delegation depend only on these structures.
There are no authoritative ``_original_*`` / ``_guarded_*`` module mirrors.

Address policy by ``sock.family``:

* ``AF_INET`` — ``(host, port)``; loopback allow, external deny, malformed fail-closed
* ``AF_INET6`` — IPv6 tuple; ``::1`` allow, external deny, malformed fail-closed
* ``AF_UNIX`` — ``str``/``bytes`` local IPC path; allowed without hostname interpretation
* unknown family — fail-closed without original call
"""

from __future__ import annotations

import asyncio
import inspect
import ipaddress
import os
import re
import socket
import traceback
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, Literal

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
_LIFECYCLE_MSG_LIMIT = 700

_guard_installed: bool = False
_sock_connect_delegate_map: dict[type[Any], Any] = {}

PatchStatus = Literal["attempted", "applied"]


@dataclass(frozen=True)
class _PatchRecord:
    """One patch target; created before setattr with status ``attempted``."""

    owner: Any
    attribute: str
    original: Any
    installed_wrapper: Any
    status: PatchStatus = "attempted"


_patch_records: list[_PatchRecord] = []


class NetworkGuardError(RuntimeError):
    """Outbound connection blocked by test network guard."""


class NetworkGuardLifecycleError(RuntimeError):
    """Credential-safe structured network-guard lifecycle failure.

    Public attributes never hold raw exception objects. Cause/context are
    cleared (``raise ... from None``) so pytest traceback cannot print secrets.
    """

    def __init__(
        self,
        *,
        phase: str,
        primary_error_type: str,
        primary_error_summary: str,
        rollback_error_summaries: list[str] | None = None,
        ownership_conflicts: list[str] | None = None,
    ) -> None:
        self.phase = _sanitize(phase)
        self.primary_error_type = _sanitize(primary_error_type) or "None"
        self.primary_error_summary = _truncate(_sanitize(primary_error_summary) or "<empty>")
        self.rollback_error_summaries = [
            _truncate(_sanitize(item) or "<empty>") for item in (rollback_error_summaries or [])
        ]
        self.ownership_conflicts = [
            _truncate(_sanitize(item) or "<empty>") for item in (ownership_conflicts or [])
        ]
        self.rollback_failure_count = len(self.rollback_error_summaries)
        message = _build_lifecycle_message(
            phase=self.phase,
            primary_error_type=self.primary_error_type,
            primary_error_summary=self.primary_error_summary,
            rollback_error_summaries=self.rollback_error_summaries,
            ownership_conflicts=self.ownership_conflicts,
        )
        super().__init__(message)

    def __repr__(self) -> str:
        """Safe repr: types/phase/counts only, no raw bodies."""
        return (
            f"NetworkGuardLifecycleError(phase={self.phase!r}, "
            f"primary_error_type={self.primary_error_type!r}, "
            f"rollback_failure_count={self.rollback_failure_count}, "
            f"ownership_conflicts={len(self.ownership_conflicts)})"
        )


def _truncate(text: str, max_len: int = _LIFECYCLE_MSG_LIMIT) -> str:
    """Ограничить длину диагностического текста."""
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}... <truncated {len(text) - max_len} chars>"


def _sanitize(text: str) -> str:
    """Fail-closed redact credentials/DSN/tokens in lifecycle diagnostics."""
    if not text:
        return ""
    value = text
    value = re.sub(
        r"(?i)([A-Za-z][A-Za-z0-9+.\-]*://)([^/\s:@]+):([^@\s]+)@",
        r"\1<redacted>:<redacted>@",
        value,
    )
    value = re.sub(
        r"(?i)(--(?:password|token|api-key))(?:\s+|=)(?:'[^']*'|\"[^\"]*\"|[^\s,;]+)",
        lambda match: f"{match.group(1)}=<redacted>",
        value,
    )
    value = re.sub(
        r"(?i)\b(PASSWORD|PASS|TOKEN|SECRET|API_KEY|DATABASE_URL|DSN)\b\s*([=:])\s*"
        r"(?:'[^']*'|\"[^\"]*\"|[^\s,;]+)?",
        lambda match: f"{match.group(1)}{match.group(2)}<redacted>",
        value,
    )
    value = re.sub(
        r"(?i)Authorization\s*:\s*(Bearer|Basic|Token)\s*(?:'[^']*'|\"[^\"]*\"|[^\s,;]+)",
        r"Authorization: \1 <redacted>",
        value,
    )
    value = re.sub(
        r"(?i)\b[A-Za-z0-9._-]+(?:TOKEN|PASSWORD|SECRET|API_KEY|DATABASE_URL|DSN|PASS)"
        r"[A-Za-z0-9._-]+\b",
        "<redacted>",
        value,
    )
    return _truncate(value)


def _summarize_exception(exc: BaseException | None) -> tuple[str, str]:
    """Вернуть (type_name, sanitized_summary) без хранения raw exception."""
    if exc is None:
        return ("None", "none")
    return (type(exc).__name__, _sanitize(str(exc)) or "<empty>")


def _build_lifecycle_message(
    *,
    phase: str,
    primary_error_type: str,
    primary_error_summary: str,
    rollback_error_summaries: list[str],
    ownership_conflicts: list[str],
) -> str:
    """Собрать безопасный lifecycle message без raw secrets."""
    rollback_desc = (
        ", ".join(rollback_error_summaries) if rollback_error_summaries else "none"
    )
    conflicts_desc = ", ".join(ownership_conflicts) if ownership_conflicts else "none"
    return _truncate(
        f"[NetworkGuardLifecycle] phase={phase}; "
        f"primary={primary_error_type}:{primary_error_summary}; "
        f"rollback_errors={rollback_desc}; "
        f"ownership_conflicts={conflicts_desc}; "
        f"rollback_failure_count={len(rollback_error_summaries)}"
    )


def _raise_lifecycle_error(
    *,
    phase: str,
    primary: BaseException | None,
    rollback_error_summaries: list[str] | None = None,
    ownership_conflicts: list[str] | None = None,
) -> None:
    """Raise credential-safe lifecycle error without exception chaining."""
    primary_type, primary_summary = _summarize_exception(primary)
    raise NetworkGuardLifecycleError(
        phase=phase,
        primary_error_type=primary_type,
        primary_error_summary=primary_summary,
        rollback_error_summaries=list(rollback_error_summaries or []),
        ownership_conflicts=list(ownership_conflicts or []),
    ) from None


def _static_probe_attribute(owner: Any, attribute: str) -> tuple[str, Any]:
    """Прочитать attribute без пользовательского ``__getattribute__``.

    Returns:
        ``("ok", value)`` или ``("error", exc)``.
    """
    try:
        owner_vars = vars(owner)
    except TypeError:
        owner_vars = None
    except Exception as exc:  # noqa: BLE001
        return ("error", exc)

    if isinstance(owner_vars, Mapping) and attribute in owner_vars:
        return ("ok", owner_vars[attribute])

    try:
        return ("ok", inspect.getattr_static(owner, attribute))
    except Exception as exc:  # noqa: BLE001
        return ("error", exc)


def _is_abstract_sock_connect_owner(owner: Any) -> bool:
    """True, если owner.sock_connect ссылается на абстрактную base implementation."""
    try:
        base_method = asyncio.base_events.BaseEventLoop.sock_connect
    except Exception:
        return False
    status, value = _static_probe_attribute(owner, "sock_connect")
    if status != "ok":
        return False
    return value is base_method


def _collect_concrete_sock_connect_owners() -> list[type[Any]]:
    """Собрать concrete owners для patch sock_connect без abstract delegate."""
    targets: list[type[Any]] = []

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None
    if running_loop is not None and hasattr(type(running_loop), "sock_connect"):
        targets.append(type(running_loop))

    tmp_loop = None
    try:
        tmp_loop = asyncio.new_event_loop()
        if hasattr(type(tmp_loop), "sock_connect"):
            targets.append(type(tmp_loop))
    except Exception:
        pass
    finally:
        if tmp_loop is not None:
            try:
                tmp_loop.close()
            except Exception:
                pass

    try:
        from asyncio import windows_events as we

        for name in ("ProactorEventLoop", "BaseProactorEventLoop"):
            owner = getattr(we, name, None)
            if owner is not None and hasattr(owner, "sock_connect"):
                targets.append(owner)
    except ImportError:
        pass

    seen: set[int] = set()
    unique: list[type[Any]] = []
    for owner in targets:
        if (
            id(owner) not in seen
            and hasattr(owner, "sock_connect")
            and not _is_abstract_sock_connect_owner(owner)
        ):
            seen.add(id(owner))
            unique.append(owner)
    return unique


def _clear_guard_registry() -> None:
    """Сбросить canonical registry/state."""
    global _guard_installed
    global _sock_connect_delegate_map
    global _patch_records

    _guard_installed = False
    _sock_connect_delegate_map = {}
    _patch_records = []


def _resolve_sock_connect_delegate(loop_instance: Any) -> Any | None:
    """Exact type, иначе ближайший registered concrete base по C3 MRO."""
    loop_type = type(loop_instance)
    delegate = _sock_connect_delegate_map.get(loop_type)
    if delegate is not None:
        return delegate
    for owner in loop_type.__mro__[1:]:
        delegate = _sock_connect_delegate_map.get(owner)
        if delegate is not None:
            return delegate
    return None


def _is_loopback_host(host: str) -> bool:
    """True для hostname allowlist или loopback IP."""
    normalized = host.strip().lower().strip("[]")
    if normalized in ALLOWED_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _extract_host(address: Any) -> str | None:
    """Достать hostname из tuple/str address."""
    if isinstance(address, tuple) and address:
        host = address[0]
        if isinstance(host, bytes):
            return host.decode(errors="replace")
        return str(host)
    if isinstance(address, str):
        return address
    return None


def _assert_address_allowed_for_family(
    address: Any,
    *,
    family: int,
    context: str,
) -> None:
    """Family-aware allow/deny до original call.

    AF_UNIX: str/bytes path — локальный IPC, разрешён без hostname semantics.
    """
    if family == getattr(socket, "AF_UNIX", -1):
        if isinstance(address, (str, bytes)):
            return
        raise NetworkGuardError(
            f"Outbound network blocked: malformed AF_UNIX address={address!r} "
            f"context={context}"
        )

    if family == socket.AF_INET:
        if not (isinstance(address, tuple) and len(address) >= 2):
            raise NetworkGuardError(
                f"Outbound network blocked: malformed AF_INET address={address!r} "
                f"context={context}"
            )
        host = _extract_host(address)
        if host is None:
            raise NetworkGuardError(
                f"Outbound network blocked: cannot parse AF_INET address={address!r} "
                f"context={context}"
            )
        assert_host_allowed(host, context=context)
        return

    if family == socket.AF_INET6:
        if not (isinstance(address, tuple) and len(address) >= 2):
            raise NetworkGuardError(
                f"Outbound network blocked: malformed AF_INET6 address={address!r} "
                f"context={context}"
            )
        host = _extract_host(address)
        if host is None:
            raise NetworkGuardError(
                f"Outbound network blocked: cannot parse AF_INET6 address={address!r} "
                f"context={context}"
            )
        assert_host_allowed(host, context=context)
        return

    raise NetworkGuardError(
        f"Outbound network blocked: unknown socket family={family} "
        f"address={address!r} context={context}"
    )


def assert_host_allowed(host: str, *, context: str) -> None:
    """Поднять NetworkGuardError если host не loopback."""
    if not _is_loopback_host(host):
        stack = "".join(traceback.format_stack(limit=20))
        raise NetworkGuardError(
            f"Outbound network blocked by test guard: host={host!r} "
            f"context={context}\nCall stack:\n{stack}"
        )


def clear_proxy_environment(*, environ: dict[str, str] | None = None) -> dict[str, str]:
    """Удалить proxy env, чтобы они не обходили guard."""
    env = environ if environ is not None else os.environ
    removed: dict[str, str] = {}
    for key in _PROXY_ENV_KEYS:
        if key in env:
            removed[key] = env.pop(key)
    return removed


def _restore_patch_records(
    records: list[_PatchRecord],
    *,
    rollback_error_summaries: list[str],
    conflicts: list[str],
    conflict_phase: str,
) -> None:
    """Ownership-safe rollback/uninstall через static probe (не через getattr)."""
    for record in reversed(records):
        status, current = _static_probe_attribute(record.owner, record.attribute)
        if status != "ok":
            err = current if isinstance(current, BaseException) else RuntimeError(str(current))
            _, summary = _summarize_exception(err)
            rollback_error_summaries.append(
                f"static-probe-failed:{type(err).__name__}:{summary}"
            )
            continue
        if current is record.installed_wrapper:
            try:
                setattr(record.owner, record.attribute, record.original)
            except Exception as set_exc:  # noqa: BLE001
                # setattr may mutate-then-raise: re-probe before recording failure.
                probe_status, probed = _static_probe_attribute(
                    record.owner, record.attribute
                )
                if probe_status == "ok" and probed is record.original:
                    continue
                _, summary = _summarize_exception(set_exc)
                rollback_error_summaries.append(
                    f"restore-failed:{type(set_exc).__name__}:{summary}"
                )
        elif current is record.original:
            continue
        else:
            conflicts.append(
                f"{record.owner!r}.{record.attribute} ownership conflict during {conflict_phase}"
            )


def _classify_setattr_failure(
    record: _PatchRecord,
    *,
    rollback_candidates: list[_PatchRecord],
    rollback_error_summaries: list[str],
    conflicts: list[str],
) -> None:
    """После exception из setattr: static probe → rollback / noop / conflict."""
    status, current = _static_probe_attribute(record.owner, record.attribute)
    if status != "ok":
        err = current if isinstance(current, BaseException) else RuntimeError(str(current))
        _, summary = _summarize_exception(err)
        rollback_error_summaries.append(
            f"static-probe-failed-after-setattr:{type(err).__name__}:{summary}"
        )
        return
    if current is record.installed_wrapper:
        rollback_candidates.append(replace(record, status="applied"))
        return
    if current is record.original:
        return
    conflicts.append(
        f"{record.owner!r}.{record.attribute} foreign value after setattr failure; "
        "preserved without overwrite"
    )


def install_network_guard() -> None:
    """Install guard atomically; publish canonical state только после полного успеха."""
    global _guard_installed
    global _sock_connect_delegate_map
    global _patch_records

    if _guard_installed:
        return

    clear_proxy_environment()

    orig_create = socket.create_connection
    orig_getaddr = socket.getaddrinfo
    orig_connect = socket.socket.connect
    orig_connect_ex = socket.socket.connect_ex
    owners = _collect_concrete_sock_connect_owners()
    local_delegate_map: dict[type[Any], Any] = {}
    for owner in owners:
        probe_status, saved = _static_probe_attribute(owner, "sock_connect")
        if probe_status != "ok":
            _raise_lifecycle_error(
                phase="install-plan",
                primary=saved if isinstance(saved, BaseException) else RuntimeError(str(saved)),
            )
        if _is_abstract_sock_connect_owner(owner) or (
            saved is asyncio.base_events.BaseEventLoop.sock_connect
        ):
            _raise_lifecycle_error(
                phase="install-plan",
                primary=RuntimeError(f"abstract sock_connect delegate for owner {owner!r}"),
            )
        if owner in local_delegate_map:
            _raise_lifecycle_error(
                phase="install-plan",
                primary=RuntimeError(f"duplicate owner in delegate map: {owner!r}"),
            )
        local_delegate_map[owner] = saved

    def guarded_create_connection(address, *args, **kwargs):  # type: ignore[no-untyped-def]
        host = _extract_host(address)
        if host is None:
            raise NetworkGuardError(
                f"Outbound network blocked: cannot parse address={address!r}"
            )
        assert_host_allowed(host, context="socket.create_connection")
        return orig_create(address, *args, **kwargs)

    def guarded_connect(self, address):  # type: ignore[no-untyped-def]
        family = getattr(self, "family", None)
        if family is None:
            raise NetworkGuardError(
                "Outbound network blocked: socket without family on connect"
            )
        _assert_address_allowed_for_family(
            address, family=int(family), context="socket.socket.connect"
        )
        return orig_connect(self, address)

    def guarded_connect_ex(self, address):  # type: ignore[no-untyped-def]
        family = getattr(self, "family", None)
        if family is None:
            raise NetworkGuardError(
                "Outbound network blocked: socket without family on connect_ex"
            )
        _assert_address_allowed_for_family(
            address, family=int(family), context="socket.socket.connect_ex"
        )
        return orig_connect_ex(self, address)

    def guarded_getaddrinfo(host, *args, **kwargs):  # type: ignore[no-untyped-def]
        host_s = host.decode(errors="replace") if isinstance(host, bytes) else str(host)
        if host_s and not _is_loopback_host(host_s):
            assert_host_allowed(host_s, context="socket.getaddrinfo")
        return orig_getaddr(host, *args, **kwargs)

    async def guarded_sock_connect(self, sock, address):  # type: ignore[no-untyped-def]
        # Delegation uses only published canonical map (no local-plan fallback).
        delegate = _resolve_sock_connect_delegate(self)
        if delegate is None:
            raise RuntimeError(
                "network_guard internal error: no concrete sock_connect delegate found"
            )
        family = getattr(sock, "family", None)
        if family is None:
            raise NetworkGuardError(
                "Outbound network blocked: sock without family on sock_connect"
            )
        _assert_address_allowed_for_family(
            address, family=int(family), context="asyncio.loop.sock_connect"
        )
        return await delegate(self, sock, address)

    patch_plan: list[_PatchRecord] = [
        _PatchRecord(socket, "create_connection", orig_create, guarded_create_connection),
        _PatchRecord(socket, "getaddrinfo", orig_getaddr, guarded_getaddrinfo),
        _PatchRecord(socket.socket, "connect", orig_connect, guarded_connect),
        _PatchRecord(socket.socket, "connect_ex", orig_connect_ex, guarded_connect_ex),
    ]
    patch_plan.extend(
        _PatchRecord(owner, "sock_connect", saved, guarded_sock_connect)
        for owner, saved in local_delegate_map.items()
    )

    rollback_candidates: list[_PatchRecord] = []
    primary_exc: BaseException | None = None
    rollback_error_summaries: list[str] = []
    conflicts: list[str] = []

    for planned in patch_plan:
        record = replace(planned, status="attempted")
        try:
            setattr(record.owner, record.attribute, record.installed_wrapper)
            rollback_candidates.append(replace(record, status="applied"))
        except Exception as set_exc:  # noqa: BLE001
            primary_exc = set_exc
            _classify_setattr_failure(
                record,
                rollback_candidates=rollback_candidates,
                rollback_error_summaries=rollback_error_summaries,
                conflicts=conflicts,
            )
            break

    if primary_exc is not None:
        _restore_patch_records(
            rollback_candidates,
            rollback_error_summaries=rollback_error_summaries,
            conflicts=conflicts,
            conflict_phase="install rollback",
        )
        _clear_guard_registry()
        _raise_lifecycle_error(
            phase="install-rollback",
            primary=primary_exc,
            rollback_error_summaries=rollback_error_summaries,
            ownership_conflicts=conflicts,
        )

    _sock_connect_delegate_map = dict(local_delegate_map)
    _patch_records = list(rollback_candidates)
    _guard_installed = True


def uninstall_network_guard(*, _allow_for_guard_unit_tests: bool = False) -> None:
    """Uninstall with ownership checks; safe no-op when already uninstalled.

    Pre-existing patches captured as ``original`` are restored.
    Targets mutated after install are preserved and reported as conflicts.
    """
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
                "(pass _allow_for_guard_unit_tests=True or set ALLOW_TEST_GUARD_UNINSTALL=1)"
            )

    if not _guard_installed:
        return

    rollback_error_summaries: list[str] = []
    conflicts: list[str] = []
    records = list(_patch_records)
    _restore_patch_records(
        records,
        rollback_error_summaries=rollback_error_summaries,
        conflicts=conflicts,
        conflict_phase="uninstall",
    )
    _clear_guard_registry()

    if rollback_error_summaries or conflicts:
        _raise_lifecycle_error(
            phase="uninstall",
            primary=RuntimeError("uninstall completed with lifecycle issues"),
            rollback_error_summaries=rollback_error_summaries,
            ownership_conflicts=conflicts,
        )


def is_network_guard_installed() -> bool:
    """Установлен ли guard в текущем процессе."""
    return _guard_installed
