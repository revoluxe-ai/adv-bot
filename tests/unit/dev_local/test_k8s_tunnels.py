"""Unit-тесты менеджера kubectl port-forward (без реального кластера)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import app.dev_local.k8s_tunnels as k8s_tunnels
from app.settings.settings_master import Settings


@pytest.fixture(autouse=True)
def _reset_monitor_state() -> None:
    """Сбрасывает глобальное состояние между тестами."""
    k8s_tunnels._monitor_started = False
    k8s_tunnels._atexit_registered = False
    k8s_tunnels._processes_by_name = {}
    yield
    k8s_tunnels._stop_owned_tunnels()
    k8s_tunnels._monitor_started = False
    k8s_tunnels._atexit_registered = False
    k8s_tunnels._processes_by_name = {}


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


def test_start_dev_tunnels_monitor_idempotent() -> None:
    mock_thread_instance = MagicMock()

    with (
        patch.object(k8s_tunnels.Path, "is_file", return_value=True),
        patch.object(k8s_tunnels, "_ports_ready", return_value=False),
        patch.object(k8s_tunnels.threading, "Thread", return_value=mock_thread_instance) as mock_thread_cls,
        patch.object(k8s_tunnels, "atexit") as mock_atexit,
    ):
        k8s_tunnels._monitor_started = False
        k8s_tunnels.start_dev_tunnels_monitor(wait_ready=False)
        k8s_tunnels.start_dev_tunnels_monitor(wait_ready=False)

    mock_thread_cls.assert_called_once()
    mock_thread_instance.start.assert_called_once()
    mock_atexit.register.assert_called_once()


def test_tunnel_port_ready_dead_process() -> None:
    proc = MagicMock()
    proc.poll.return_value = 1
    spec = k8s_tunnels._tunnel_specs()[0]
    runtime = k8s_tunnels._TunnelRuntime(proc=proc, external=False)
    with patch.object(k8s_tunnels, "_tcp_port_open", return_value=False):
        assert k8s_tunnels._tunnel_port_ready(runtime, spec) is False


@pytest.mark.unit
def test_tunnel_port_ready_stuck_kubectl_port_closed() -> None:
    """Живой kubectl без TCP на probe_port — нездоров, monitor должен перезапустить."""
    proc = MagicMock()
    proc.poll.return_value = None
    spec = k8s_tunnels._tunnel_specs()[0]
    runtime = k8s_tunnels._TunnelRuntime(proc=proc, external=False)
    with patch.object(k8s_tunnels, "_tcp_port_open", return_value=False):
        assert k8s_tunnels._tunnel_port_ready(runtime, spec) is False


def test_start_skips_monitor_when_ports_already_open() -> None:
    specs = k8s_tunnels._tunnel_specs()

    with (
        patch.object(k8s_tunnels.Path, "is_file", return_value=True),
        patch.object(k8s_tunnels, "_ports_ready", return_value=True),
        patch.object(k8s_tunnels, "_adopt_external_forward") as adopt,
        patch.object(k8s_tunnels.threading, "Thread") as mock_thread,
        patch.object(k8s_tunnels, "atexit"),
    ):
        k8s_tunnels._monitor_started = False
        k8s_tunnels.start_dev_tunnels_monitor(wait_ready=False)

    mock_thread.assert_not_called()
    assert adopt.call_count == len(specs)


@pytest.mark.unit
def test_start_tunnel_stops_owned_kubectl_before_external_adopt() -> None:
    """Порт уже слушает другой forward — свой kubectl завершаем, не оставляем зомби."""
    spec = k8s_tunnels._tunnel_specs()[0]
    proc = MagicMock()
    k8s_tunnels._processes_by_name[spec.name] = k8s_tunnels._TunnelRuntime(
        proc=proc,
        external=False,
    )
    with (
        patch.object(k8s_tunnels, "_tcp_port_open", return_value=True),
        patch.object(k8s_tunnels, "_terminate_process") as terminate,
    ):
        k8s_tunnels._start_tunnel(spec, "kubeconfig.yaml")

    terminate.assert_called_once_with(proc)
    runtime = k8s_tunnels._processes_by_name[spec.name]
    assert runtime.external is True
    assert runtime.proc is None


def test_postgres_tunnel_uses_pod_by_default() -> None:
    spec = k8s_tunnels._tunnel_specs()[0]
    assert spec.resource == "pod/postgres-db-0"


def test_settings_run_local_default_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RUN_LOCAL", raising=False)
    assert Settings().run_local is False


def test_settings_run_local_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_LOCAL", "true")
    assert Settings().run_local is True
