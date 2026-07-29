"""Mock-only tests for destructive integration orchestration in root conftest.

Покрывает fail-closed Docker lifecycle, корректный приоритет primary ошибок,
reset cleanup state и безопасную санитизацию диагностик.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.support.destructive_pg_dsn import DestructiveTestDatabaseError

_ROOT_CONFTEST_PATH = Path(__file__).resolve().parents[3] / "conftest.py"
_ROOT_SPEC = importlib.util.spec_from_file_location(
    "_root_conftest_for_destructive_orchestration",
    _ROOT_CONFTEST_PATH,
)
assert _ROOT_SPEC is not None and _ROOT_SPEC.loader is not None
root_conftest = importlib.util.module_from_spec(_ROOT_SPEC)
_ROOT_SPEC.loader.exec_module(root_conftest)

_SAFE_ENV = {
    "ALLOW_DESTRUCTIVE_TEST_DB": "1",
    "DEV_TUNNELS_ENABLED": "false",
    "DEV_TUNNELS_KUBECONFIG": "",
    "DEV_TUNNEL_PG_LOCAL_PORT": "",
    "DEV_TUNNEL_CH_HTTP_PORT": "",
}


def _unwrap_fixture_function(func: object):
    """Вернуть исходную функцию fixture без pytest wrapper."""
    return getattr(func, "__wrapped__", func)


def _request_with_destructive_marker(fixturename: str) -> pytest.FixtureRequest:
    """Собрать request/node с marker ``destructive_local``."""

    class _Marker:
        pass

    class _Node:
        keywords: dict[str, object] = {"destructive_local": True}

        def get_closest_marker(self, name: str):
            return _Marker() if name == "destructive_local" else None

    return SimpleNamespace(fixturename=fixturename, node=_Node())  # type: ignore[return-value]


def _get_compose_down_call(sync_run: MagicMock):
    """Вернуть call для compose down -v --remove-orphans, если он был."""
    for call in sync_run.call_args_list:
        argv = call.args
        if "down" in argv and "-v" in argv and "--remove-orphans" in argv:
            return call
    return None


def _has_compose_down_call(sync_run: MagicMock) -> bool:
    """Проверить, что cleanup compose down действительно вызывался."""
    return _get_compose_down_call(sync_run) is not None


def _asyncio_run_mock_success(coro) -> None:
    """Mock asyncio.run success without awaiting real coroutine body."""
    coro.close()
    return None


def _sync_run_happy_path(*args: str, **_kwargs: object) -> tuple[int, str, str]:
    """Полностью успешный docker flow: preflight -> up -> health -> down."""
    if args == ("docker", "--version"):
        return 0, "Docker version 26.1.0", ""
    if args == ("docker", "info", "--format", "{{.ServerVersion}}"):
        return 0, "26.1.0", ""
    if args == ("docker", "compose", "version"):
        return 0, "Docker Compose version v2.27.0", ""
    if "up" in args:
        return 0, "", ""
    if "ps" in args and "-q" in args and "test_db" in args:
        return 0, "cid-123\n", ""
    if args[:2] == ("docker", "inspect"):
        return 0, "running healthy", ""
    if args[:2] == ("docker", "exec"):
        return 0, "", ""
    if "down" in args:
        return 0, "", ""
    return 0, "", ""


@pytest.mark.unit
def test_docker_cli_missing_raises_error_without_skip() -> None:
    """Отсутствие Docker CLI => fail-closed ошибка detect, без skip."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    sync_run = MagicMock(
        side_effect=lambda *a, **k: (127, "", "command not found: docker")
        if a == ("docker", "--version")
        else (0, "", "")
    )
    skip_mock = MagicMock()
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.pytest, "skip", skip_mock),
    ):
        with pytest.raises(RuntimeError, match=r"DOCKER_STAGE=detect.*exit_code=127"):
            gen = setup_fn(request)
            next(gen)
    skip_mock.assert_not_called()


@pytest.mark.unit
def test_docker_daemon_unavailable_raises_error_without_skip() -> None:
    """Недоступный daemon => fail-closed ошибка daemon, без skip."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)

    def _daemon_down(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if args == ("docker", "--version"):
            return 0, "Docker version 26.1.0", ""
        if args == ("docker", "info", "--format", "{{.ServerVersion}}"):
            return 1, "", "cannot connect to daemon"
        return 0, "", ""

    sync_run = MagicMock(side_effect=_daemon_down)
    skip_mock = MagicMock()
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.pytest, "skip", skip_mock),
    ):
        with pytest.raises(RuntimeError, match=r"DOCKER_STAGE=daemon.*exit_code=1"):
            gen = setup_fn(request)
            next(gen)
    skip_mock.assert_not_called()


@pytest.mark.unit
def test_compose_unavailable_raises_error_without_skip() -> None:
    """Недоступный compose => fail-closed ошибка compose, без skip."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)

    def _compose_missing(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if args == ("docker", "--version"):
            return 0, "Docker version 26.1.0", ""
        if args == ("docker", "info", "--format", "{{.ServerVersion}}"):
            return 0, "26.1.0", ""
        if args == ("docker", "compose", "version"):
            return 127, "", "docker: 'compose' is not a docker command"
        return 0, "", ""

    sync_run = MagicMock(side_effect=_compose_missing)
    skip_mock = MagicMock()
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.pytest, "skip", skip_mock),
    ):
        with pytest.raises(RuntimeError, match=r"DOCKER_STAGE=compose.*exit_code=127"):
            gen = setup_fn(request)
            next(gen)
    skip_mock.assert_not_called()


