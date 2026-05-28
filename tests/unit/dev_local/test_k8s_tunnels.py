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
    k8s_tunnels._active_processes = []
    yield
    k8s_tunnels._stop_all_tunnels()
    k8s_tunnels._monitor_started = False
    k8s_tunnels._active_processes = []


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


def test_start_dev_tunnels_monitor_idempotent() -> None:
    mock_thread_instance = MagicMock()

    with (
        patch.object(k8s_tunnels.Path, "is_file", return_value=True),
        patch.object(k8s_tunnels.threading, "Thread", return_value=mock_thread_instance) as mock_thread_cls,
        patch.object(k8s_tunnels, "atexit") as mock_atexit,
    ):
        k8s_tunnels._monitor_started = False
        k8s_tunnels.start_dev_tunnels_monitor()
        k8s_tunnels.start_dev_tunnels_monitor()

    mock_thread_cls.assert_called_once()
    mock_thread_instance.start.assert_called_once()
    mock_atexit.register.assert_called_once()


def test_tunnel_healthy_dead_process() -> None:
    proc = MagicMock()
    proc.poll.return_value = 1
    spec = k8s_tunnels._tunnel_specs()[0]
    assert k8s_tunnels._tunnel_healthy(proc, spec) is False


def test_settings_run_local_default_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RUN_LOCAL", raising=False)
    assert Settings().run_local is False


def test_settings_run_local_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_LOCAL", "true")
    assert Settings().run_local is True
