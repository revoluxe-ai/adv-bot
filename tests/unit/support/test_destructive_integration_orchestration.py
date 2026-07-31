"""Mock-only tests for destructive orchestration helpers in root conftest.

Сохраняет fail-closed sanitizer/diagnostic contracts и адаптирует setup/
ClickHouse fixtures к session-owned lifecycle (compose down не на function close).
"""

from __future__ import annotations

import asyncio
import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.support.destructive_lifecycle import TestInfraSessionState, TestResourceNeeds
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
    "ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE": "1",
    "DEV_TUNNELS_ENABLED": "false",
    "DEV_TUNNELS_KUBECONFIG": "",
    "DEV_TUNNEL_PG_LOCAL_PORT": "",
    "DEV_TUNNEL_CH_HTTP_PORT": "",
}


def _unwrap_fixture_function(func: object):
    return getattr(func, "__wrapped__", func)


def _request_with_destructive_marker(fixturename: str) -> pytest.FixtureRequest:
    class _Marker:
        pass

    class _Node:
        keywords: dict[str, object] = {"destructive_local": True}

        def get_closest_marker(self, name: str):
            return _Marker() if name == "destructive_local" else None

    return SimpleNamespace(fixturename=fixturename, node=_Node())  # type: ignore[return-value]


def _mock_lifecycle(**overrides):
    """Minimal lifecycle mock for function-fixture unit tests."""
    state = TestInfraSessionState()
    lc = MagicMock()
    lc.state = state
    lc._compose_cmd = ["docker", "compose"]
    lc.ensure_resources = MagicMock()
    lc.record_pg_data_reset = MagicMock()
    lc.record_ch_data_reset = MagicMock()
    lc.teardown = MagicMock()
    for k, v in overrides.items():
        setattr(lc, k, v)
    return lc


# ---------------------------------------------------------------------------
# setup_test_database (thin gated entrypoint)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_setup_delegates_to_lifecycle_after_validation() -> None:
    """Marker+DSN OK → ensure_resources(PG); no compose down on fixture close."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    lc = _mock_lifecycle()
    sync_run = MagicMock(side_effect=AssertionError("sync_run must not be called here"))
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_resolve_test_infra_lifecycle", MagicMock(return_value=lc)),
        patch.object(root_conftest, "_sync_run", sync_run),
    ):
        gen = setup_fn(request)
        next(gen)
        gen.close()
    lc.ensure_resources.assert_called_once_with(TestResourceNeeds(needs_pg=True))
    sync_run.assert_not_called()


@pytest.mark.unit
def test_validation_error_before_lifecycle_resolve() -> None:
    """Tunnel/DSN error до resolve lifecycle и docker."""
    request = _request_with_destructive_marker("setup_test_database")
    setup_fn = _unwrap_fixture_function(root_conftest.setup_test_database)
    resolve = MagicMock()
    with (
        patch.dict(
            "os.environ",
            {**_SAFE_ENV, "DEV_TUNNELS_ENABLED": "true"},
            clear=False,
        ),
        patch.object(root_conftest, "_resolve_test_infra_lifecycle", resolve),
    ):
        with pytest.raises(DestructiveTestDatabaseError, match="DEV_TUNNELS_ENABLED"):
            gen = setup_fn(request)
            next(gen)
    resolve.assert_not_called()


@pytest.mark.unit
def test_session_lifecycle_teardown_calls_compose_down_once() -> None:
    """Session fixture teardown → lifecycle.teardown once."""
    teardown_fn = _unwrap_fixture_function(root_conftest._test_infra_lifecycle)
    built = _mock_lifecycle()
    with patch.object(root_conftest, "_build_test_infra_lifecycle", MagicMock(return_value=built)):
        gen = teardown_fn()
        next(gen)
        with pytest.raises(StopIteration):
            next(gen)
    built.teardown.assert_called_once()


@pytest.mark.unit
def test_session_lifecycle_preserves_primary_on_teardown_error() -> None:
    """Primary exception из session body передаётся в teardown."""
    teardown_fn = _unwrap_fixture_function(root_conftest._test_infra_lifecycle)
    built = _mock_lifecycle()
    with patch.object(root_conftest, "_build_test_infra_lifecycle", MagicMock(return_value=built)):
        gen = teardown_fn()
        next(gen)
        with pytest.raises(RuntimeError, match="session boom"):
            gen.throw(RuntimeError("session boom"))
    kwargs = built.teardown.call_args.kwargs
    assert isinstance(kwargs.get("primary_exception"), RuntimeError)


# ---------------------------------------------------------------------------
# ClickHouse fixture (no PG dependency, no fixed 5s sleep)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clickhouse_retry_log_is_sanitized_and_client_closes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ClickHouse retry-log sanitizes sentinels and closes client in teardown."""
    clickhouse_fixture_fn = _unwrap_fixture_function(root_conftest.clickhouse_client)
    request = _request_with_destructive_marker("clickhouse_client")
    lc = _mock_lifecycle()
    lc.state.clickhouse_schema_initialized = True

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
    module_path = "tests.support.destructive_clickhouse"
    reset_mock = AsyncMock()
    with (
        patch.dict("os.environ", dict(_SAFE_ENV), clear=False),
        patch.object(root_conftest, "_validate_ch_preflight", MagicMock()),
        patch.object(
            root_conftest, "_resolve_test_infra_lifecycle", MagicMock(return_value=lc)
        ),
        patch.object(root_conftest.asyncio, "sleep", sleep_mock),
        patch(
            f"{module_path}.create_validated_async_clickhouse_client",
            new=AsyncMock(return_value=fake_client),
        ),
        patch(
            "tests.support.destructive_ch_reset.reset_clickhouse_test_data",
            new=reset_mock,
        ),
    ):
        agen = clickhouse_fixture_fn(request)
        yielded = await agen.__anext__()
        assert yielded is fake_client
        with pytest.raises(StopAsyncIteration):
            await agen.__anext__()

    output = capsys.readouterr().out
    for secret in (
        "SNTL_CH_TOKEN_81f30",
        "SNTL_CH_PASSWORD_a74c2",
        "postgresql://sntl_user:sntl_pass@host/db",
        "SNTL_CH_JWT_d49e1",
    ):
        assert secret not in output
    assert "<redacted>" in output
    assert "Retry 1/10 in 1s" in output
    assert fake_client.close.call_count == 1
    sleep_mock.assert_any_await(1)
    # no mandatory 5s settle sleep
    assert all(c.args[0] != 5 for c in sleep_mock.await_args_list)
    reset_mock.assert_awaited_once()
    lc.record_ch_data_reset.assert_called_once()