@pytest.mark.unit
def test_compose_up_non_zero_keeps_source_error_and_calls_down() -> None:
    """compose up non-zero: сохраняется stage=up и вызывается cleanup down."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)

    def _up_fails(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if args == ("docker", "--version"):
            return 0, "Docker version 26.1.0", ""
        if args == ("docker", "info", "--format", "{{.ServerVersion}}"):
            return 0, "26.1.0", ""
        if args == ("docker", "compose", "version"):
            return 0, "Docker Compose version v2.27.0", ""
        if "up" in args:
            return 1, "", "compose up failed"
        if "down" in args:
            return 0, "", ""
        if "ps" in args and "-q" in args and "test_db" in args:
            return 0, "cid-partial\n", ""
        return 0, "", ""

    sync_run = MagicMock(side_effect=_up_fails)
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
    ):
        with pytest.raises(RuntimeError, match=r"DOCKER_STAGE=up.*exit_code=1"):
            gen = setup_fn(request)
            next(gen)
    assert _has_compose_down_call(sync_run)


@pytest.mark.unit
def test_health_timeout_raises_error_and_calls_down() -> None:
    """Health timeout => fail-closed stage=health + обязательный cleanup."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)

    def _never_healthy(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if args == ("docker", "--version"):
            return 0, "Docker version 26.1.0", ""
        if args == ("docker", "info", "--format", "{{.ServerVersion}}"):
            return 0, "26.1.0", ""
        if args == ("docker", "compose", "version"):
            return 0, "Docker Compose version v2.27.0", ""
        if "up" in args:
            return 0, "", ""
        if "ps" in args and "-q" in args and "test_db" in args:
            return 0, "cid-123\n", ""
        if args[:2] == ("docker", "inspect"):
            return 0, "running starting", ""
        if "down" in args:
            return 0, "", ""
        return 0, "", ""

    sync_run = MagicMock(side_effect=_never_healthy)
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest, "SETUP_DB_STARTUP_MAX_RETRIES", 2),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        with pytest.raises(RuntimeError, match=r"DOCKER_STAGE=health"):
            gen = setup_fn(request)
            next(gen)
    assert _has_compose_down_call(sync_run)


