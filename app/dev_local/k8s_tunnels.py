"""kubectl port-forward к Postgres и ClickHouse для локальной разработки (RUN_LOCAL=true).

Поддерживает несколько точек входа: если порты уже проброшены другим процессом,
новый процесс только проверяет TCP и не запускает второй kubectl.
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
_atexit_registered = False
_monitor_lock = threading.Lock()


@dataclass(frozen=True)
class _TunnelSpec:
    """Описание одного port-forward."""

    name: str
    namespace: str
    resource: str
    local_ports: tuple[int, ...]
    remote_ports: tuple[int, ...]
    probe_port: int


@dataclass
class _TunnelRuntime:
    """Состояние туннеля в текущем процессе."""

    proc: subprocess.Popen[bytes] | None
    external: bool  # порт уже слушал другой kubectl / ручной forward


_processes_by_name: dict[str, _TunnelRuntime] = {}


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


def _ports_ready(specs: list[_TunnelSpec]) -> bool:
    return all(_tcp_port_open("127.0.0.1", spec.probe_port) for spec in specs)


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


def _stop_owned_tunnels() -> None:
    """Останавливает только kubectl, запущенные этим процессом (не чужой forward)."""
    global _processes_by_name
    for runtime in _processes_by_name.values():
        if runtime.external or runtime.proc is None:
            continue
        _terminate_process(runtime.proc)
    _processes_by_name = {}


def _stop_tunnel(name: str) -> None:
    global _processes_by_name
    runtime = _processes_by_name.pop(name, None)
    if runtime is not None and not runtime.external and runtime.proc is not None:
        _terminate_process(runtime.proc)


def _adopt_external_forward(spec: _TunnelSpec) -> None:
    """Помечает туннель как уже проброшенный (другой процесс или ручной kubectl)."""
    global _processes_by_name
    _processes_by_name[spec.name] = _TunnelRuntime(proc=None, external=True)
    logger.info(
        "Tunnel %s: port %s already listening, reusing existing port-forward",
        spec.name,
        spec.probe_port,
    )


def _start_tunnel(
    spec: _TunnelSpec, kubeconfig: str
) -> subprocess.Popen[bytes] | None:
    """Запускает или переиспользует port-forward для одного туннеля."""
    global _processes_by_name

    if _tcp_port_open("127.0.0.1", spec.probe_port):
        _stop_tunnel(spec.name)
        _adopt_external_forward(spec)
        return None

    _stop_tunnel(spec.name)
    proc = _start_port_forward(spec, kubeconfig)
    _processes_by_name[spec.name] = _TunnelRuntime(proc=proc, external=False)
    return proc


def _start_all_tunnels(kubeconfig: str, specs: list[_TunnelSpec]) -> None:
    for spec in specs:
        _start_tunnel(spec, kubeconfig)


def _tunnel_port_ready(
    _runtime: _TunnelRuntime | None,
    spec: _TunnelSpec,
) -> bool:
    """Туннель здоров только если localhost:probe_port принимает TCP.

    Живой kubectl без слушающего порта (зависший bind) — нездоров: watchdog перезапустит.
    """
    return _tcp_port_open("127.0.0.1", spec.probe_port)


def wait_for_dev_tunnels_ready(
    timeout_sec: float | None = None,
    specs: list[_TunnelSpec] | None = None,
) -> None:
    """Блокирует до готовности всех туннелей (TCP на localhost).

    Не зависит от того, кто поднял port-forward — этот или другой процесс.

    Raises:
        TimeoutError: туннели не поднялись за timeout_sec.
    """
    tunnel_specs = specs if specs is not None else _tunnel_specs()
    if timeout_sec is None:
        raw = os.environ.get("DEV_TUNNEL_READY_TIMEOUT_SEC", "").strip()
        timeout_sec = float(raw) if raw else _DEFAULT_READY_TIMEOUT_SEC

    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if _ports_ready(tunnel_specs):
            logger.info("Dev k8s tunnels are ready on localhost")
            return
        time.sleep(_READY_POLL_INTERVAL_SEC)

    raise TimeoutError(
        "Dev k8s tunnels not ready within "
        f"{timeout_sec}s. Check kubectl access and DEV_TUNNEL_PG_RESOURCE "
        "(default pod/postgres-db-0)."
    )


def _monitor_loop(kubeconfig: str, specs: list[_TunnelSpec]) -> None:
    """Watchdog: перезапускает только туннели, запущенные этим процессом."""
    _start_all_tunnels(kubeconfig, specs)
    time.sleep(_STARTUP_WAIT_SEC)

    while True:
        time.sleep(_MONITOR_INTERVAL_SEC)
        for spec in specs:
            runtime = _processes_by_name.get(spec.name)
            if _tunnel_port_ready(runtime, spec):
                continue

            if (
                runtime is not None
                and not runtime.external
                and runtime.proc is not None
                and runtime.proc.poll() is not None
            ):
                _log_tunnel_exit(spec, runtime.proc)

            logger.warning(
                "Tunnel %s unhealthy, restarting (external=%s)",
                spec.name,
                runtime.external if runtime else None,
            )
            _start_tunnel(spec, kubeconfig)
            time.sleep(_STARTUP_WAIT_SEC)


def _register_atexit_once() -> None:
    global _atexit_registered
    if _atexit_registered:
        return
    atexit.register(_stop_owned_tunnels)
    _atexit_registered = True


def start_dev_tunnels_monitor(*, wait_ready: bool = True) -> None:
    """Идемпотентно обеспечивает port-forward для локальной разработки.

    Если порты уже слушают (другая точка входа / dev-tunnels.ps1) — только ждёт
    готовности, без второго kubectl и без watchdog.

    Args:
        wait_ready: дождаться TCP на localhost перед возвратом.
    """
    global _monitor_started

    kubeconfig = _default_kubeconfig()
    if not Path(kubeconfig).is_file():
        raise FileNotFoundError(f"Kubeconfig not found: {kubeconfig}")

    specs = _tunnel_specs()

    with _monitor_lock:
        if _monitor_started:
            if wait_ready:
                wait_for_dev_tunnels_ready(specs=specs)
            return

        if _ports_ready(specs):
            logger.info(
                "All dev tunnel ports already forwarded; skipping kubectl in this process"
            )
            for spec in specs:
                _adopt_external_forward(spec)
            _monitor_started = True
            if wait_ready:
                wait_for_dev_tunnels_ready(specs=specs)
            return

        _monitor_started = True

    _register_atexit_once()
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