# ---------------------------------------------------------------------------
# Sanitizers / diagnostics (unchanged contracts)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sanitizer_hides_url_password() -> None:
    secret_url = "postgresql://SNTL_URL_USER_81f30:SNTL_URL_PASSWORD_a74c2@localhost:5432/db"
    text = f"context {secret_url} suffix"
    sanitized = root_conftest._scrub_sensitive_text(text)
    assert secret_url not in sanitized
    assert "<redacted>" in sanitized


@pytest.mark.unit
def test_sanitizer_hides_assignments() -> None:
    password_secret = "SNTL_PASSWORD_9f3c712a"
    token_secret = "SNTL_TOKEN_128bd16e"
    api_key_secret = "SNTL_APIKEY_0d9e3ca1"
    text = (
        f"context PASSWORD={password_secret} TOKEN={token_secret} "
        f"API_KEY={api_key_secret} suffix"
    )
    sanitized = root_conftest._scrub_sensitive_text(text)
    assert password_secret not in sanitized
    assert token_secret not in sanitized
    assert api_key_secret not in sanitized
    assert sanitized.count("<redacted>") >= 3


@pytest.mark.unit
def test_sanitizer_hides_cli_flags_and_authorization() -> None:
    password_secret = "SNTL_PASSWORD_0ce8f3a1"
    token_secret = "SNTL_TOKEN_b3f8a29d"
    command = ("docker", "login", "--password", password_secret, f"--token={token_secret}")
    safe_cmd = root_conftest._safe_command_repr(command)
    assert password_secret not in safe_cmd
    assert token_secret not in safe_cmd
    bearer_secret = "SNTL_BEARER_4dc2f9a7"
    safe_stderr = root_conftest._scrub_sensitive_text(
        f"Authorization: Bearer {bearer_secret}"
    )
    assert bearer_secret not in safe_stderr
    assert "Authorization: Bearer <redacted>" in safe_stderr


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw_text", "forbidden_parts", "required_parts", "min_redacted_count"),
    [
        ("ctx --password SNTL_PASSWORD_9f3c712a tail", ["SNTL_PASSWORD_9f3c712a"], ["ctx", "tail"], 1),
        ("ctx PASSWORD=SNTL_PASSWORD_554f7d10 tail", ["SNTL_PASSWORD_554f7d10"], ["ctx", "tail"], 1),
        ("ctx TOKEN=SNTL_TOKEN_726add57 tail", ["SNTL_TOKEN_726add57"], ["ctx", "tail"], 1),
        (
            "ctx postgresql://SNTL_URL_USER_52e1:SNTL_URL_PASS_1d94@host/db tail",
            ["SNTL_URL_USER_52e1:SNTL_URL_PASS_1d94@host/db"],
            ["ctx", "tail"],
            1,
        ),
        ("ctx Authorization: Bearer SNTL_AUTH_6a51bcb9 tail", ["SNTL_AUTH_6a51bcb9"], ["ctx", "tail"], 1),
    ],
)
def test_sanitizer_required_bypass_vectors(
    raw_text: str,
    forbidden_parts: list[str],
    required_parts: list[str],
    min_redacted_count: int,
) -> None:
    sanitized = root_conftest._scrub_sensitive_text(raw_text)
    for forbidden in forbidden_parts:
        assert forbidden not in sanitized
    for marker in required_parts:
        assert marker in sanitized
    assert sanitized.count("<redacted>") >= min_redacted_count


