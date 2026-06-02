"""Unit-тесты менеджера kubectl port-forward (без реального кластера)."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

import app.dev_local.k8s_tunnels as k8s_tunnels
from app.settings.settings_master import Settings


@pytest.fixture(autouse=True)
def _reset_monitor_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сбрасывает глобальное состояние между тестами."""
    monkeypatch.setenv("DEV_TUNNELS_ENABLED", "true")
    k8s_tunnels._monitor_started = False
    k8s_tunnels._cleanup_registered = False
    k8s_tunnels._processes_by_name = {}
    k8s_tunnels._consecutive_restart_failures = {}
    k8s_tunnels._tunnel_ok_logged = set()
    k8s_tunnels._last_repair_monotonic = {}
    for spec in k8s_tunnels._tunnel_specs():
        k8s_tunnels._release_repair_lock(spec)
    k8s_tunnels._repair_lock_files = {}
    yield
    k8s_tunnels._stop_owned_tunnels()
    k8s_tunnels._monitor_started = False
    k8s_tunnels._cleanup_registered = False
    k8s_tunnels._processes_by_name = {}
    k8s_tunnels._consecutive_restart_failures = {}
    k8s_tunnels._tunnel_ok_logged = set()
    k8s_tunnels._last_repair_monotonic = {}
    for spec in k8s_tunnels._tunnel_specs():
        k8s_tunnels._release_repair_lock(spec)
    k8s_tunnels._repair_lock_files = {}


def test_tcp_port_open_success() -> None:
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)
    with patch("app.dev_local.k8s_tunnels.socket.create_connection", return_value=mock_sock):
        assert k8s_tunnels._tcp_port_open("127.0.0.1", 15432) is True


def test_tcp_port_open_failure() -> None:
    with patch(
        "app.dev_local.k8s_tunnels.socket.create_connection",
        side_effect=OSError("connection refused"),
    ):
        assert k8s_tunnels._tcp_port_open("127.0.0.1", 15432) is False


