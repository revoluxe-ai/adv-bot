"""Fail-closed subprocess guard для unit / safe integration профиля.

Блокирует egress и port-forward не только по ``argv[0]``, но и по payload:

* curl / wget / ssh / scp / nc во всей командной строке
* ``bash|sh|cmd|powershell -c/-Command`` обёртки
* ``python -c`` с сетевыми токенами
* ``kubectl port-forward`` / ``ssh -L|-R|-D``
* ``os.system`` / ``os.popen``
* ``asyncio.create_subprocess_exec`` / ``create_subprocess_shell``

Docker/kubectl (без port-forward) требуют destructive opt-in.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

ALLOW_DESTRUCTIVE_TEST_SUBPROCESS_ENV: str = "ALLOW_DESTRUCTIVE_TEST_SUBPROCESS"
ALLOW_TEST_GUARD_UNINSTALL_ENV: str = "ALLOW_TEST_GUARD_UNINSTALL"

_ALWAYS_BLOCKED_BASENAMES: frozenset[str] = frozenset(
    {
        "curl",
        "curl.exe",
        "wget",
        "wget.exe",
        "ssh",
        "ssh.exe",
        "scp",
        "scp.exe",
        "nc",
        "nc.exe",
        "ncat",
        "ncat.exe",
        "telnet",
        "telnet.exe",
    }
)

_DESTRUCTIVE_ONLY_BASENAMES: frozenset[str] = frozenset(
    {
        "docker",
        "docker.exe",
        "docker-compose",
        "docker-compose.exe",
        "kubectl",
        "kubectl.exe",
    }
)

_SHELL_BASENAMES: frozenset[str] = frozenset(
    {
        "bash",
        "bash.exe",
        "sh",
        "sh.exe",
        "zsh",
        "zsh.exe",
        "cmd",
        "cmd.exe",
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
    }
)

_PYTHON_BASENAMES: frozenset[str] = frozenset(
    {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}
)

_PS_WEB_TOKENS: frozenset[str] = frozenset(
    {
        "invoke-webrequest",
        "invoke-restmethod",
        "iwr",
        "irm",
        "webclient",
        "downloadstring",
        "downloadfile",
        "httpclient",
    }
)

_NETWORK_PAYLOAD_TOKENS: tuple[str, ...] = (
    "curl",
    "wget",
    "ssh",
    "scp",
    "ncat",
    "telnet",
    "port-forward",
    "port_forward",
    "invoke-webrequest",
    "invoke-restmethod",
    "webclient",
    "urllib",
    "httpx",
    "aiohttp",
    "requests.",
    "socket.",
    "http.client",
    "https://",
    "http://",
)

_SSH_FORWARD_RE = re.compile(r"(^|\s)-(?:L|R|D)\b")

_guard_installed: bool = False
_original_subprocess_run: Callable[..., Any] | None = None
_original_subprocess_popen: Callable[..., Any] | None = None
_original_subprocess_call: Callable[..., Any] | None = None
_original_subprocess_check_call: Callable[..., Any] | None = None
_original_subprocess_check_output: Callable[..., Any] | None = None
_original_os_system: Callable[..., Any] | None = None
_original_os_popen: Callable[..., Any] | None = None
_original_asyncio_exec: Callable[..., Any] | None = None
_original_asyncio_shell: Callable[..., Any] | None = None

# Snapshot at import (before unit tests may replace ``_original_*`` with MagicMock).
# Used to recover after polluting guard unit tests that overwrite originals.
_BOOTSTRAP_SUBPROCESS_RUN: Callable[..., Any] = subprocess.run
_BOOTSTRAP_SUBPROCESS_POPEN: Callable[..., Any] = subprocess.Popen
_BOOTSTRAP_SUBPROCESS_CALL: Callable[..., Any] = subprocess.call
_BOOTSTRAP_SUBPROCESS_CHECK_CALL: Callable[..., Any] = subprocess.check_call
_BOOTSTRAP_SUBPROCESS_CHECK_OUTPUT: Callable[..., Any] = subprocess.check_output
_BOOTSTRAP_OS_SYSTEM: Callable[..., Any] = os.system
_BOOTSTRAP_OS_POPEN: Callable[..., Any] = os.popen
_BOOTSTRAP_ASYNCIO_EXEC: Callable[..., Any] = asyncio.create_subprocess_exec
_BOOTSTRAP_ASYNCIO_SHELL: Callable[..., Any] = asyncio.create_subprocess_shell


def _is_mock_like(obj: object) -> bool:
    """True если callable похож на unittest.mock (утечка из unit-suite)."""
    mod = getattr(type(obj), "__module__", "") or ""
    name = type(obj).__name__
    return mod.startswith("unittest.mock") or name in {
        "MagicMock",
        "Mock",
        "AsyncMock",
        "NonCallableMagicMock",
    }


def _resolve_install_original(
    current: object, bootstrap: Callable[..., Any]
) -> Callable[..., Any]:
    """Выбрать original для install: current, если не mock, иначе bootstrap."""
    if _is_mock_like(current):
        return bootstrap
    return current  # type: ignore[return-value]


def restore_bootstrap_process_apis() -> None:
    """Принудительно вернуть process APIs к bootstrap (post-pollution recovery).

    Вызывать после unit-тестов guard, которые подменяли ``_original_*`` на
    ``MagicMock``: иначе ``uninstall`` записывает MagicMock в ``subprocess.run``
    и session docker cleanup падает с ``exit_code=<MagicMock ... returncode>``.
    """
    global _original_subprocess_run
    global _original_subprocess_popen
    global _original_subprocess_call
    global _original_subprocess_check_call
    global _original_subprocess_check_output
    global _original_os_system
    global _original_os_popen
    global _original_asyncio_exec
    global _original_asyncio_shell

    subprocess.run = _BOOTSTRAP_SUBPROCESS_RUN  # type: ignore[assignment]
    subprocess.Popen = _BOOTSTRAP_SUBPROCESS_POPEN  # type: ignore[misc, assignment]
    subprocess.call = _BOOTSTRAP_SUBPROCESS_CALL  # type: ignore[assignment]
    subprocess.check_call = _BOOTSTRAP_SUBPROCESS_CHECK_CALL  # type: ignore[assignment]
    subprocess.check_output = _BOOTSTRAP_SUBPROCESS_CHECK_OUTPUT  # type: ignore[assignment]
    os.system = _BOOTSTRAP_OS_SYSTEM  # type: ignore[assignment]
    os.popen = _BOOTSTRAP_OS_POPEN  # type: ignore[assignment]
    asyncio.create_subprocess_exec = _BOOTSTRAP_ASYNCIO_EXEC  # type: ignore[assignment]
    asyncio.create_subprocess_shell = _BOOTSTRAP_ASYNCIO_SHELL  # type: ignore[assignment]
    if _guard_installed:
        _original_subprocess_run = _BOOTSTRAP_SUBPROCESS_RUN
        _original_subprocess_popen = _BOOTSTRAP_SUBPROCESS_POPEN
        _original_subprocess_call = _BOOTSTRAP_SUBPROCESS_CALL
        _original_subprocess_check_call = _BOOTSTRAP_SUBPROCESS_CHECK_CALL
        _original_subprocess_check_output = _BOOTSTRAP_SUBPROCESS_CHECK_OUTPUT
        _original_os_system = _BOOTSTRAP_OS_SYSTEM
        _original_os_popen = _BOOTSTRAP_OS_POPEN
        _original_asyncio_exec = _BOOTSTRAP_ASYNCIO_EXEC
        _original_asyncio_shell = _BOOTSTRAP_ASYNCIO_SHELL
    else:
        _original_subprocess_run = None
        _original_subprocess_popen = None
        _original_subprocess_call = None
        _original_subprocess_check_call = None
        _original_subprocess_check_output = None
        _original_os_system = None
        _original_os_popen = None
        _original_asyncio_exec = None
        _original_asyncio_shell = None


class SubprocessGuardError(RuntimeError):
    """Запуск subprocess заблокирован test subprocess guard."""


def _parse_truthy(raw: str | None) -> bool:
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_destructive_subprocess_opt_in_enabled(
    *,
    environ: dict[str, str] | None = None,
) -> bool:
    """Разрешены ли docker (destructive_local + opt-in).

    ``kubectl port-forward`` всё равно блокируется.
    """
    env = environ if environ is not None else os.environ
    if _parse_truthy(env.get(ALLOW_DESTRUCTIVE_TEST_SUBPROCESS_ENV)):
        return True
    if _parse_truthy(env.get("ALLOW_DESTRUCTIVE_TEST_DB")):
        return True
    if _parse_truthy(env.get("ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE")):
        return True
    return False


def _basename(argv0: str) -> str:
    return Path(str(argv0)).name.lower()


def _normalize_argv(args: Any) -> list[str]:
    if isinstance(args, (str, bytes)):
        text = args.decode() if isinstance(args, bytes) else args
        return text.split()
    if isinstance(args, Sequence):
        return [str(a) for a in args]
    return [str(args)]


def _joined_command(args: Any) -> str:
    if isinstance(args, (str, bytes)):
        return args.decode() if isinstance(args, bytes) else args
    return " ".join(_normalize_argv(args))


def _payload_has_network_token(joined_lower: str) -> str | None:
    """Вернуть первый запрещённый token в payload или None."""
    for token in _NETWORK_PAYLOAD_TOKENS:
        if token in joined_lower:
            return token
    if _SSH_FORWARD_RE.search(joined_lower):
        return "ssh-port-forward"
    for token in _PS_WEB_TOKENS:
        if token in joined_lower:
            return token
    return None


def assert_subprocess_allowed(
    args: Any,
    *,
    environ: dict[str, str] | None = None,
) -> None:
    """Проверить argv/payload до запуска. Без сетевого I/O."""
    argv = _normalize_argv(args)
    if not argv:
        raise SubprocessGuardError("Empty subprocess argv — refuse")
    base = _basename(argv[0])
    joined = _joined_command(args)
    joined_lower = joined.lower()

    # Port-forward anywhere in the command line.
    if "port-forward" in joined_lower or "port_forward" in joined_lower:
        raise SubprocessGuardError(
            "Subprocess blocked by test guard: port-forward forbidden"
        )

    if base in _ALWAYS_BLOCKED_BASENAMES:
        raise SubprocessGuardError(
            f"Subprocess blocked by test guard: executable={base!r} "
            "(HTTP/SSH CLI forbidden in unit/safe profile)"
        )

    # Shell wrappers: default-deny network tokens in full payload.
    if base in _SHELL_BASENAMES:
        hit = _payload_has_network_token(joined_lower)
        if hit is not None:
            raise SubprocessGuardError(
                f"Subprocess blocked by test guard: shell payload contains "
                f"forbidden token {hit!r}"
            )
        # Default-deny interactive shell -c with unknown body still OK for
        # non-network local commands; block bare curl-like basenames inside.
        for blocked in _ALWAYS_BLOCKED_BASENAMES:
            # word-boundary-ish: " curl " or start/end
            if re.search(rf"(^|[\s&|;]){re.escape(blocked.removesuffix('.exe'))}([\s&|;.]|$)", joined_lower):
                raise SubprocessGuardError(
                    f"Subprocess blocked by test guard: shell invokes {blocked!r}"
                )

    if base in _PYTHON_BASENAMES:
        # python -c <code> / -m http.server etc.
        hit = _payload_has_network_token(joined_lower)
        if hit is not None:
            raise SubprocessGuardError(
                f"Subprocess blocked by test guard: python payload contains "
                f"forbidden token {hit!r}"
            )

    if base in _DESTRUCTIVE_ONLY_BASENAMES:
        if not is_destructive_subprocess_opt_in_enabled(environ=environ):
            raise SubprocessGuardError(
                f"Subprocess blocked by test guard: executable={base!r} "
                f"requires {ALLOW_DESTRUCTIVE_TEST_SUBPROCESS_ENV}=1 "
                "(destructive_local only)"
            )


def install_subprocess_guard() -> None:
    """Патч subprocess/os/asyncio process APIs. Идемпотентно."""
    global _guard_installed
    global _original_subprocess_run
    global _original_subprocess_popen
    global _original_subprocess_call
    global _original_subprocess_check_call
    global _original_subprocess_check_output
    global _original_os_system
    global _original_os_popen
    global _original_asyncio_exec
    global _original_asyncio_shell

    if _guard_installed:
        return

    _original_subprocess_run = _resolve_install_original(
        subprocess.run, _BOOTSTRAP_SUBPROCESS_RUN
    )
    _original_subprocess_popen = _resolve_install_original(
        subprocess.Popen, _BOOTSTRAP_SUBPROCESS_POPEN
    )
    _original_subprocess_call = _resolve_install_original(
        subprocess.call, _BOOTSTRAP_SUBPROCESS_CALL
    )
    _original_subprocess_check_call = _resolve_install_original(
        subprocess.check_call, _BOOTSTRAP_SUBPROCESS_CHECK_CALL
    )
    _original_subprocess_check_output = _resolve_install_original(
        subprocess.check_output, _BOOTSTRAP_SUBPROCESS_CHECK_OUTPUT
    )
    _original_os_system = _resolve_install_original(os.system, _BOOTSTRAP_OS_SYSTEM)
    _original_os_popen = _resolve_install_original(os.popen, _BOOTSTRAP_OS_POPEN)
    _original_asyncio_exec = _resolve_install_original(
        asyncio.create_subprocess_exec, _BOOTSTRAP_ASYNCIO_EXEC
    )
    _original_asyncio_shell = _resolve_install_original(
        asyncio.create_subprocess_shell, _BOOTSTRAP_ASYNCIO_SHELL
    )

    def guarded_run(*p_args, **kwargs):  # type: ignore[no-untyped-def]
        argv = p_args[0] if p_args else kwargs.get("args")
        assert_subprocess_allowed(argv)
        assert _original_subprocess_run is not None
        return _original_subprocess_run(*p_args, **kwargs)

    def guarded_popen(*p_args, **kwargs):  # type: ignore[no-untyped-def]
        argv = p_args[0] if p_args else kwargs.get("args")
        assert_subprocess_allowed(argv)
        assert _original_subprocess_popen is not None
        return _original_subprocess_popen(*p_args, **kwargs)

    def guarded_call(*p_args, **kwargs):  # type: ignore[no-untyped-def]
        argv = p_args[0] if p_args else kwargs.get("args")
        assert_subprocess_allowed(argv)
        assert _original_subprocess_call is not None
        return _original_subprocess_call(*p_args, **kwargs)

    def guarded_check_call(*p_args, **kwargs):  # type: ignore[no-untyped-def]
        argv = p_args[0] if p_args else kwargs.get("args")
        assert_subprocess_allowed(argv)
        assert _original_subprocess_check_call is not None
        return _original_subprocess_check_call(*p_args, **kwargs)

    def guarded_check_output(*p_args, **kwargs):  # type: ignore[no-untyped-def]
        argv = p_args[0] if p_args else kwargs.get("args")
        assert_subprocess_allowed(argv)
        assert _original_subprocess_check_output is not None
        return _original_subprocess_check_output(*p_args, **kwargs)

    def guarded_os_system(command: Any) -> Any:
        assert_subprocess_allowed(command)
        assert _original_os_system is not None
        return _original_os_system(command)

    def guarded_os_popen(command: Any, *args: Any, **kwargs: Any) -> Any:
        assert_subprocess_allowed(command)
        assert _original_os_popen is not None
        return _original_os_popen(command, *args, **kwargs)

    async def guarded_asyncio_exec(*p_args: Any, **kwargs: Any) -> Any:
        assert_subprocess_allowed(p_args)
        assert _original_asyncio_exec is not None
        return await _original_asyncio_exec(*p_args, **kwargs)

    async def guarded_asyncio_shell(cmd: Any, **kwargs: Any) -> Any:
        assert_subprocess_allowed(cmd)
        assert _original_asyncio_shell is not None
        return await _original_asyncio_shell(cmd, **kwargs)

    subprocess.run = guarded_run  # type: ignore[assignment]
    subprocess.Popen = guarded_popen  # type: ignore[misc, assignment]
    subprocess.call = guarded_call  # type: ignore[assignment]
    subprocess.check_call = guarded_check_call  # type: ignore[assignment]
    subprocess.check_output = guarded_check_output  # type: ignore[assignment]
    os.system = guarded_os_system  # type: ignore[assignment]
    os.popen = guarded_os_popen  # type: ignore[assignment]
    asyncio.create_subprocess_exec = guarded_asyncio_exec  # type: ignore[assignment]
    asyncio.create_subprocess_shell = guarded_asyncio_shell  # type: ignore[assignment]
    _guard_installed = True


def uninstall_subprocess_guard(*, _allow_for_guard_unit_tests: bool = False) -> None:
    """Восстановить оригинальные subprocess/os/asyncio APIs.

    Обычным тестам запрещено. Unit-тесты guard передают
    ``_allow_for_guard_unit_tests=True`` либо ставят
    ``ALLOW_TEST_GUARD_UNINSTALL=1``.
    """
    global _guard_installed
    global _original_subprocess_run
    global _original_subprocess_popen
    global _original_subprocess_call
    global _original_subprocess_check_call
    global _original_subprocess_check_output
    global _original_os_system
    global _original_os_popen
    global _original_asyncio_exec
    global _original_asyncio_shell

    if not _allow_for_guard_unit_tests and not _parse_truthy(
        os.environ.get(ALLOW_TEST_GUARD_UNINSTALL_ENV)
    ):
        raise RuntimeError(
            "uninstall_subprocess_guard is forbidden outside guard unit tests "
            f"(pass _allow_for_guard_unit_tests=True or set "
            f"{ALLOW_TEST_GUARD_UNINSTALL_ENV}=1)"
        )

    if not _guard_installed:
        return

    # Если unit-тест подменил ``_original_*`` на MagicMock — не записывать
    # mock обратно в process APIs (иначе session docker cleanup ломается).
    def _restore(api_attr: str, original: object, bootstrap: Callable[..., Any]) -> None:
        target_mod = subprocess if api_attr.startswith("subprocess.") else (
            os if api_attr.startswith("os.") else asyncio
        )
        name = api_attr.split(".", 1)[1]
        value = bootstrap if original is None or _is_mock_like(original) else original
        setattr(target_mod, name, value)

    _restore("subprocess.run", _original_subprocess_run, _BOOTSTRAP_SUBPROCESS_RUN)
    _restore("subprocess.Popen", _original_subprocess_popen, _BOOTSTRAP_SUBPROCESS_POPEN)
    _restore("subprocess.call", _original_subprocess_call, _BOOTSTRAP_SUBPROCESS_CALL)
    _restore(
        "subprocess.check_call",
        _original_subprocess_check_call,
        _BOOTSTRAP_SUBPROCESS_CHECK_CALL,
    )
    _restore(
        "subprocess.check_output",
        _original_subprocess_check_output,
        _BOOTSTRAP_SUBPROCESS_CHECK_OUTPUT,
    )
    _restore("os.system", _original_os_system, _BOOTSTRAP_OS_SYSTEM)
    _restore("os.popen", _original_os_popen, _BOOTSTRAP_OS_POPEN)
    _restore(
        "asyncio.create_subprocess_exec",
        _original_asyncio_exec,
        _BOOTSTRAP_ASYNCIO_EXEC,
    )
    _restore(
        "asyncio.create_subprocess_shell",
        _original_asyncio_shell,
        _BOOTSTRAP_ASYNCIO_SHELL,
    )
    _original_subprocess_run = None
    _original_subprocess_popen = None
    _original_subprocess_call = None
    _original_subprocess_check_call = None
    _original_subprocess_check_output = None
    _original_os_system = None
    _original_os_popen = None
    _original_asyncio_exec = None
    _original_asyncio_shell = None
    _guard_installed = False


def is_subprocess_guard_installed() -> bool:
    """Установлен ли subprocess guard."""
    return _guard_installed