@pytest.mark.unit
def test_sanitizer_truncates_stderr_length() -> None:
    very_long = "X" * (root_conftest.DOCKER_DIAGNOSTIC_MAX_LEN + 200)
    exc = root_conftest._docker_stage_error(
        stage="health",
        command=("docker", "inspect"),
        exit_code=1,
        stderr=very_long,
        owner_action="check logs",
    )
    assert "<truncated" in str(exc)


@pytest.mark.unit
def test_scrub_sensitive_text_accepts_none_and_magicmock() -> None:
    """Non-str stderr (suite MagicMock leak) → empty, без TypeError в re.sub."""
    from unittest.mock import MagicMock

    assert root_conftest._scrub_sensitive_text(None) == ""
    assert root_conftest._scrub_sensitive_text(MagicMock()) == ""
    assert root_conftest._coerce_diagnostic_text(MagicMock()) == ""
    assert root_conftest._coerce_diagnostic_text(b"plain") == "plain"


@pytest.mark.unit
def test_docker_stage_error_with_magicmock_stderr_does_not_typeerror() -> None:
    """Teardown path: MagicMock stderr → RuntimeError diagnostics, not TypeError."""
    from unittest.mock import MagicMock

    exc = root_conftest._docker_stage_error(
        stage="cleanup",
        command=("docker", "compose", "down"),
        exit_code=1,
        stderr=MagicMock(),
        owner_action="retry cleanup",
    )
    message = str(exc)
    assert "DOCKER_STAGE=cleanup" in message
    assert "exit_code=1" in message
    assert "stderr=<empty>" in message


@pytest.mark.unit
def test_compose_down_coerces_magicmock_stderr_before_raise() -> None:
    """_compose_down передаёт str в raise_docker_stage даже при MagicMock err."""
    from unittest.mock import MagicMock

    from tests.support.destructive_lifecycle import coerce_compose_stream
    from tests.unit.support.test_destructive_lifecycle import _lifecycle

    captured: dict[str, object] = {}

    def _raise_stage(**kwargs: object) -> None:
        captured.update(kwargs)
        raise RuntimeError("stage")

    def _sync_run(*_a: object, **_k: object) -> tuple[int, str, object]:
        return 1, "", MagicMock(name="fake_stderr")

    lc = _lifecycle(sync_run=_sync_run, raise_stage=_raise_stage)
    lc._compose_cmd = ["docker", "compose"]
    err = lc._compose_down()
    assert isinstance(err, RuntimeError)
    assert captured.get("stderr") == ""
    assert coerce_compose_stream(MagicMock()) == ""


@pytest.mark.unit
def test_compose_down_skips_raise_on_magicmock_returncode() -> None:
    """MagicMock returncode (subprocess.run leak) → warning, не DOCKER_STAGE ERROR.

    Victim-паттерн pytest-full: session teardown compose down видит
    ``exit_code=<MagicMock name='mock().returncode'>`` и ERROR на последнем
    тесте (graphic_positions DTO) хотя DTO Docker не использует.
    """
    from unittest.mock import MagicMock

    from tests.support.destructive_lifecycle import coerce_compose_exit_code
    from tests.unit.support.test_destructive_lifecycle import _lifecycle

    raise_calls: list[dict[str, object]] = []

    def _raise_stage(**kwargs: object) -> None:
        raise_calls.append(kwargs)
        raise RuntimeError("stage")

    polluted_rc = MagicMock(name="mock().returncode")

    def _sync_run(*_a: object, **_k: object) -> tuple[object, str, str]:
        return polluted_rc, "", ""

    lc = _lifecycle(sync_run=_sync_run, raise_stage=_raise_stage)
    lc._compose_cmd = ["docker", "compose"]
    err = lc._compose_down()
    assert err is None
    assert raise_calls == []
    assert coerce_compose_exit_code(polluted_rc) is None
    assert coerce_compose_exit_code(0) == 0
    assert coerce_compose_exit_code(2) == 2


@pytest.mark.unit
def test_safe_error_text_contains_stage_exitcode_owner_action() -> None:
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
def test_no_raw_err_prints_in_docker_diagnostics() -> None:
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
def test_format_retry_diagnostic_sanitizes() -> None:
    msg = root_conftest._format_retry_diagnostic(
        operation="Test DB init",
        error=RuntimeError("TOKEN=SNTL_RETRY_TOKEN_4be12"),
        attempt=1,
        max_attempts=2,
        backoff_sec=2,
    )
    assert "SNTL_RETRY_TOKEN_4be12" not in msg
    assert "Retry 1/2 in 2s" in msg
    assert "<redacted>" in msg
