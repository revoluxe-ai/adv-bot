"""kubectl port-forward к Postgres и ClickHouse для локальной разработки (RUN_LOCAL=true).

Запускает два процесса ``kubectl port-forward`` и фоновый watchdog (раз в секунду):
проверяет, что процесс жив и локальный TCP-порт отвечает; при сбое — перезапуск.
"""

from __future__ import annotations

import atexit
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MONITOR_INTERVAL_SEC = 1.0
_TCP_PROBE_TIMEOUT_SEC = 0.5

_monitor_started = False
_monitor_lock = threading.Lock()
_active_processes: list[subprocess.Popen[bytes]] = []


@dataclass(frozen=True)
class _TunnelSpec:
    """Описание одного port-forward."""

    name: str
    namespace: str
    resource: str
    local_ports: tuple[int, ...]
    remote_ports: tuple[int, ...]
    probe_port: int


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_kubeconfig() -> str:
    env_path = os.environ.get("DEV_TUNNELS_KUBECONFIG", "").strip()
    if env_path:
        return env_path
    return str(_repo_root() / "k8s" / "new-cluster" / "new-cluster-config.yaml")


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


def _tunnel_specs() -> list[_TunnelSpec]:
    pg_port = _int_env("DEV_TUNNEL_PG_LOCAL_PORT", 15432)
    ch_http = _int_env("DEV_TUNNEL_CH_HTTP_PORT", 18123)
    ch_native = _int_env("DEV_TUNNEL_CH_NATIVE_PORT", 19000)
    return [
        _TunnelSpec(
            name="postgres",
            namespace="prod-adv-bot",
            resource="svc/postgres-db",
            local_ports=(pg_port,),
            remote_ports=(5432,),
            probe_port=pg_port,
        ),
        _TunnelSpec(
            name="clickhouse",
            namespace="prod-analytics",
            resource="svc/chi-clickhouse-main-0-0",
            local_ports=(ch_http, ch_native),
            remote_ports=(8123, 9000),
            probe_port=ch_http,
        ),
    ]


def _tcp_port_open(host: str, port: int) -> bool:
    """Проверяет доступность TCP-порта (port-forward слушает localhost)."""
    try:
        with socket.create_connection((host, port), timeout=_TCP_PROBE_TIMEOUT_SEC):
            return True
    except OSError:
        return False


def _build_port_forward_args(spec: _TunnelSpec) -> list[str]:
    mappings = [
        f"{local}:{remote}"
        for local, remote in zip(spec.local_ports, spec.remote_ports, strict=True)
    ]
    return [
        "kubectl",
        "port-forward",
        "-n",
        spec.namespace,
        spec.resource,
        *mappings,
    ]


def _start_port_forward(
    spec: _TunnelSpec, kubeconfig: str
) -> subprocess.Popen[bytes]:
    """Запускает kubectl port-forward для одного туннеля."""
    env = os.environ.copy()
    env["KUBECONFIG"] = kubeconfig
    cmd = _build_port_forward_args(spec)
    kwargs: dict[str, Any] = {
        "args": cmd,
        "env": env,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.PIPE,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    proc = subprocess.Popen(**kwargs)
    logger.info(
        "Started %s tunnel (pid=%s): %s",
        spec.name,
        proc.pid,
        " ".join(cmd),
    )
    return proc


def _terminate_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _stop_all_tunnels() -> None:
    global _active_processes
    for proc in _active_processes:
        _terminate_process(proc)
    _active_processes = []


def _start_all_tunnels(kubeconfig: str, specs: list[_TunnelSpec]) -> list[subprocess.Popen[bytes]]:
    _stop_all_tunnels()
    procs: list[subprocess.Popen[bytes]] = []
    for spec in specs:
        procs.append(_start_port_forward(spec, kubeconfig))
    _active_processes.extend(procs)
    return procs


def _tunnel_healthy(
    proc: subprocess.Popen[bytes], spec: _TunnelSpec
) -> bool:
    if proc.poll() is not None:
        return False
    return _tcp_port_open("127.0.0.1", spec.probe_port)


def _monitor_loop(kubeconfig: str, specs: list[_TunnelSpec]) -> None:
    """Watchdog: раз в секунду проверяет процессы и порты, перезапускает при сбое."""
    procs = _start_all_tunnels(kubeconfig, specs)
    # Даём kubectl время поднять listen
    time.sleep(2.0)

    while True:
        time.sleep(_MONITOR_INTERVAL_SEC)
        need_restart = False
        for proc, spec in zip(procs, specs, strict=True):
            if not _tunnel_healthy(proc, spec):
                logger.warning(
                    "Tunnel %s unhealthy (pid=%s, poll=%s), will restart",
                    spec.name,
                    proc.pid,
                    proc.poll(),
                )
                need_restart = True
                break

        if need_restart:
            procs = _start_all_tunnels(kubeconfig, specs)
            time.sleep(2.0)


def start_dev_tunnels_monitor() -> None:
    """Идемпотентно запускает фоновый монитор port-forward (только один поток на процесс)."""
    global _monitor_started

    with _monitor_lock:
        if _monitor_started:
            return
        _monitor_started = True

    kubeconfig = _default_kubeconfig()
    if not Path(kubeconfig).is_file():
        raise FileNotFoundError(f"Kubeconfig not found: {kubeconfig}")

    specs = _tunnel_specs()
    atexit.register(_stop_all_tunnels)

    thread = threading.Thread(
        target=_monitor_loop,
        args=(kubeconfig, specs),
        name="dev-k8s-tunnels",
        daemon=True,
    )
    thread.start()
    logger.info(
        "Dev k8s tunnels monitor started (kubeconfig=%s, PG=%s, CH HTTP=%s)",
        kubeconfig,
        specs[0].probe_port,
        specs[1].probe_port,
    )
