"""Unit: fail-closed subprocess guard (без реального запуска CLI)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.support.subprocess_guard import (
    SubprocessGuardError,
    assert_subprocess_allowed,
    install_subprocess_guard,
    is_subprocess_guard_installed,
    uninstall_subprocess_guard,
)


@pytest.fixture
def isolated_subprocess_guard():
    """Изолировать subprocess guard для unit-проверок."""
    was = is_subprocess_guard_installed()
    uninstall_subprocess_guard(_allow_for_guard_unit_tests=True)
    install_subprocess_guard()
    yield
    uninstall_subprocess_guard(_allow_for_guard_unit_tests=True)
    if was:
        install_subprocess_guard()


@pytest.mark.unit
def test_curl_blocked() -> None:
    with pytest.raises(SubprocessGuardError, match="curl"):
        assert_subprocess_allowed(["curl", "https://example.com"])


@pytest.mark.unit
def test_wget_blocked() -> None:
    with pytest.raises(SubprocessGuardError, match="wget"):
        assert_subprocess_allowed(["wget", "https://example.com"])


@pytest.mark.unit
def test_kubectl_port_forward_blocked() -> None:
    with pytest.raises(SubprocessGuardError, match="port-forward"):
        assert_subprocess_allowed(
            ["kubectl", "port-forward", "svc/postgres", "5433:5432"]
        )


@pytest.mark.unit
def test_powershell_web_blocked() -> None:
    with pytest.raises(SubprocessGuardError, match="web|forbidden"):
        assert_subprocess_allowed(
            [
                "powershell",
                "-Command",
                "Invoke-WebRequest https://example.com",
            ]
        )


@pytest.mark.unit
def test_bash_curl_payload_blocked() -> None:
    with pytest.raises(SubprocessGuardError):
        assert_subprocess_allowed(["bash", "-c", "curl https://example.com"])


@pytest.mark.unit
def test_cmd_curl_payload_blocked() -> None:
    with pytest.raises(SubprocessGuardError):
        assert_subprocess_allowed(["cmd", "/c", "curl https://example.com"])


@pytest.mark.unit
def test_sh_wget_payload_blocked() -> None:
    with pytest.raises(SubprocessGuardError):
        assert_subprocess_allowed(["sh", "-c", "wget https://example.com"])


@pytest.mark.unit
def test_python_urllib_payload_blocked() -> None:
    with pytest.raises(SubprocessGuardError):
        assert_subprocess_allowed(
            [
                "python",
                "-c",
                "import urllib.request; urllib.request.urlopen('https://x')",
            ]
        )


@pytest.mark.unit
def test_docker_blocked_without_opt_in() -> None:
    with pytest.raises(SubprocessGuardError, match="ALLOW_DESTRUCTIVE"):
        assert_subprocess_allowed(["docker", "ps"], environ={})


@pytest.mark.unit
def test_docker_allowed_with_pg_opt_in() -> None:
    assert_subprocess_allowed(
        ["docker", "ps"],
        environ={"ALLOW_DESTRUCTIVE_TEST_DB": "1"},
    )


@pytest.mark.unit
def test_subprocess_run_blocks_curl_without_calling_original(
    isolated_subprocess_guard,
) -> None:
    import tests.support.subprocess_guard as sg

    original = MagicMock()
    sg._original_subprocess_run = original
    import subprocess

    with pytest.raises(SubprocessGuardError, match="curl"):
        subprocess.run(["curl", "https://example.com"], check=False)
    original.assert_not_called()


@pytest.mark.unit
def test_os_system_blocks_without_calling_original(isolated_subprocess_guard) -> None:
    import tests.support.subprocess_guard as sg

    original = MagicMock(return_value=0)
    sg._original_os_system = original
    import os

    with pytest.raises(SubprocessGuardError):
        os.system("curl https://example.com")
    original.assert_not_called()


@pytest.mark.unit
def test_os_popen_blocks_without_calling_original(isolated_subprocess_guard) -> None:
    import tests.support.subprocess_guard as sg

    original = MagicMock()
    sg._original_os_popen = original
    import os

    with pytest.raises(SubprocessGuardError):
        os.popen("wget https://example.com")
    original.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_asyncio_exec_blocks_without_calling_original(
    isolated_subprocess_guard,
) -> None:
    import tests.support.subprocess_guard as sg

    original = AsyncMock()
    sg._original_asyncio_exec = original
    import asyncio

    with pytest.raises(SubprocessGuardError):
        await asyncio.create_subprocess_exec("curl", "https://example.com")
    original.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_asyncio_shell_blocks_without_calling_original(
    isolated_subprocess_guard,
) -> None:
    import tests.support.subprocess_guard as sg

    original = AsyncMock()
    sg._original_asyncio_shell = original
    import asyncio

    with pytest.raises(SubprocessGuardError):
        await asyncio.create_subprocess_shell("curl https://example.com")
    original.assert_not_called()


@pytest.mark.unit
def test_uninstall_forbidden_without_allow() -> None:
    with pytest.raises(RuntimeError, match="forbidden"):
        uninstall_subprocess_guard()