@pytest.mark.unit
def test_successful_setup_then_cleanup_rc_non_zero_raises_cleanup_error() -> None:
    """Успешный setup/test + down rc!=0 должен падать stage=cleanup."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)

    def _cleanup_non_zero(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if "down" in args:
            return 2, "", "cleanup failed TOKEN=abc123"
        return _sync_run_happy_path(*args, **_kwargs)

    sync_run = MagicMock(side_effect=_cleanup_non_zero)
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        gen = setup_fn(request)
        next(gen)
        with pytest.raises(RuntimeError, match=r"DOCKER_STAGE=cleanup.*exit_code=2"):
            gen.close()
    assert root_conftest._DOCKER_CLEANUP_STATE["container_id"] is None
    assert root_conftest._DOCKER_CLEANUP_STATE["compose_cmd"] is None
    assert root_conftest._TEST_DB_READY is False


@pytest.mark.unit
def test_successful_setup_then_cleanup_exception_raises_cleanup_error() -> None:
    """Успешный setup/test + exception в down должен падать stage=cleanup."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)

    def _cleanup_raises(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if "down" in args:
            raise RuntimeError("down exploded PASSWORD=secret")
        return _sync_run_happy_path(*args, **_kwargs)

    sync_run = MagicMock(side_effect=_cleanup_raises)
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        gen = setup_fn(request)
        next(gen)
        with pytest.raises(RuntimeError, match=r"DOCKER_STAGE=cleanup"):
            gen.close()
    assert root_conftest._DOCKER_CLEANUP_STATE["container_id"] is None
    assert root_conftest._DOCKER_CLEANUP_STATE["compose_cmd"] is None
    assert root_conftest._TEST_DB_READY is False


@pytest.mark.unit
def test_primary_setup_error_preserved_when_cleanup_non_zero() -> None:
    """Primary setup ошибка не маскируется cleanup rc!=0."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)

    def _up_fails_and_cleanup_non_zero(
        *args: str, **_kwargs: object
    ) -> tuple[int, str, str]:
        if "up" in args:
            return 1, "", "compose up failed hard"
        if "down" in args:
            return 9, "", "cleanup rc!=0"
        if args == ("docker", "--version"):
            return 0, "Docker version 26.1.0", ""
        if args == ("docker", "info", "--format", "{{.ServerVersion}}"):
            return 0, "26.1.0", ""
        if args == ("docker", "compose", "version"):
            return 0, "Docker Compose version v2.27.0", ""
        return 0, "", ""

    sync_run = MagicMock(side_effect=_up_fails_and_cleanup_non_zero)
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
    ):
        with pytest.raises(RuntimeError, match=r"DOCKER_STAGE=up.*compose up failed hard"):
            gen = setup_fn(request)
            next(gen)
    assert _has_compose_down_call(sync_run)


@pytest.mark.unit
def test_primary_test_error_preserved_when_cleanup_exception() -> None:
    """Primary test-body ошибка не маскируется cleanup exception."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)

    def _cleanup_raises(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if "down" in args:
            raise RuntimeError("cleanup down exploded")
        return _sync_run_happy_path(*args, **_kwargs)

    sync_run = MagicMock(side_effect=_cleanup_raises)
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        gen = setup_fn(request)
        next(gen)
        with pytest.raises(RuntimeError, match="test body boom"):
            gen.throw(RuntimeError("test body boom"))


@pytest.mark.unit
def test_test_body_exception_after_yield_calls_down() -> None:
    """Если test body упал после yield, fixture finally вызывает compose down."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    sync_run = MagicMock(side_effect=_sync_run_happy_path)

    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        gen = setup_fn(request)
        next(gen)
        with pytest.raises(RuntimeError, match="test body boom"):
            gen.throw(RuntimeError("test body boom"))
    assert _has_compose_down_call(sync_run)


@pytest.mark.unit
def test_generator_close_calls_down() -> None:
    """Закрытие generator fixture через close() приводит к compose down."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    sync_run = MagicMock(side_effect=_sync_run_happy_path)

    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        gen = setup_fn(request)
        next(gen)
        gen.close()
    assert _has_compose_down_call(sync_run)


@pytest.mark.unit
def test_keyboard_interrupt_after_compose_up_calls_down() -> None:
    """KeyboardInterrupt в setup path должен приводить к compose down."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    sync_run = MagicMock(side_effect=_sync_run_happy_path)

    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=KeyboardInterrupt()),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        with pytest.raises(KeyboardInterrupt):
            gen = setup_fn(request)
            next(gen)
    assert _has_compose_down_call(sync_run)


@pytest.mark.unit
def test_validation_error_before_docker_calls() -> None:
    """Validation error до Docker: detect/subprocess/engine не вызываются."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    preflight = MagicMock(return_value=["docker", "compose"])
    sync_run = MagicMock(side_effect=_sync_run_happy_path)
    create_engine = MagicMock()
    with (
        patch.dict(
            "os.environ",
            {**_SAFE_ENV, "DEV_TUNNELS_ENABLED": "true"},
            clear=False,
        ),
        patch.object(root_conftest, "_docker_compose_preflight_or_raise", preflight),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest, "_create_test_async_engine", create_engine),
    ):
        with pytest.raises(DestructiveTestDatabaseError, match="DEV_TUNNELS_ENABLED"):
            gen = setup_fn(request)
            next(gen)
    preflight.assert_not_called()
    sync_run.assert_not_called()
    create_engine.assert_not_called()


@pytest.mark.unit
def test_deterministic_safety_error_not_retried() -> None:
    """Deterministic safety error в init path не должен ретраиться."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    sync_run = MagicMock(side_effect=_sync_run_happy_path)
    create_engine = MagicMock(
        side_effect=DestructiveTestDatabaseError("safety deterministic fail")
    )
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest, "_create_test_async_engine", create_engine),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        with pytest.raises(DestructiveTestDatabaseError, match="deterministic"):
            gen = setup_fn(request)
            next(gen)
    assert create_engine.call_count == 1
    assert _has_compose_down_call(sync_run)


@pytest.mark.unit
def test_not_implemented_error_in_init_is_not_retried_and_cleanup_runs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """NotImplementedError fail-fast: no retry backoff, settle sleep допускается отдельно."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    sync_run = MagicMock(side_effect=_sync_run_happy_path)
    create_engine = MagicMock(
        side_effect=NotImplementedError("event loop sock_connect not implemented")
    )
    sleep_mock = MagicMock()
    retry_diag_mock = MagicMock(return_value="RETRY_DIAGNOSTIC_SENTINEL")

    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest, "_create_test_async_engine", create_engine),
        patch.object(root_conftest.time, "sleep", sleep_mock),
        patch.object(root_conftest, "_format_retry_diagnostic", retry_diag_mock),
        patch.object(root_conftest, "SETUP_DB_INIT_MAX_RETRIES", 5),
        patch.object(root_conftest, "SETUP_DB_SETTLE_SLEEP_SEC", 7),
    ):
        with pytest.raises(NotImplementedError, match="not implemented"):
            gen = setup_fn(request)
            next(gen)

    out = capsys.readouterr().out
    assert create_engine.call_count == 1
    assert sleep_mock.call_count == 1
    sleep_mock.assert_called_once_with(7)  # settle sleep only
    retry_diag_mock.assert_not_called()
    assert "RETRY_DIAGNOSTIC_SENTINEL" not in out
    assert _has_compose_down_call(sync_run)
    assert root_conftest._DOCKER_CLEANUP_STATE["container_id"] is None
    assert root_conftest._DOCKER_CLEANUP_STATE["compose_cmd"] is None
    assert root_conftest._TEST_DB_READY is False


