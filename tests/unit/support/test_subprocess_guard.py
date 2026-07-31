"""Unit: fail-closed subprocess guard (без реального запуска CLI)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.support.subprocess_guard import (
    SubprocessGuardError,
    assert_subprocess_allowed,
    install_subprocess_guard,
    is_subprocess_guard_installed,
    restore_bootstrap_process_apis,
    uninstall_subprocess_guard,
)


@pytest.fixture
def isolated_subprocess_guard():
    """Изолировать subprocess guard для unit-проверок.

    Обязательно восстанавливает bootstrap process APIs после теста: иначе
    подмена ``_original_subprocess_run = MagicMock()`` при uninstall записывает
    mock в ``subprocess.run`` и session ``docker compose down`` падает с
    ``DOCKER_STAGE=cleanup`` / ``exit_code=<MagicMock ... returncode>`` на
    случайном последнем тесте (например graphic_positions DTO).
    """
    was = is_subprocess_guard_installed()
    uninstall_subprocess_guard(_allow_for_guard_unit_tests=True)
    restore_bootstrap_process_apis()
    install_subprocess_guard()
    yield
    uninstall_subprocess_guard(_allow_for_guard_unit_tests=True)
    restore_bootstrap_process_apis()
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
    import subprocess

    import tests.support.subprocess_guard as sg

    previous = sg._original_subprocess_run
    original = MagicMock()
    try:
        sg._original_subprocess_run = original
        with pytest.raises(SubprocessGuardError, match="curl"):
            subprocess.run(["curl", "https://example.com"], check=False)
        original.assert_not_called()
    finally:
        sg._original_subprocess_run = previous


@pytest.mark.unit
def test_os_system_blocks_without_calling_original(isolated_subprocess_guard) -> None:
    import os

    import tests.support.subprocess_guard as sg

    previous = sg._original_os_system
    original = MagicMock(return_value=0)
    try:
        sg._original_os_system = original
        with pytest.raises(SubprocessGuardError):
            os.system("curl https://example.com")
        original.assert_not_called()
    finally:
        sg._original_os_system = previous


@pytest.mark.unit
def test_os_popen_blocks_without_calling_original(isolated_subprocess_guard) -> None:
    import os

    import tests.support.subprocess_guard as sg

    previous = sg._original_os_popen
    original = MagicMock()
    try:
        sg._original_os_popen = original
        with pytest.raises(SubprocessGuardError):
            os.popen("wget https://example.com")
        original.assert_not_called()
    finally:
        sg._original_os_popen = previous


@pytest.mark.unit
@pytest.mark.asyncio
async def test_asyncio_exec_blocks_without_calling_original(
    isolated_subprocess_guard,
) -> None:
    import asyncio

    import tests.support.subprocess_guard as sg

    previous = sg._original_asyncio_exec
    original = AsyncMock()
    try:
        sg._original_asyncio_exec = original
        with pytest.raises(SubprocessGuardError):
            await asyncio.create_subprocess_exec("curl", "https://example.com")
        original.assert_not_called()
    finally:
        sg._original_asyncio_exec = previous


@pytest.mark.unit
@pytest.mark.asyncio
async def test_asyncio_shell_blocks_without_calling_original(
    isolated_subprocess_guard,
) -> None:
    import asyncio

    import tests.support.subprocess_guard as sg

    previous = sg._original_asyncio_shell
    original = AsyncMock()
    try:
        sg._original_asyncio_shell = original
        with pytest.raises(SubprocessGuardError):
            await asyncio.create_subprocess_shell("curl https://example.com")
        original.assert_not_called()
    finally:
        sg._original_asyncio_shell = previous


@pytest.mark.unit
def test_uninstall_forbidden_without_allow() -> None:
    with pytest.raises(RuntimeError, match="forbidden"):
        uninstall_subprocess_guard()


@pytest.mark.unit
def test_uninstall_does_not_restore_magicmock_as_subprocess_run(
    isolated_subprocess_guard,
) -> None:
    """Regression: MagicMock ``_original_*`` не должен утечь в subprocess.run.

    Исторический баг: unit подменял ``_original_subprocess_run = MagicMock()``,
    fixture uninstall писал mock в ``subprocess.run``, session compose down
    получал ``exit_code=<MagicMock name='mock().returncode'>`` и ERROR на
    последнем тесте сессии (victim: graphic_positions DTO).
    """
    import subprocess

    import tests.support.subprocess_guard as sg
    from tests.support.subprocess_guard import _BOOTSTRAP_SUBPROCESS_RUN, _is_mock_like

    sg._original_subprocess_run = MagicMock(name="leaked_original_run")
    uninstall_subprocess_guard(_allow_for_guard_unit_tests=True)

    assert not _is_mock_like(subprocess.run)
    assert subprocess.run is _BOOTSTRAP_SUBPROCESS_RUN

    # Вернуть guard для финализатора fixture (isolated_subprocess_guard).
    restore_bootstrap_process_apis()
    install_subprocess_guard()