def test_start_dev_tunnels_skipped_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без DEV_TUNNELS_ENABLED приложение не трогает kubectl."""
    monkeypatch.setenv("DEV_TUNNELS_ENABLED", "false")
    with patch.object(k8s_tunnels.threading, "Thread") as mock_thread:
        k8s_tunnels.start_dev_tunnels_monitor(wait_ready=False)
    mock_thread.assert_not_called()
    assert k8s_tunnels._monitor_started is False


def test_start_missing_kubeconfig_leaves_monitor_not_started() -> None:
    with (
        patch.object(k8s_tunnels.Path, "is_file", return_value=False),
        patch.object(k8s_tunnels.threading, "Thread") as mock_thread,
    ):
        k8s_tunnels._monitor_started = False
        with pytest.raises(FileNotFoundError, match="Kubeconfig not found"):
            k8s_tunnels.start_dev_tunnels_monitor(wait_ready=False)

    assert k8s_tunnels._monitor_started is False
    mock_thread.assert_not_called()


def test_already_started_waits_outside_monitor_lock() -> None:
    """Повторный start с wait_ready не держит _monitor_lock на время poll/sleep."""
    lock_held_during_wait: bool | None = None

    def _wait_stub(*, specs: list) -> None:
        nonlocal lock_held_during_wait
        lock_held_during_wait = k8s_tunnels._monitor_lock.locked()

    k8s_tunnels._monitor_started = True
    with patch.object(k8s_tunnels, "wait_for_dev_tunnels_ready", side_effect=_wait_stub):
        k8s_tunnels.start_dev_tunnels_monitor(wait_ready=True)

    assert lock_held_during_wait is False


def test_start_dev_tunnels_monitor_idempotent() -> None:
    mock_thread_instance = MagicMock()

    with (
        patch.object(k8s_tunnels.Path, "is_file", return_value=True),
        patch.object(k8s_tunnels, "_ports_ready", return_value=False),
        patch.object(k8s_tunnels.threading, "Thread", return_value=mock_thread_instance) as mock_thread_cls,
        patch.object(k8s_tunnels, "_register_cleanup_once") as mock_cleanup,
    ):
        k8s_tunnels._monitor_started = False
        k8s_tunnels.start_dev_tunnels_monitor(wait_ready=False)
        k8s_tunnels.start_dev_tunnels_monitor(wait_ready=False)

    mock_thread_cls.assert_called_once()
    mock_thread_instance.start.assert_called_once()
    mock_cleanup.assert_called_once()


def test_tunnel_port_ready_dead_process() -> None:
    proc = MagicMock()
    proc.poll.return_value = 1
    spec = k8s_tunnels._tunnel_specs()[0]
    runtime = k8s_tunnels._TunnelRuntime(proc=proc, external=False)
    with patch.object(k8s_tunnels, "_tunnel_probe_ready", return_value=True):
        assert k8s_tunnels._tunnel_port_ready(runtime, spec) is False


@pytest.mark.unit
def test_tunnel_port_ready_stuck_kubectl_port_closed() -> None:
    """Живой kubectl без TCP на probe_port — нездоров, monitor должен перезапустить."""
    proc = MagicMock()
    proc.poll.return_value = None
    spec = k8s_tunnels._tunnel_specs()[0]
    runtime = k8s_tunnels._TunnelRuntime(proc=proc, external=False)
    with patch.object(k8s_tunnels, "_tunnel_probe_ready", return_value=False):
        assert k8s_tunnels._tunnel_port_ready(runtime, spec) is False


@pytest.mark.unit
def test_tunnel_probe_ready_is_tcp_only_for_clickhouse() -> None:
    """Tunnel ready = TCP (kubectl слушает); HTTP smoke — отдельная проверка."""
    ch_spec = k8s_tunnels._tunnel_specs()[1]
    with patch.object(k8s_tunnels, "_tcp_port_open", return_value=True):
        assert k8s_tunnels._tunnel_probe_ready(ch_spec) is True

    with patch.object(k8s_tunnels, "_tcp_port_open", return_value=False):
        assert k8s_tunnels._tunnel_probe_ready(ch_spec) is False


@pytest.mark.unit
def test_clickhouse_http_healthy_separate_from_probe() -> None:
    """HTTP health проверяется отдельно, не блокирует tunnel ready."""
    with patch.object(k8s_tunnels, "_clickhouse_http_select_1", side_effect=OSError("timeout")):
        assert k8s_tunnels._clickhouse_http_healthy(18123) is False

    with patch.object(k8s_tunnels, "_clickhouse_http_select_1"):
        assert k8s_tunnels._clickhouse_http_healthy(18123) is True


@pytest.mark.unit
def test_start_tunnel_kills_matching_stale_kubectl() -> None:
    spec = k8s_tunnels._tunnel_specs()[1]
    with (
        patch.object(k8s_tunnels, "_tunnel_probe_ready", return_value=False),
        patch.object(k8s_tunnels, "_force_free_local_port", return_value=True) as force_free,
        patch.object(k8s_tunnels, "_port_bindable", return_value=True),
        patch.object(k8s_tunnels, "_port_is_free", return_value=True),
        patch.object(k8s_tunnels, "_start_port_forward") as start_pf,
    ):
        proc = MagicMock(pid=5555)
        proc.poll.return_value = None
        start_pf.return_value = proc
        k8s_tunnels._repair_broken_tunnel(spec, "kubeconfig.yaml")

    force_free.assert_called_once()
    start_pf.assert_called_once()


@pytest.mark.unit
def test_try_reuse_healthy_forward_does_not_kill() -> None:
    spec = k8s_tunnels._tunnel_specs()[1]
    with (
        patch.object(k8s_tunnels, "_tunnel_probe_ready", return_value=True),
        patch.object(k8s_tunnels, "_clear_broken_tunnel_listeners") as clear,
        patch.object(k8s_tunnels, "_start_port_forward") as start_pf,
    ):
        assert k8s_tunnels._try_reuse_healthy_forward(spec) is True
    clear.assert_not_called()
    start_pf.assert_not_called()
    runtime = k8s_tunnels._processes_by_name[spec.name]
    assert runtime.external is True


@pytest.mark.unit
def test_start_tunnel_refuses_foreign_listener() -> None:
    spec = k8s_tunnels._tunnel_specs()[0]  # postgres - no fallback logic
    with (
        patch.object(k8s_tunnels, "_tunnel_probe_ready", return_value=False),
        patch.object(k8s_tunnels, "_all_listener_pids", return_value=[9999]),
        patch.object(k8s_tunnels, "_is_matching_kubectl_port_forward", return_value=False),
        patch.object(k8s_tunnels, "_process_cmdline", return_value="python -m http.server 15432"),
        patch.object(k8s_tunnels, "_find_matching_kubectl_pids", return_value=[]),
    ):
        with pytest.raises(RuntimeError, match="not matching kubectl"):
            k8s_tunnels._repair_broken_tunnel(spec, "kubeconfig.yaml")


@pytest.mark.unit
def test_start_tunnel_skips_new_kubectl_if_port_still_open() -> None:
    spec = k8s_tunnels._tunnel_specs()[1]
    with (
        patch.object(k8s_tunnels, "_tunnel_probe_ready", return_value=False),
        patch.object(k8s_tunnels, "_clear_broken_tunnel_listeners"),
        patch.object(k8s_tunnels, "_port_bindable", return_value=True),
        patch.object(k8s_tunnels, "_port_is_free", return_value=False),
        patch.object(k8s_tunnels, "_start_port_forward") as start_pf,
    ):
        result = k8s_tunnels._repair_broken_tunnel(spec, "kubeconfig.yaml")
    assert result is None
    start_pf.assert_not_called()


@pytest.mark.unit
def test_clickhouse_falls_back_to_free_local_port(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = k8s_tunnels._tunnel_specs()[1]
    monkeypatch.setenv("RUN_LOCAL", "true")
    with (
        patch.object(k8s_tunnels, "_tunnel_probe_ready", return_value=False),
        patch.object(k8s_tunnels, "_clear_broken_tunnel_listeners"),
        patch.object(k8s_tunnels, "_port_bindable", return_value=False),
        patch.object(k8s_tunnels, "_port_is_free", return_value=True),
        patch.object(k8s_tunnels, "_select_clickhouse_fallback_port", return_value=28123),
        patch.object(k8s_tunnels, "_start_port_forward") as start_pf,
    ):
        proc = MagicMock(pid=5555)
        proc.poll.return_value = None
        start_pf.return_value = proc
        result = k8s_tunnels._repair_broken_tunnel(spec, "kubeconfig.yaml")

    assert result is proc
    assert spec.probe_port == 28123
    assert spec.local_ports[0] == 28123
    assert k8s_tunnels.os.environ["CLICKHOUSE_PORT"] == "28123"


@pytest.mark.unit
def test_repair_skips_when_lock_busy() -> None:
    spec = k8s_tunnels._tunnel_specs()[1]
    with (
        patch.object(k8s_tunnels, "_acquire_repair_lock", return_value=False),
        patch.object(k8s_tunnels, "_start_port_forward") as start_pf,
    ):
        result = k8s_tunnels._repair_broken_tunnel(spec, "kubeconfig.yaml")
    assert result is None
    start_pf.assert_not_called()


def test_ports_ready_waits_outside_monitor_lock() -> None:
    """Первый start при уже открытых портах не держит lock на время wait_ready."""
    lock_held_during_wait: bool | None = None

    def _wait_stub(*, specs: list) -> None:
        nonlocal lock_held_during_wait
        lock_held_during_wait = k8s_tunnels._monitor_lock.locked()

    with (
        patch.object(k8s_tunnels.Path, "is_file", return_value=True),
        patch.object(k8s_tunnels, "_ports_ready", return_value=True),
        patch.object(k8s_tunnels, "_try_reuse_healthy_forward", return_value=True),
        patch.object(k8s_tunnels, "wait_for_dev_tunnels_ready", side_effect=_wait_stub),
        patch.object(k8s_tunnels.threading, "Thread"),
        patch.object(k8s_tunnels, "_register_cleanup_once"),
    ):
        k8s_tunnels._monitor_started = False
        k8s_tunnels.start_dev_tunnels_monitor(wait_ready=True)

    assert lock_held_during_wait is False


def test_start_reuse_monitor_when_ports_already_open() -> None:
    """При готовых портах — reuse monitor (bootstrap=False), без нового kubectl."""
    specs = k8s_tunnels._tunnel_specs()

    with (
        patch.object(k8s_tunnels.Path, "is_file", return_value=True),
        patch.object(k8s_tunnels, "_ports_ready", return_value=True),
        patch.object(k8s_tunnels, "_try_reuse_healthy_forward", return_value=True) as reuse,
        patch.object(k8s_tunnels.threading, "Thread") as mock_thread,
        patch.object(k8s_tunnels, "_register_cleanup_once"),
    ):
        k8s_tunnels._monitor_started = False
        k8s_tunnels.start_dev_tunnels_monitor(wait_ready=False)

    mock_thread.assert_called_once()
    assert mock_thread.call_args.kwargs.get("kwargs") == {"bootstrap": False}
    assert reuse.call_count == len(specs)


@pytest.mark.unit
def test_try_reuse_keeps_healthy_owned_kubectl() -> None:
    """Здоровый owned forward другого/этого процесса не останавливается."""
    spec = k8s_tunnels._tunnel_specs()[0]
    proc = MagicMock()
    proc.poll.return_value = None
    proc.pid = 1234
    k8s_tunnels._processes_by_name[spec.name] = k8s_tunnels._TunnelRuntime(
        proc=proc,
        external=False,
    )
    with (
        patch.object(k8s_tunnels, "_tunnel_probe_ready", return_value=True),
        patch.object(k8s_tunnels, "_terminate_process") as terminate,
    ):
        assert k8s_tunnels._try_reuse_healthy_forward(spec) is True
    terminate.assert_not_called()
    runtime = k8s_tunnels._processes_by_name[spec.name]
    assert runtime.external is False
    assert runtime.proc is proc


def test_postgres_tunnel_uses_pooler_service_by_default() -> None:
    spec = k8s_tunnels._tunnel_specs()[0]
    assert spec.resource == "svc/postgres-db-pooler"


def test_wait_for_ready_runs_postgres_smoke_check() -> None:
    specs = k8s_tunnels._tunnel_specs()
    with (
        patch.object(k8s_tunnels, "_ports_ready", return_value=True),
        patch.object(k8s_tunnels, "_postgres_select_1_smoke_check") as pg_smoke,
        patch.object(k8s_tunnels, "_clickhouse_select_1_smoke_check") as ch_smoke,
    ):
        k8s_tunnels.wait_for_dev_tunnels_ready(timeout_sec=1, specs=specs)
    pg_smoke.assert_called_once_with(specs)
    ch_smoke.assert_called_once_with(specs)


def test_postgres_smoke_error_non_strict_only_logs_warning() -> None:
    specs = k8s_tunnels._tunnel_specs()
    fake_psycopg = types.SimpleNamespace(connect=MagicMock(side_effect=RuntimeError("too many clients")))
    with (
        patch.dict(
            "os.environ",
            {
                "POSTGRES_DBNAME": "db",
                "POSTGRES_USER": "user",
                "POSTGRES_PASSWORD": "pwd",
                "DEV_TUNNEL_PG_SMOKE_STRICT": "false",
            },
            clear=False,
        ),
        patch.object(k8s_tunnels, "logger") as logger_mock,
        patch.dict("sys.modules", {"psycopg": fake_psycopg}, clear=False),
    ):
        k8s_tunnels._postgres_select_1_smoke_check(specs)
    logger_mock.warning.assert_called()


def test_postgres_smoke_error_strict_raises_timeout() -> None:
    specs = k8s_tunnels._tunnel_specs()
    fake_psycopg = types.SimpleNamespace(connect=MagicMock(side_effect=RuntimeError("too many clients")))
    with (
        patch.dict(
            "os.environ",
            {
                "POSTGRES_DBNAME": "db",
                "POSTGRES_USER": "user",
                "POSTGRES_PASSWORD": "pwd",
                "DEV_TUNNEL_PG_SMOKE_STRICT": "true",
            },
            clear=False,
        ),
        patch.dict("sys.modules", {"psycopg": fake_psycopg}, clear=False),
    ):
        with pytest.raises(TimeoutError, match="Postgres smoke SELECT 1 failed"):
            k8s_tunnels._postgres_select_1_smoke_check(specs)


def test_settings_run_local_default_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RUN_LOCAL", raising=False)
    assert Settings().run_local is False


def test_settings_run_local_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_LOCAL", "true")
    assert Settings().run_local is True


@pytest.mark.unit
def test_shutdown_signal_handler_sigint_raises_keyboard_interrupt() -> None:
    import signal

    with (
        patch.object(k8s_tunnels, "_stop_owned_tunnels") as mock_stop,
        pytest.raises(KeyboardInterrupt),
    ):
        k8s_tunnels._shutdown_signal_handler(signal.SIGINT, None)

    mock_stop.assert_called_once_with(reason="signal 2")


@pytest.mark.unit
def test_shutdown_signal_handler_sigterm_raises_system_exit() -> None:
    import signal

    with (
        patch.object(k8s_tunnels, "_stop_owned_tunnels") as mock_stop,
        pytest.raises(SystemExit) as exc_info,
    ):
        k8s_tunnels._shutdown_signal_handler(signal.SIGTERM, None)

    mock_stop.assert_called_once_with(reason=f"signal {signal.SIGTERM}")
    assert exc_info.value.code == 128 + signal.SIGTERM