@pytest.mark.unit
def test_cleanup_down_call_contains_flags_and_timeout() -> None:
    """Cleanup-команда обязана содержать down -v --remove-orphans и timeout=20."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    sync_run = MagicMock(side_effect=_sync_run_happy_path)

    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        gen = setup_fn(request)
        next(gen)
        gen.close()

    down_call = _get_compose_down_call(sync_run)
    assert down_call is not None
    argv = down_call.args
    assert "down" in argv
    assert "-v" in argv
    assert "--remove-orphans" in argv
    assert "--timeout" in argv
    assert "1" in argv
    assert down_call.kwargs.get("timeout") == 20


@pytest.mark.unit
def test_sanitizer_hides_url_password() -> None:
    """Санитайзер должен скрывать password в URL."""
    secret_url = "postgresql://SNTL_URL_USER_81f30:SNTL_URL_PASSWORD_a74c2@localhost:5432/db"
    text = f"context {secret_url} suffix"
    sanitized = root_conftest._scrub_sensitive_text(text)
    assert secret_url not in sanitized
    assert "SNTL_URL_USER_81f30:SNTL_URL_PASSWORD_a74c2@localhost:5432/db" not in sanitized
    assert "<redacted>" in sanitized
    assert "context" in sanitized
    assert "suffix" in sanitized


@pytest.mark.unit
def test_sanitizer_hides_assignments() -> None:
    """Санитайзер должен скрывать PASSWORD/TOKEN/API_KEY/DATABASE_URL."""
    password_secret = "SNTL_PASSWORD_9f3c712a"
    token_secret = "SNTL_TOKEN_128bd16e"
    api_key_secret = "SNTL_APIKEY_0d9e3ca1"
    db_url_secret = "postgresql://SNTL_DB_USER_2d8f:SNTL_DB_PASS_44ae@host/db"
    dsn_secret = "postgresql://SNTL_DSN_USER_f47a:SNTL_DSN_PASS_8c13@host/db"
    text = (
        f"context PASSWORD={password_secret} TOKEN={token_secret} API_KEY={api_key_secret} "
        f"DATABASE_URL={db_url_secret} DSN={dsn_secret} suffix"
    )
    sanitized = root_conftest._scrub_sensitive_text(text)
    assert password_secret not in sanitized
    assert token_secret not in sanitized
    assert api_key_secret not in sanitized
    assert db_url_secret not in sanitized
    assert dsn_secret not in sanitized
    assert "SNTL_DB_USER_2d8f:SNTL_DB_PASS_44ae@host/db" not in sanitized
    assert "SNTL_DSN_USER_f47a:SNTL_DSN_PASS_8c13@host/db" not in sanitized
    assert "context" in sanitized
    assert "suffix" in sanitized
    assert sanitized.count("<redacted>") >= 5


@pytest.mark.unit
def test_sanitizer_hides_cli_flags_and_authorization() -> None:
    """Санитайзер должен скрывать --password/--token и Authorization."""
    password_secret = "SNTL_PASSWORD_0ce8f3a1"
    token_secret = "SNTL_TOKEN_b3f8a29d"
    api_key_secret = "SNTL_APIKEY_6e4b7c10"
    command = (
        "docker",
        "login",
        "--password",
        password_secret,
        f"--token={token_secret}",
        "--api-key",
        api_key_secret,
    )
    safe_cmd = root_conftest._safe_command_repr(command)
    assert password_secret not in safe_cmd
    assert token_secret not in safe_cmd
    assert api_key_secret not in safe_cmd
    assert "<redacted>" in safe_cmd
    assert "docker" in safe_cmd
    assert "login" in safe_cmd

    bearer_secret = "SNTL_BEARER_4dc2f9a7"
    basic_secret = "SNTL_BASIC_8f71ac04"
    stderr = (
        f"context Authorization: Bearer {bearer_secret} and "
        f"Authorization: Basic {basic_secret} suffix"
    )
    safe_stderr = root_conftest._scrub_sensitive_text(stderr)
    assert bearer_secret not in safe_stderr
    assert basic_secret not in safe_stderr
    assert "Authorization: Bearer <redacted>" in safe_stderr
    assert "Authorization: Basic <redacted>" in safe_stderr
    assert "context" in safe_stderr
    assert "suffix" in safe_stderr


@pytest.mark.unit
def test_clickhouse_retry_diagnostic_is_sanitized_and_retried(capsys: pytest.CaptureFixture[str]) -> None:
    """Retry-диагностика ClickHouse должна редактировать секреты и сохранить контекст retry."""
    clickhouse_fn = _unwrap_fixture_function(root_conftest.clickhouse_client)
    request = _request_with_destructive_marker("clickhouse_client")

    class _Client:
        def __init__(self) -> None:
            self.command_calls = 0
            self.closed = False

        async def command(self, sql: str):
            self.command_calls += 1
            if self.command_calls == 1:
                raise RuntimeError(
                    "SNTL_CH_TOKEN_81f30 SNTL_CH_PASSWORD_a74c2 "
                    "DATABASE_URL='postgresql://sntl_user:sntl_pass@host/db' "
                    "Authorization:Bearer SNTL_CH_JWT_d49e1"
                )
            return "ok"

        def close(self) -> None:
            self.closed = True

    client = _Client()
    sleep_mock = AsyncMock(return_value=None)
    create_client_mock = AsyncMock(return_value=client)
    real_sync_run = MagicMock(side_effect=AssertionError("sync_run should not be used"))
    real_engine_factory = MagicMock(side_effect=AssertionError("engine should not be used"))

    async def _run_fixture() -> None:
        agen = clickhouse_fn(request, object())
        yielded = await agen.__anext__()
        assert yielded is client
        with pytest.raises(StopAsyncIteration):
            await agen.__anext__()

    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_require_destructive_local", MagicMock()),
        patch("tests.support.destructive_clickhouse.create_validated_async_clickhouse_client", create_client_mock),
        patch.object(root_conftest, "DatabaseError", RuntimeError),
        patch.object(root_conftest.asyncio, "sleep", sleep_mock),
        patch.object(root_conftest, "_sync_run", real_sync_run),
        patch.object(root_conftest, "_create_test_async_engine", real_engine_factory),
    ):
        asyncio.run(_run_fixture())

    output = capsys.readouterr().out
    assert "SNTL_CH_TOKEN_81f30" not in output
    assert "SNTL_CH_PASSWORD_a74c2" not in output
    assert "postgresql://sntl_user:sntl_pass@host/db" not in output
    assert "SNTL_CH_JWT_d49e1" not in output
    assert "<redacted>" in output
    assert "RuntimeError" in output
    assert "Retry 1/10 in 1s" in output
    assert sleep_mock.await_count == 2  # 1s retry + 5s post-ready
    sleep_mock.assert_any_await(1)
    sleep_mock.assert_any_await(5)
    assert client.closed is True
    real_sync_run.assert_not_called()
    real_engine_factory.assert_not_called()


@pytest.mark.unit
def test_primary_error_preserved_and_cleanup_warning_sanitized(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Primary ошибка должна сохраниться, cleanup warning — быть санитайзнутым и ограниченным."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    primary_marker = "SNTL_PRIMARY_MARKER_7ad21"
    cleanup_secret_token = "SNTL_CLEANUP_TOKEN_430ad"
    cleanup_secret_password = "SNTL_CLEANUP_PASSWORD_871bf"
    cleanup_secret_jwt = "SNTL_CLEANUP_JWT_51ae2"

    def _cleanup_non_zero_with_secrets(
        *args: str, **_kwargs: object
    ) -> tuple[int, str, str]:
        if "down" in args:
            noisy = (
                f"{cleanup_secret_token} --password {cleanup_secret_password} "
                f"Authorization:Bearer {cleanup_secret_jwt} " + ("Z" * 1200)
            )
            return 77, "", noisy
        return _sync_run_happy_path(*args, **_kwargs)

    sync_run = MagicMock(side_effect=_cleanup_non_zero_with_secrets)
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        gen = setup_fn(request)
        next(gen)
        with pytest.raises(RuntimeError, match=primary_marker):
            gen.throw(RuntimeError(f"primary failure {primary_marker}"))

    output = capsys.readouterr().out
    assert "Cleanup failure ignored due to primary exception" in output
    assert cleanup_secret_token not in output
    assert cleanup_secret_password not in output
    assert cleanup_secret_jwt not in output
    assert "<redacted>" in output
    assert "<truncated" in output
    warning_lines = [line for line in output.splitlines() if "Cleanup failure ignored" in line]
    assert warning_lines
    assert max(len(line) for line in warning_lines) <= 2200
    assert root_conftest._DOCKER_CLEANUP_STATE["container_id"] is None
    assert root_conftest._DOCKER_CLEANUP_STATE["compose_cmd"] is None
    assert root_conftest._TEST_DB_READY is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw_text", "forbidden_parts", "required_parts", "min_redacted_count"),
    [
        ("ctx --password SNTL_PASSWORD_9f3c712a tail", ["SNTL_PASSWORD_9f3c712a"], ["ctx", "tail"], 1),
        ("ctx --password=SNTL_PASSWORD_39ae82cd tail", ["SNTL_PASSWORD_39ae82cd"], ["ctx", "tail"], 1),
        ("ctx --PASSWORD SNTL_PASSWORD_1cb7db30 tail", ["SNTL_PASSWORD_1cb7db30"], ["ctx", "tail"], 1),
        ("ctx --token SNTL_TOKEN_88b3a20d tail", ["SNTL_TOKEN_88b3a20d"], ["ctx", "tail"], 1),
        ("ctx --token=SNTL_TOKEN_6ca95f0a tail", ["SNTL_TOKEN_6ca95f0a"], ["ctx", "tail"], 1),
        ("ctx --api-key SNTL_APIKEY_f7d45ca3 tail", ["SNTL_APIKEY_f7d45ca3"], ["ctx", "tail"], 1),
        ("ctx --api-key=SNTL_APIKEY_83d12f90 tail", ["SNTL_APIKEY_83d12f90"], ["ctx", "tail"], 1),
        ("ctx PASSWORD=SNTL_PASSWORD_554f7d10 tail", ["SNTL_PASSWORD_554f7d10"], ["ctx", "tail"], 1),
        ("ctx PASSWORD = SNTL_PASSWORD_08f7cc52 tail", ["SNTL_PASSWORD_08f7cc52"], ["ctx", "tail"], 1),
        ("ctx PASSWORD:'SNTL_PASSWORD_73deac66' tail", ["SNTL_PASSWORD_73deac66"], ["ctx", "tail"], 1),
        ('ctx PASS="SNTL_PASS_4a3d1b9c" tail', ["SNTL_PASS_4a3d1b9c"], ["ctx", "tail"], 1),
        ("ctx TOKEN=SNTL_TOKEN_726add57 tail", ["SNTL_TOKEN_726add57"], ["ctx", "tail"], 1),
        ('ctx TOKEN : "SNTL_TOKEN_f2ba49ed" tail', ["SNTL_TOKEN_f2ba49ed"], ["ctx", "tail"], 1),
        ('ctx TOKEN:"SNTL_TOKEN_28f31de7" tail', ["SNTL_TOKEN_28f31de7"], ["ctx", "tail"], 1),
        ("ctx SECRET=SNTL_SECRET_d6fca195 tail", ["SNTL_SECRET_d6fca195"], ["ctx", "tail"], 1),
        ("ctx API_KEY=SNTL_APIKEY_a4bd8f31 tail", ["SNTL_APIKEY_a4bd8f31"], ["ctx", "tail"], 1),
        ("ctx DATABASE_URL=SNTL_DBURL_314ac7b2 tail", ["SNTL_DBURL_314ac7b2"], ["ctx", "tail"], 1),
        (
            "ctx DATABASE_URL='postgresql://SNTL_DB_USER_5d8a:SNTL_DB_PASS_09e1@host/db' tail",
            [
                "postgresql://SNTL_DB_USER_5d8a:SNTL_DB_PASS_09e1@host/db",
                "SNTL_DB_USER_5d8a:SNTL_DB_PASS_09e1@host/db",
            ],
            ["ctx", "tail"],
            1,
        ),
        (
            'ctx DATABASE_URL="postgresql://SNTL_DB_USER_7f9c:SNTL_DB_PASS_3a2e@host/db" tail',
            [
                "postgresql://SNTL_DB_USER_7f9c:SNTL_DB_PASS_3a2e@host/db",
                "SNTL_DB_USER_7f9c:SNTL_DB_PASS_3a2e@host/db",
            ],
            ["ctx", "tail"],
            1,
        ),
        ("ctx DSN:SNTL_DSN_0cc5f48a tail", ["SNTL_DSN_0cc5f48a"], ["ctx", "tail"], 1),
        ("ctx Authorization: Bearer SNTL_AUTH_6a51bcb9 tail", ["SNTL_AUTH_6a51bcb9"], ["ctx", "tail"], 1),
        ("ctx Authorization:Bearer SNTL_AUTH_9d2ac80f tail", ["SNTL_AUTH_9d2ac80f"], ["ctx", "tail"], 1),
        ("ctx Authorization: Basic SNTL_AUTH_7b3ef908 tail", ["SNTL_AUTH_7b3ef908"], ["ctx", "tail"], 1),
        ("ctx Authorization:Basic SNTL_AUTH_450bc6e1 tail", ["SNTL_AUTH_450bc6e1"], ["ctx", "tail"], 1),
        (
            "ctx postgresql://SNTL_URL_USER_52e1:SNTL_URL_PASS_1d94@host/db tail",
            [
                "postgresql://SNTL_URL_USER_52e1:SNTL_URL_PASS_1d94@host/db",
                "SNTL_URL_USER_52e1:SNTL_URL_PASS_1d94@host/db",
            ],
            ["ctx", "tail"],
            2,
        ),
        ("ctx PASSWORD=", [], ["ctx", "PASSWORD=<redacted>"], 1),
        ("ctx TOKEN:", [], ["ctx", "TOKEN:<redacted>"], 1),
        ("ctx DSN =", [], ["ctx", "DSN=<redacted>"], 1),
        (
            "prefix TOKEN=SNTL_MULTI_TOKEN_55f9 DATABASE_URL='postgresql://SNTL_MULTI_USER_0e4a:SNTL_MULTI_PASS_8c1d@host/db' --password SNTL_MULTI_PASS_314e suffix",
            [
                "SNTL_MULTI_TOKEN_55f9",
                "SNTL_MULTI_PASS_314e",
                "postgresql://SNTL_MULTI_USER_0e4a:SNTL_MULTI_PASS_8c1d@host/db",
                "SNTL_MULTI_USER_0e4a:SNTL_MULTI_PASS_8c1d@host/db",
            ],
            ["prefix", "suffix"],
            3,
        ),
        ('ctx TOKEN:"SNTL_TOKEN_SPACE_4ec1 9ab3" tail', ["SNTL_TOKEN_SPACE_4ec1 9ab3"], ["ctx", "tail"], 1),
        ('ctx --token "SNTL_TOKEN_QUOTED_b31f c8dd" tail', ["SNTL_TOKEN_QUOTED_b31f c8dd"], ["ctx", "tail"], 1),
        (
            "ctx Authorization:Bearer SNTL_JWT_abc.def.ghi.7721 tail",
            ["SNTL_JWT_abc.def.ghi.7721"],
            ["ctx", "tail", "Authorization: Bearer <redacted>"],
            1,
        ),
    ],
    ids=[
        "flag-password-space",
        "flag-password-eq",
        "flag-password-uppercase",
        "flag-token-space",
        "flag-token-eq",
        "flag-api-key-space",
        "flag-api-key-eq",
        "password-assignment",
        "password-assignment-spaced",
        "password-colon-quoted",
        "pass-double-quoted",
        "token-assignment",
        "token-colon-quoted",
        "token-colon-spaced-quoted",
        "secret-assignment",
        "api-key-assignment",
        "database-url-assignment",
        "database-url-single-quoted",
        "database-url-double-quoted",
        "dsn-colon",
        "authorization-bearer-space",
        "authorization-bearer-nospace",
        "authorization-basic-space",
        "authorization-basic-nospace",
        "dsn-url-credentials",
        "password-empty",
        "token-empty",
        "dsn-empty-spaced",
        "compound-multiple-secrets",
        "token-colon-with-spaces-in-value",
        "flag-token-quoted-spaced-value",
        "authorization-bearer-jwt-like",
    ],
)
def test_sanitizer_required_bypass_vectors(
    raw_text: str,
    forbidden_parts: list[str],
    required_parts: list[str],
    min_redacted_count: int,
) -> None:
    """Обязательные bypass-векторы санитайзера должны редактироваться fail-closed."""
    sanitized = root_conftest._scrub_sensitive_text(raw_text)
    for forbidden in forbidden_parts:
        assert forbidden not in sanitized
    for marker in required_parts:
        assert marker in sanitized
    assert sanitized.count("<redacted>") >= min_redacted_count


@pytest.mark.unit
def test_sanitizer_truncates_stderr_length() -> None:
    """Санитайзер должен ограничивать длину stderr."""
    very_long = "X" * (root_conftest.DOCKER_DIAGNOSTIC_MAX_LEN + 200)
    exc = root_conftest._docker_stage_error(
        stage="health",
        command=("docker", "inspect"),
        exit_code=1,
        stderr=very_long,
        owner_action="check logs",
    )
    message = str(exc)
    assert "<truncated" in message


@pytest.mark.unit
def test_safe_error_text_contains_stage_exitcode_owner_action() -> None:
    """Безопасный текст ошибки сохраняет stage, exit code и owner action."""
    exc = root_conftest._docker_stage_error(
        stage="cleanup",
        command=("docker", "compose", "down"),
        exit_code=2,
        stderr="TOKEN=abc",
        owner_action="Run cleanup with docker compose down",
    )
    message = str(exc)
    assert "DOCKER_STAGE=cleanup" in message
    assert "exit_code=2" in message
    assert "owner_action=" in message
    assert "TOKEN=abc" not in message


@pytest.mark.unit
def test_destructive_teardown_warning_is_sanitized(capsys: pytest.CaptureFixture[str]) -> None:
    """Session teardown warning не должен содержать сырые секреты из stderr."""
    teardown_fn = _unwrap_fixture_function(root_conftest._destructive_db_session_teardown)
    secrets = ["secret", "topsecret", "pass", "opaque", "superkey"]
    stderr_text = (
        "TOKEN=secret TOKEN:\"topsecret\" postgresql://user:pass@host/db "
        "Authorization:Bearer opaque --api-key superkey"
    )

    def _sync_run_side_effect(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if "down" in args:
            return 9, "", stderr_text
        return 0, "", ""

    sync_run = MagicMock(side_effect=_sync_run_side_effect)
    real_subprocess_run = MagicMock(
        side_effect=AssertionError("real subprocess forbidden")
    )
    with (
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.subprocess, "run", real_subprocess_run),
    ):
        root_conftest._DOCKER_CLEANUP_STATE["container_id"] = None
        root_conftest._DOCKER_CLEANUP_STATE["compose_cmd"] = ["docker", "compose"]
        gen = teardown_fn(["docker", "compose"])
        next(gen)
        with pytest.raises(StopIteration):
            next(gen)

    output = capsys.readouterr().out
    for secret in secrets:
        assert secret not in output
    assert "rc=9" in output
    assert "compose down failed" in output
    assert "<redacted>" in output
    real_subprocess_run.assert_not_called()


@pytest.mark.unit
def test_retry_log_is_sanitized_and_keeps_retry_context(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Retry-log не должен печатать raw exception и обязан сохранять retry context."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    sync_run = MagicMock(side_effect=_sync_run_happy_path)
    sleep_mock = MagicMock()
    real_subprocess_run = MagicMock(
        side_effect=AssertionError("real subprocess forbidden")
    )
    create_engine = MagicMock(side_effect=AssertionError("engine forbidden"))
    first_error = RuntimeError(
        "TOKEN=SNTL_RETRY_TOKEN_4be12 DATABASE_URL='postgresql://SNTL_RETRY_USER_1af3:SNTL_RETRY_PASS_e2d9@host/db' "
        "Authorization:Bearer SNTL_RETRY_JWT_abc.def.9920 --password SNTL_RETRY_PASS_80cd"
    )
    run_calls = {"count": 0}

    def _asyncio_run_retry_then_success(coro):
        coro.close()
        if run_calls["count"] == 0:
            run_calls["count"] += 1
            raise first_error
        run_calls["count"] += 1
        return None

    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest, "_create_test_async_engine", create_engine),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_retry_then_success),
        patch.object(root_conftest.time, "sleep", sleep_mock),
        patch.object(root_conftest.subprocess, "run", real_subprocess_run),
        patch.object(root_conftest, "SETUP_DB_INIT_MAX_RETRIES", 2),
    ):
        gen = setup_fn(request)
        next(gen)
        gen.close()

    output = capsys.readouterr().out
    for secret in (
        "SNTL_RETRY_TOKEN_4be12",
        "SNTL_RETRY_PASS_80cd",
        "SNTL_RETRY_JWT_abc.def.9920",
        "postgresql://SNTL_RETRY_USER_1af3:SNTL_RETRY_PASS_e2d9@host/db",
        "SNTL_RETRY_USER_1af3:SNTL_RETRY_PASS_e2d9@host/db",
    ):
        assert secret not in output
    assert "<redacted>" in output
    assert "RuntimeError" in output
    assert "Retry 1/2 in 2s" in output
    assert sleep_mock.call_count >= 1
    sleep_mock.assert_any_call(2)
    real_subprocess_run.assert_not_called()
    create_engine.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clickhouse_retry_log_is_sanitized_and_client_closes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ClickHouse retry-log sanitizes sentinels and closes client in teardown."""
    clickhouse_fixture_fn = _unwrap_fixture_function(root_conftest.clickhouse_client)
    request = _request_with_destructive_marker("clickhouse_client")

    class _FakeClient:
        def __init__(self) -> None:
            self.calls = 0
            self.close = MagicMock()

        async def command(self, sql: str):
            self.calls += 1
            if self.calls == 1 and sql == "SELECT 1":
                raise root_conftest.DatabaseError(
                    "TOKEN=SNTL_CH_TOKEN_81f30 PASSWORD=SNTL_CH_PASSWORD_a74c2 "
                    "DATABASE_URL='postgresql://sntl_user:sntl_pass@host/db' "
                    "Authorization:Bearer SNTL_CH_JWT_d49e1"
                )
            return None

    fake_client = _FakeClient()
    sleep_mock = AsyncMock()
    real_subprocess_run = MagicMock(
        side_effect=AssertionError("real subprocess forbidden")
    )
    sync_run = MagicMock(side_effect=AssertionError("docker/subprocess forbidden"))
    create_engine = MagicMock(side_effect=AssertionError("engine forbidden"))

    module_path = "tests.support.destructive_clickhouse"
    with (
        patch.object(root_conftest, "_require_destructive_local", MagicMock()),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest, "_create_test_async_engine", create_engine),
        patch.object(root_conftest.subprocess, "run", real_subprocess_run),
        patch.object(root_conftest.asyncio, "sleep", sleep_mock),
        patch(f"{module_path}.create_validated_async_clickhouse_client", new=AsyncMock(return_value=fake_client)),
        patch(f"{module_path}.ALLOWED_CH_DATABASE", "test_adv_bot_clickhouse"),
    ):
        agen = clickhouse_fixture_fn(request, object())
        yielded = await agen.__anext__()
        assert yielded is fake_client
        with pytest.raises(StopAsyncIteration):
            await agen.__anext__()

    output = capsys.readouterr().out
    for secret in (
        "SNTL_CH_TOKEN_81f30",
        "SNTL_CH_PASSWORD_a74c2",
        "postgresql://sntl_user:sntl_pass@host/db",
        "sntl_user:sntl_pass@host/db",
        "SNTL_CH_JWT_d49e1",
    ):
        assert secret not in output
    assert "<redacted>" in output
    assert "DatabaseError" in output
    assert "Retry 1/10 in 1s" in output
    assert fake_client.close.call_count == 1
    sleep_mock.assert_any_await(1)
    sleep_mock.assert_any_await(5)
    assert sleep_mock.await_count == 2
    real_subprocess_run.assert_not_called()
    sync_run.assert_not_called()
    create_engine.assert_not_called()


