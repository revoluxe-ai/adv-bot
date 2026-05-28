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
_STARTUP_WAIT_SEC = 2.0
_READY_POLL_INTERVAL_SEC = 0.5
_DEFAULT_READY_TIMEOUT_SEC = 90.0

_monitor_started = False
_monitor_lock = threading.Lock()
_processes_by_name: dict[str, subprocess.Popen[bytes] | None] = {}


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


def _str_env(name: str, default: str) -> str:
    raw = os.environ.get(name, "").strip()
    return raw if raw else default


def _tunnel_specs() -> list[_TunnelSpec]:
    pg_port = _int_env("DEV_TUNNEL_PG_LOCAL_PORT", 15432)
    ch_http = _int_env("DEV_TUNNEL_CH_HTTP_PORT", 18123)
    ch_native = _int_env("DEV_TUNNEL_CH_NATIVE_PORT", 19000)
    forward_ch_native = _str_env("DEV_TUNNEL_CH_FORWARD_NATIVE", "false").lower() == "true"
    # svc/postgres-db — headless без selector; port-forward только к pooler или pod.
    pg_resource = _str_env("DEV_TUNNEL_PG_RESOURCE", "pod/postgres-db-0")
    ch_local_ports: tuple[int, ...] = (ch_http,)
    ch_remote_ports: tuple[int, ...] = (8123,)
    if forward_ch_native:
        ch_local_ports = (ch_http, ch_native)
        ch_remote_ports = (8123, 9000)
    return [
        _TunnelSpec(
            name="postgres",
            namespace="prod-adv-bot",
            resource=pg_resource,
            local_ports=(pg_port,),
            remote_ports=(5432,),
            probe_port=pg_port,
        ),
        _TunnelSpec(
            name="clickhouse",
            namespace="prod-analytics",
            resource="svc/chi-clickhouse-main-0-0",
            local_ports=ch_local_ports,
            remote_ports=ch_remote_ports,
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


def _read_kubectl_stderr(proc: subprocess.Popen[bytes]) -> str:
    """Читает stderr kubectl после завершения процесса."""
    if proc.stderr is None:
        return ""
    try:
        raw = proc.stderr.read()
    except Exception:
        return ""
    return raw.decode("utf-8", errors="replace").strip()


def _log_tunnel_exit(spec: _TunnelSpec, proc: subprocess.Popen[bytes]) -> None:
    err = _read_kubectl_stderr(proc)
    if err:
        logger.error("Tunnel %s kubectl exited: %s", spec.name, err)
    else:
        logger.error(
            "Tunnel %s kubectl exited with code %s",
            spec.name,
            proc.returncode,
        )


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
    global _processes_by_name
    for proc in _processes_by_name.values():
        if proc is not None:
            _terminate_process(proc)
    _processes_by_name = {}


def _stop_tunnel(name: str) -> None:
    global _processes_by_name
    proc = _processes_by_name.pop(name, None)
    if proc is not None:
        _terminate_process(proc)


def _start_tunnel(
    spec: _TunnelSpec, kubeconfig: str
) -> subprocess.Popen[bytes] | None:
    """Перезапускает один туннель (остальные не трогает).

    Если порт уже слушает (ручной port-forward) — kubectl не запускаем.
    """
    global _processes_by_name
    if _tcp_port_open("127.0.0.1", spec.probe_port):
        logger.info(
            "Tunnel %s: port %s already listening, using existing forward",
            spec.name,
            spec.probe_port,
        )
        _stop_tunnel(spec.name)
        _processes_by_name[spec.name] = None
        return None
    _stop_tunnel(spec.name)
    proc = _start_port_forward(spec, kubeconfig)
    _processes_by_name[spec.name] = proc
    return proc


def _start_all_tunnels(kubeconfig: str, specs: list[_TunnelSpec]) -> None:
    for spec in specs:
        _start_tunnel(spec, kubeconfig)


def _tunnel_port_ready(
    proc: subprocess.Popen[bytes] | None, spec: _TunnelSpec
) -> bool:
    if _tcp_port_open("127.0.0.1", spec.probe_port):
        return True
    if proc is None:
        return False
    if proc.poll() is not None:
        return False
    return False


def _all_tunnels_ready(specs: list[_TunnelSpec]) -> bool:
    for spec in specs:
        if spec.name not in _processes_by_name:
            return False
        proc = _processes_by_name[spec.name]
        if not _tunnel_port_ready(proc, spec):
            return False
    return True


def wait_for_dev_tunnels_ready(
    timeout_sec: float | None = None,
    specs: list[_TunnelSpec] | None = None,
) -> None:
    """Блокирует до готовности всех туннелей (TCP на localhost).

    Raises:
        TimeoutError: туннели не поднялись за timeout_sec.
    """
    tunnel_specs = specs if specs is not None else _tunnel_specs()
    if timeout_sec is None:
        raw = os.environ.get("DEV_TUNNEL_READY_TIMEOUT_SEC", "").strip()
        timeout_sec = float(raw) if raw else _DEFAULT_READY_TIMEOUT_SEC

    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if _all_tunnels_ready(tunnel_specs):
            logger.info("Dev k8s tunnels are ready")
            return
        time.sleep(_READY_POLL_INTERVAL_SEC)

    raise TimeoutError(
        "Dev k8s tunnels not ready within "
        f"{timeout_sec}s. Check kubectl access and DEV_TUNNEL_PG_RESOURCE "
        "(default pod/postgres-db-0)."
    )


def _monitor_loop(kubeconfig: str, specs: list[_TunnelSpec]) -> None:
    """Watchdog: раз в секунду проверяет процессы и порты, перезапускает при сбое."""
    _start_all_tunnels(kubeconfig, specs)
    time.sleep(_STARTUP_WAIT_SEC)

    while True:
        time.sleep(_MONITOR_INTERVAL_SEC)
        for spec in specs:
            proc = _processes_by_name.get(spec.name)
            if _tunnel_port_ready(proc, spec):
                continue
            if proc is not None and proc.poll() is not None:
                _log_tunnel_exit(spec, proc)
            logger.warning(
                "Tunnel %s unhealthy, restarting (pid=%s, poll=%s)",
                spec.name,
                proc.pid if proc else None,
                proc.poll() if proc else None,
            )
            _start_tunnel(spec, kubeconfig)
            time.sleep(_STARTUP_WAIT_SEC)


def start_dev_tunnels_monitor(*, wait_ready: bool = True) -> None:
    """Идемпотентно запускает фоновый монитор port-forward (только один поток на процесс).

    Args:
        wait_ready: дождаться TCP на localhost перед возвратом (для bootstrap приложения).
    """
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
        "Dev k8s tunnels monitor started (kubeconfig=%s, PG=%s via %s, CH HTTP=%s)",
        kubeconfig,
        specs[0].probe_port,
        specs[0].resource,
        specs[1].probe_port,
    )
    if wait_ready:
        wait_for_dev_tunnels_ready(specs=specs)