@pytest.mark.unit
def test_primary_error_preserved_cleanup_warning_sanitized_and_truncated(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Primary exception survives; cleanup warning sanitized, truncated and state reset."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    primary_marker = "PRIMARY_MARKER_SAFE_5e12"
    long_tail = "X" * (root_conftest.DOCKER_DIAGNOSTIC_MAX_LEN + 300)
    cleanup_stderr = (
        "TOKEN=SNTL_CLEANUP_TOKEN_430ad --password SNTL_CLEANUP_PASSWORD_871bf "
        "Authorization:Bearer SNTL_CLEANUP_JWT_51ae2 "
        f"DATABASE_URL='postgresql://sntl_cleanup_user:sntl_cleanup_pass@host/db' {long_tail}"
    )

    def _cleanup_non_zero(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if "down" in args:
            return 9, "", cleanup_stderr
        return _sync_run_happy_path(*args, **_kwargs)

    sync_run = MagicMock(side_effect=_cleanup_non_zero)
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        gen = setup_fn(request)
        next(gen)
        with pytest.raises(RuntimeError, match=primary_marker):
            gen.throw(RuntimeError(primary_marker))

    output = capsys.readouterr().out
    assert "Cleanup failure ignored due to primary exception" in output
    assert "<redacted>" in output
    assert "<truncated" in output
    for secret in (
        "SNTL_CLEANUP_TOKEN_430ad",
        "SNTL_CLEANUP_PASSWORD_871bf",
        "SNTL_CLEANUP_JWT_51ae2",
        "postgresql://sntl_cleanup_user:sntl_cleanup_pass@host/db",
        "sntl_cleanup_user:sntl_cleanup_pass@host/db",
    ):
        assert secret not in output
    assert root_conftest._DOCKER_CLEANUP_STATE["container_id"] is None
    assert root_conftest._DOCKER_CLEANUP_STATE["compose_cmd"] is None
    assert root_conftest._TEST_DB_READY is False


@pytest.mark.unit
def test_no_raw_err_prints_in_docker_diagnostics() -> None:
    """Raw print(err)/print(str(exc)) запрещены для docker diagnostic outputs."""
    source = _ROOT_CONFTEST_PATH.read_text(encoding="utf-8")
    forbidden_patterns = [
        r"print\(\s*err\s*\)",
        r"print\(\s*err\.strip\(\)\s*\)",
        r"print\(\s*str\(exc\)\s*\)",
        r"print\(f[\"'][^\n]*\{err(?:\.strip\(\))?\}[^\n]*[\"']\)",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, source) is None


@pytest.mark.unit
def test_no_real_subprocess_calls_in_mock_tests() -> None:
    """Mock-only path не должен вызывать реальный subprocess.run."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    sync_run = MagicMock(side_effect=_sync_run_happy_path)
    real_subprocess_run = MagicMock(side_effect=AssertionError("real subprocess forbidden"))
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
        patch.object(root_conftest.subprocess, "run", real_subprocess_run),
    ):
        gen = setup_fn(request)
        next(gen)
        gen.close()
    real_subprocess_run.assert_not_called()


@pytest.mark.unit
def test_cleanup_timeout_state_reset_and_cleanup_error() -> None:
    """Timeout в down должен давать stage=cleanup и reset состояния."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)

    def _cleanup_timeout(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        if "down" in args:
            raise subprocess.TimeoutExpired(cmd="docker compose down", timeout=20)
        return _sync_run_happy_path(*args, **_kwargs)

    sync_run = MagicMock(side_effect=_cleanup_timeout)
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_sync_run", sync_run),
        patch.object(root_conftest.asyncio, "run", side_effect=_asyncio_run_mock_success),
        patch.object(root_conftest.time, "sleep", MagicMock()),
    ):
        gen = setup_fn(request)
        next(gen)
        with pytest.raises(RuntimeError, match=r"DOCKER_STAGE=cleanup.*exit_code=124"):
            gen.close()
    assert root_conftest._DOCKER_CLEANUP_STATE["container_id"] is None
    assert root_conftest._DOCKER_CLEANUP_STATE["compose_cmd"] is None
    assert root_conftest._TEST_DB_READY is False
