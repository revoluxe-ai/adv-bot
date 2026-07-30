"""LEGACY — kubectl port-forward к Postgres/ClickHouse (очередь на выпиливание).

**Статус:** deprecated / pending removal. Канонический локальный путь — публичный
IP / NodePort из ``.env`` (см. ``k8s/network/local-dev-external-access.md``,
``env.sample``). Не добавлять новые callers и unit-тесты на этот модуль.

Трекинг: ``DOTO/WORKLOG.md`` — «Выпилить app/dev_local/k8s_tunnels (+ scripts/dev-tunnels.ps1)».

Включение (пока модуль жив): ``DEV_TUNNELS_ENABLED=true`` перед
``start_dev_tunnels_monitor``. Автозапуск при импорте ``settings`` отключён.

Несколько точек входа (несколько Python-процессов) могут работать параллельно:

- если forward на localhost уже поднят **и** probe OK (TCP; для CH — HTTP ``SELECT 1``) —
  процесс **не** запускает свой kubectl и **не** убивает чужой; только логирует reuse
  и при ``wait_ready`` выполняет smoke-check;
- если probe FAIL — только тогда cleanup stale kubectl и подъём своего forward
  (или перезапуск owned).

При завершении процесса (atexit, SIGINT/SIGTERM, выход monitor-thread)
останавливаются только kubectl, запущенные **этим** процессом (``external`` не трогаем).
"""

from __future__ import annotations

import atexit
import logging
import os
import platform
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

import psutil

logger = logging.getLogger(__name__)

_MONITOR_INTERVAL_SEC = 1.0
_TCP_PROBE_TIMEOUT_SEC = 0.5
_STARTUP_WAIT_SEC = 2.0
_READY_POLL_INTERVAL_SEC = 0.5
_DEFAULT_READY_TIMEOUT_SEC = 90.0
_DEFAULT_CH_SMOKE_TIMEOUT_SEC = 4.0
_PORT_FREE_TIMEOUT_SEC = 15.0
_REPAIR_COOLDOWN_SEC = 3.0
_KUBECTL_START_GRACE_SEC = 0.8
_DEFAULT_MAX_TUNNEL_RESTARTS = 8

_monitor_started = False
_cleanup_registered = False
_monitor_lock = threading.Lock()
_consecutive_restart_failures: dict[str, int] = {}
_tunnel_ok_logged: set[str] = set()
_last_repair_monotonic: dict[str, float] = {}
_repair_lock_files: dict[str, BinaryIO] = {}


@dataclass
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


def _normalize_kubeconfig_candidate(raw_path: str) -> Path:
    """Нормализует kubeconfig path без Windows escape-багов."""
    return Path(raw_path.strip().strip('"').strip("'")).expanduser()


def _kubeconfig_candidates() -> list[tuple[str, Path]]:
    """Возвращает кандидаты kubeconfig по приоритету env-переменных и default path."""
    candidates: list[tuple[str, Path]] = []
    for env_name in (
        "KUBECONFIG",
        "DEV_KUBECONFIG",
        "TWC_KUBECONFIG",
        "DEV_TUNNELS_KUBECONFIG",
    ):
        raw_value = os.environ.get(env_name, "").strip()
        if not raw_value:
            continue
        for raw_part in raw_value.split(os.pathsep):
            candidate = raw_part.strip()
            if candidate:
                candidates.append((env_name, _normalize_kubeconfig_candidate(candidate)))

    candidates.append(
        (
            "default",
            (_repo_root() / "k8s" / "new-cluster" / "new-cluster-config.yaml").resolve(),
        )
    )
    return candidates


def _configured_kubeconfig_path() -> Path:
    """Возвращает kubeconfig только из явной конфигурации окружения.

    Monitor не должен стартовать на репозиторном default path, если kubeconfig
    не задан явно или файл отсутствует.
    """
    configured_candidates: list[tuple[str, Path]] = []
    for source, candidate in _kubeconfig_candidates():
        if source == "default":
            continue
        configured_candidates.append((source, candidate))
        if candidate.is_file():
            resolved = candidate.resolve()
            logger.info("Using kubeconfig from %s: %s", source, resolved)
            return resolved

    checked = ", ".join(
        f"{source}={path}" for source, path in configured_candidates
    )
    raise FileNotFoundError(
        "Kubeconfig not found. Checked: "
        f"{checked or 'no configured kubeconfig env vars'}. "
        f"Platform={platform.system()}. "
        "Set KUBECONFIG, DEV_KUBECONFIG, TWC_KUBECONFIG or DEV_TUNNELS_KUBECONFIG."
    )


def resolve_kubeconfig_path() -> Path:
    """Определяет kubeconfig path и логирует фактический выбор."""
    candidates = _kubeconfig_candidates()
    for source, candidate in candidates:
        if candidate.is_file():
            resolved = candidate.resolve()
            logger.info("Using kubeconfig from %s: %s", source, resolved)
            return resolved

    checked = ", ".join(f"{source}={path}" for source, path in candidates)
    raise FileNotFoundError(
        "Kubeconfig not found. Checked: "
        f"{checked}. Platform={platform.system()}. "
        "Set KUBECONFIG, DEV_KUBECONFIG, TWC_KUBECONFIG or DEV_TUNNELS_KUBECONFIG."
    )


def _default_kubeconfig() -> str:
    """Совместимый wrapper для существующих вызовов."""
    return str(resolve_kubeconfig_path())


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return float(raw)


def _str_env(name: str, default: str) -> str:
    raw = os.environ.get(name, "").strip()
    return raw if raw else default


def _ch_smoke_timeout_sec() -> float:
    return _float_env("DEV_TUNNEL_CH_SMOKE_TIMEOUT_SEC", _DEFAULT_CH_SMOKE_TIMEOUT_SEC)


def _port_free_timeout_sec() -> float:
    return _float_env("DEV_TUNNEL_PORT_FREE_TIMEOUT_SEC", _PORT_FREE_TIMEOUT_SEC)


def _repair_cooldown_sec() -> float:
    return _float_env("DEV_TUNNEL_REPAIR_COOLDOWN_SEC", _REPAIR_COOLDOWN_SEC)


def _max_tunnel_restarts() -> int:
    return _int_env("DEV_TUNNEL_MAX_RESTARTS", _DEFAULT_MAX_TUNNEL_RESTARTS)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def _parse_port_candidates(raw: str) -> list[int]:
    """Парсит список портов и диапазонов вида ``28123,28124-28140``."""
    ports: list[int] = []
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start_raw, end_raw = item.split("-", 1)
            ports.extend(range(int(start_raw), int(end_raw) + 1))
        else:
            ports.append(int(item))
    return ports


def _repair_lock_key(spec: _TunnelSpec) -> str:
    """Ключ межпроцессного lock для конкретного tunnel spec."""
    return f"{spec.name}:{spec.probe_port}:{spec.namespace}:{spec.resource}"


def _repair_lock_path(spec: _TunnelSpec) -> Path:
    """Путь lock-файла для синхронизации repair между Python-процессами."""
    safe_name = spec.name.replace("/", "_")
    return Path(tempfile.gettempdir()) / f"adv-bot-dev-tunnel-{safe_name}-{spec.probe_port}.lock"


def _acquire_repair_lock(spec: _TunnelSpec) -> bool:
    """Пытается взять неблокирующий межпроцессный lock на repair/start tunnel."""
    key = _repair_lock_key(spec)
    if key in _repair_lock_files:
        return True

    lock_path = _repair_lock_path(spec)
    lock_file = lock_path.open("a+b")
    lock_file.seek(0)
    lock_file.write(b"0")
    lock_file.flush()
    lock_file.seek(0)
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        return False

    _repair_lock_files[key] = lock_file
    return True


def _release_repair_lock(spec: _TunnelSpec) -> None:
    """Освобождает межпроцессный lock tunnel repair (если был взят)."""
    key = _repair_lock_key(spec)
    lock_file = _repair_lock_files.pop(key, None)
    if lock_file is None:
        prefix = f"{spec.name}:"
        stale_key = next(
            (held_key for held_key in _repair_lock_files if held_key.startswith(prefix)),
            None,
        )
        if stale_key is not None:
            lock_file = _repair_lock_files.pop(stale_key)
    if lock_file is None:
        return

    try:
        lock_file.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except OSError:
        logger.debug("Repair lock release failed for %s", key)
    finally:
        lock_file.close()


def _tunnel_specs() -> list[_TunnelSpec]:
    pg_port = _int_env("DEV_TUNNEL_PG_LOCAL_PORT", 15432)
    ch_http = _int_env("DEV_TUNNEL_CH_HTTP_PORT", 18123)
    ch_native = _int_env("DEV_TUNNEL_CH_NATIVE_PORT", 19000)
    forward_ch_native = _str_env("DEV_TUNNEL_CH_FORWARD_NATIVE", "false").lower() == "true"
    pg_resource = _str_env("DEV_TUNNEL_PG_RESOURCE", "svc/postgres-db-pooler")
    ch_local_ports: tuple[int, ...] = (ch_http,)
    ch_remote_ports: tuple[int, ...] = (8123,)
    if forward_ch_native:
        ch_local_ports = (ch_http, ch_native)
        ch_remote_ports = (8123, 9000)
    if os.environ.get("RUN_LOCAL", "").strip().lower() == "true":
        os.environ["CLICKHOUSE_PORT"] = str(ch_http)
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


def _log_tunnel_spec(spec: _TunnelSpec, *, prefix: str) -> None:
    mappings = ", ".join(
        f"{local}:{remote}"
        for local, remote in zip(spec.local_ports, spec.remote_ports, strict=True)
    )
    logger.info(
        "%s tunnel %s: local_port=%s namespace=%s resource=%s mappings=[%s]",
        prefix,
        spec.name,
        spec.probe_port,
        spec.namespace,
        spec.resource,
        mappings,
    )


def _tcp_port_open(host: str, port: int) -> bool:
    """Проверяет доступность TCP-порта (port-forward слушает localhost)."""
    try:
        with socket.create_connection((host, port), timeout=_TCP_PROBE_TIMEOUT_SEC):
            return True
    except OSError:
        return False


def _clickhouse_http_select_1(port: int, timeout_sec: float) -> None:
    """HTTP smoke: ``SELECT 1`` через ClickHouse HTTP-интерфейс (без clickhouse_connect).

    Использует raw socket с ``settimeout`` — на Windows ``urllib`` может зависнуть,
    если port-forward принимает TCP, но не отвечает по HTTP.

    Raises:
        OSError: TCP/HTTP ошибка, таймаут или неожиданный ответ.
    """
    host = "127.0.0.1"
    payload = b"SELECT 1"
    request = (
        f"POST / HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(payload)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("ascii") + payload

    try:
        with socket.create_connection((host, port), timeout=timeout_sec) as sock:
            sock.settimeout(timeout_sec)
            sock.sendall(request)
            chunks: list[bytes] = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
    except OSError as exc:
        raise OSError(
            f"ClickHouse HTTP smoke failed on http://{host}:{port}/: {exc}"
        ) from exc

    raw = b"".join(chunks)
    if not raw:
        raise OSError(f"ClickHouse HTTP smoke empty response on http://{host}:{port}/")

    header_sep = raw.find(b"\r\n\r\n")
    body = raw[header_sep + 4 :] if header_sep >= 0 else raw
    body_text = body.decode("utf-8", errors="replace").strip()
    if body_text != "1":
        raise OSError(
            f"ClickHouse HTTP smoke unexpected body on http://{host}:{port}/: "
            f"{body_text!r} (expected '1')"
        )


def _clickhouse_http_healthy(port: int) -> bool:
    """True если ClickHouse отвечает HTTP ``SELECT 1`` (remote service alive)."""
    try:
        _clickhouse_http_select_1(port, _ch_smoke_timeout_sec())
    except OSError as exc:
        logger.debug("ClickHouse HTTP probe failed on port %s: %s", port, exc)
        return False
    return True


def _tunnel_probe_ready(spec: _TunnelSpec) -> bool:
    """Туннель ready = kubectl слушает на localhost (TCP open).

    HTTP-проверку CH выполняем отдельно в smoke-check, не как gate для tunnel ready.
    Это позволяет приложению стартовать даже если CH в кластере временно недоступен.
    """
    return _tcp_port_open("127.0.0.1", spec.probe_port)


def _ports_ready(specs: list[_TunnelSpec]) -> bool:
    return all(_tunnel_probe_ready(spec) for spec in specs)


def _tunnel_ready_message(spec: _TunnelSpec) -> str:
    """Человеко-читаемый readiness log для одного tunnel."""
    mappings = ", ".join(
        f"127.0.0.1:{local} -> {spec.namespace} {spec.resource}:{remote}"
        for local, remote in zip(spec.local_ports, spec.remote_ports, strict=True)
    )
    return f"{spec.name.capitalize()} port-forward ready: {mappings}"


def _listener_pids_netstat(port: int) -> list[int]:
    """Windows fallback: PID из ``netstat -ano`` для LISTENING на local port."""
    if sys.platform != "win32":
        return []
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("netstat failed for port %s: %s", port, exc)
        return []

    suffix = f":{port}"
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        upper = line.upper()
        if "LISTENING" not in upper or suffix not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        pid_raw = parts[-1]
        if pid_raw.isdigit():
            pids.add(int(pid_raw))
    return sorted(pids)


def _all_listener_pids(port: int) -> list[int]:
    """Все PID, слушающие local port (127.0.0.1 / ::1 / 0.0.0.0), psutil + netstat."""
    pids: set[int] = set()
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status != psutil.CONN_LISTEN or conn.laddr.port != port:
                continue
            lip = conn.laddr.ip
            if lip not in ("0.0.0.0", "127.0.0.1", "::1", "::"):
                continue
            if conn.pid:
                pids.add(conn.pid)
    except (psutil.Error, PermissionError) as exc:
        logger.debug("net_connections failed for port %s: %s", port, exc)

    for pid in _listener_pids_netstat(port):
        pids.add(pid)
    return sorted(pids)


def _listener_pid(port: int, host: str = "127.0.0.1") -> int | None:
    """Первый PID слушателя localhost:port (для диагностики)."""
    del host  # все локальные listener учитываются в _all_listener_pids
    listeners = _all_listener_pids(port)
    return listeners[0] if listeners else None


def _port_is_free(port: int) -> bool:
    """Порт свободен для bind (нет LISTEN), в отличие от ``_tcp_port_open``."""
    return not _all_listener_pids(port)


def _try_bind_loopback(port: int, family: int, host: str) -> bool:
    """Пробует bind на loopback; False при OSError (занят порт или стек недоступен)."""
    sock: socket.socket | None = None
    try:
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        if sock is not None:
            sock.close()


def _port_bindable(port: int) -> bool:
    """Проверяет, что локальный порт можно занять под kubectl (обязательно IPv4).

    Дополнительно пробует IPv6 (::1), если стек есть; отсутствие IPv6 на хосте
    не считается ошибкой — kubectl port-forward использует 127.0.0.1.
    """
    if not _port_is_free(port):
        return False
    if not _try_bind_loopback(port, socket.AF_INET, "127.0.0.1"):
        return False
    _try_bind_loopback(port, socket.AF_INET6, "::1")
    return True


def _select_clickhouse_fallback_port(current_port: int) -> int | None:
    """Возвращает свободный fallback-порт для CH HTTP tunnel, если разрешено env."""
    if not _bool_env("DEV_TUNNEL_CH_AUTO_FALLBACK_PORT", True):
        return None
    raw = _str_env("DEV_TUNNEL_CH_FALLBACK_PORTS", "28123-28149")
    for port in _parse_port_candidates(raw):
        if port == current_port:
            continue
        if _port_bindable(port):
            return port
    return None


def _retarget_clickhouse_port(spec: _TunnelSpec, new_port: int) -> None:
    """Переключает текущий RUN_LOCAL процесс на другой локальный CH HTTP port."""
    if spec.name != "clickhouse":
        return
    old_port = spec.probe_port
    local_ports = list(spec.local_ports)
    local_ports[0] = new_port
    spec.local_ports = tuple(local_ports)
    spec.probe_port = new_port
    os.environ["DEV_TUNNEL_CH_HTTP_PORT"] = str(new_port)
    os.environ["CLICKHOUSE_PORT"] = str(new_port)
    _tunnel_ok_logged.discard(spec.name)
    logger.warning(
        "Tunnel clickhouse: local port %s cannot be used; falling back to %s "
        "(CLICKHOUSE_PORT updated for this process)",
        old_port,
        new_port,
    )


def _process_cmdline(pid: int) -> str:
    return " ".join(psutil.Process(pid).cmdline())


def _is_matching_kubectl_port_forward(pid: int, spec: _TunnelSpec) -> bool:
    """True, если PID — kubectl port-forward на ожидаемый namespace/service/порты."""
    try:
        cmdline = _process_cmdline(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
        logger.debug("Cannot read cmdline for pid=%s: %s", pid, exc)
        return False

    normalized = cmdline.lower()
    if "kubectl" not in normalized or "port-forward" not in normalized:
        return False
    if spec.namespace.lower() not in normalized:
        return False
    resource_key = spec.resource.split("/", 1)[-1].lower()
    if resource_key not in normalized:
        return False
    compact = normalized.replace(" ", "")
    for local, remote in zip(spec.local_ports, spec.remote_ports, strict=True):
        mapping = f"{local}:{remote}"
        if mapping not in normalized and mapping not in compact:
            return False
    return True


def _taskkill_tree(pid: int) -> None:
    """Windows: принудительно завершить дерево процессов (kubectl port-forward)."""
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _kill_psutil_tree(pid: int) -> None:
    """Завершает процесс и дочерние (port-forward может слушать не root PID)."""
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return

    children = proc.children(recursive=True)
    for child in reversed(children):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    proc.terminate()
    _, alive = psutil.wait_procs([proc, *children], timeout=5)
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        proc.wait(timeout=2)
    except psutil.TimeoutExpired:
        pass


def _kill_pid_tree(pid: int, *, reason: str) -> None:
    """Завершает процесс по PID и дочерние (stale kubectl)."""
    try:
        psutil.Process(pid)
    except psutil.NoSuchProcess:
        logger.warning("Cleanup: stale pid=%s already gone (%s)", pid, reason)
        return

    logger.warning("Killing process tree pid=%s (%s)", pid, reason)
    _kill_psutil_tree(pid)
    if sys.platform == "win32":
        _taskkill_tree(pid)


def _find_matching_kubectl_pids(spec: _TunnelSpec) -> list[int]:
    """Ищет kubectl port-forward по cmdline (fallback, если net_connections без PID)."""
    pids: list[int] = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            pid = proc.info.get("pid")
            if pid is None:
                continue
            if _is_matching_kubectl_port_forward(int(pid), spec):
                pids.append(int(pid))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids


def _force_free_local_port(
    spec: _TunnelSpec,
    *,
    owned_pid: int | None = None,
) -> bool:
    """Убивает всех listener на ``probe_port`` (kubectl/owned), ждёт освобождения порта.

    Returns:
        True если LISTEN на порту больше нет.
    """
    timeout_sec = _port_free_timeout_sec()
    deadline = time.monotonic() + timeout_sec
    killed_total: list[int] = []

    while time.monotonic() < deadline:
        listeners = _all_listener_pids(spec.probe_port)
        if not listeners:
            if killed_total:
                logger.warning(
                    "Tunnel %s: port %s free after killing PIDs %s",
                    spec.name,
                    spec.probe_port,
                    killed_total,
                )
            return True

        killed_pass: list[int] = []
        for pid in listeners:
            if owned_pid is not None and pid == owned_pid:
                _kill_pid_tree(pid, reason=f"owned stale {spec.name}")
                killed_pass.append(pid)
                continue
            if _is_matching_kubectl_port_forward(pid, spec):
                _kill_pid_tree(
                    pid,
                    reason=f"stale kubectl on port {spec.probe_port}",
                )
                killed_pass.append(pid)
                continue
            try:
                cmdline = _process_cmdline(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                cmdline = "<unavailable>"
            raise RuntimeError(
                f"Dev tunnel port {spec.probe_port} ({spec.name}) is held by pid={pid} "
                f"(not matching kubectl port-forward). Command line: {cmdline!r}. "
                "Stop that process manually or change DEV_TUNNEL_CH_HTTP_PORT."
            )

        for pid in _find_matching_kubectl_pids(spec):
            if pid in listeners:
                continue
            _kill_pid_tree(pid, reason=f"orphan kubectl for {spec.name}")
            killed_pass.append(pid)

        killed_total.extend(killed_pass)
        time.sleep(0.3)

    remaining = _all_listener_pids(spec.probe_port)
    logger.warning(
        "Tunnel %s: port %s still has listeners %s after %.0fs (killed %s)",
        spec.name,
        spec.probe_port,
        remaining,
        timeout_sec,
        killed_total,
    )
    return False


def _clear_broken_tunnel_listeners(spec: _TunnelSpec) -> None:
    """Probe FAIL: завершить owned + stale kubectl, дождаться освобождения LISTEN-порта."""
    logger.warning(
        "Tunnel %s smoke FAIL: port %s unhealthy "
        "(namespace=%s, resource=%s, listeners=%s) — clearing",
        spec.name,
        spec.probe_port,
        spec.namespace,
        spec.resource,
        _all_listener_pids(spec.probe_port),
    )

    runtime = _processes_by_name.get(spec.name)
    owned_pid: int | None = None
    if runtime is not None and not runtime.external and runtime.proc is not None:
        owned_pid = runtime.proc.pid
        if runtime.proc.poll() is None:
            logger.warning(
                "Terminating owned broken tunnel %s pid=%s",
                spec.name,
                owned_pid,
            )
            _terminate_process_tree(runtime.proc)

    _force_free_local_port(spec, owned_pid=owned_pid)


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
    if not _port_is_free(spec.probe_port):
        listeners = _all_listener_pids(spec.probe_port)
        raise RuntimeError(
            f"Cannot start {spec.name} port-forward: port {spec.probe_port} "
            f"still has listeners {listeners}"
        )

    proc = subprocess.Popen(**kwargs)
    _log_tunnel_spec(spec, prefix="Started")
    logger.info("Started %s tunnel pid=%s: %s", spec.name, proc.pid, " ".join(cmd))
    time.sleep(_KUBECTL_START_GRACE_SEC)
    if proc.poll() is not None:
        err = _read_kubectl_stderr(proc)
        raise RuntimeError(
            f"Tunnel {spec.name} kubectl exited immediately (pid={proc.pid}): {err}"
        )
    return proc


def _terminate_process_tree(proc: subprocess.Popen[bytes]) -> None:
    """Завершает subprocess.Popen и дерево дочерних (важно для kubectl на Windows)."""
    if proc.poll() is not None:
        return
    _kill_psutil_tree(proc.pid)
    if sys.platform == "win32":
        _taskkill_tree(proc.pid)
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _terminate_process(proc: subprocess.Popen[bytes]) -> None:
    _terminate_process_tree(proc)


def _stop_owned_tunnels(*, reason: str = "shutdown") -> None:
    """Останавливает только kubectl, запущенные этим процессом (не чужой forward)."""
    global _processes_by_name
    if not _processes_by_name:
        logger.debug("Cleanup skipped: no tunnels registered (%s)", reason)
        return

    logger.info("Cleanup started (%s)", reason)
    for name, runtime in list(_processes_by_name.items()):
        if runtime.external:
            logger.info(
                "Cleanup skipped tunnel %s: external/adopted forward (%s)",
                name,
                reason,
            )
            continue
        if runtime.proc is None:
            logger.debug(
                "Cleanup skipped tunnel %s: no owned process (%s)",
                name,
                reason,
            )
            continue
        if runtime.proc.poll() is not None:
            logger.debug(
                "Cleanup skipped tunnel %s: kubectl already exited (%s)",
                name,
                reason,
            )
            continue
        logger.info(
            "Cleanup terminating owned tunnel %s pid=%s (%s)",
            name,
            runtime.proc.pid,
            reason,
        )
        _terminate_process(runtime.proc)
    _processes_by_name = {}
    logger.info("Cleanup done (%s)", reason)


def _stop_tunnel(name: str) -> None:
    global _processes_by_name
    runtime = _processes_by_name.pop(name, None)
    if runtime is not None and not runtime.external and runtime.proc is not None:
        _terminate_process(runtime.proc)


def _adopt_external_forward(spec: _TunnelSpec) -> None:
    """Помечает туннель как уже проброшенный (другой процесс или ручной kubectl)."""
    global _processes_by_name
    _processes_by_name[spec.name] = _TunnelRuntime(proc=None, external=True)


def _log_tunnel_ok_once(spec: _TunnelSpec, *, source: str, pid: int | None = None) -> None:
    """Один раз за жизнь процесса логирует, что туннель здоров и не трогается."""
    global _tunnel_ok_logged
    if spec.name in _tunnel_ok_logged:
        return
    _tunnel_ok_logged.add(spec.name)
    _log_tunnel_spec(spec, prefix="OK")
    if pid is not None:
        logger.info(
            "Tunnel %s OK — reusing %s port-forward on port %s (pid=%s), kubectl not started",
            spec.name,
            source,
            spec.probe_port,
            pid,
        )
    else:
        logger.info(
            "Tunnel %s OK — reusing %s port-forward on port %s, kubectl not started",
            spec.name,
            source,
            spec.probe_port,
        )


def _try_reuse_healthy_forward(spec: _TunnelSpec) -> bool:
    """Если forward уже здоров — adopt/reuse, без kill и без нового kubectl.

    Returns:
        True — туннель здоров, repair не нужен.
    """
    if not _tunnel_probe_ready(spec):
        return False

    runtime = _processes_by_name.get(spec.name)
    if runtime is not None and not runtime.external and runtime.proc is not None:
        if runtime.proc.poll() is None:
            _log_tunnel_ok_once(spec, source="owned", pid=runtime.proc.pid)
            return True
        logger.warning(
            "Tunnel %s: owned kubectl pid=%s exited but port %s still healthy — adopting external",
            spec.name,
            runtime.proc.pid,
            spec.probe_port,
        )
        _terminate_process_tree(runtime.proc)

    if runtime is not None and runtime.external:
        logger.debug(
            "Tunnel %s still healthy (external reuse on port %s)",
            spec.name,
            spec.probe_port,
        )
        return True

    _adopt_external_forward(spec)
    _log_tunnel_ok_once(spec, source="external")
    return True


def _repair_broken_tunnel(
    spec: _TunnelSpec, kubeconfig: str
) -> subprocess.Popen[bytes] | None:
    """Probe FAIL: очистить broken listeners и поднять свой kubectl (если порт свободен)."""
    global _processes_by_name, _last_repair_monotonic

    if not _acquire_repair_lock(spec):
        logger.info(
            "Tunnel %s repair skipped: another process holds repair lock (port=%s)",
            spec.name,
            spec.probe_port,
        )
        return None

    try:
        now = time.monotonic()
        last = _last_repair_monotonic.get(spec.name, 0.0)
        cooldown = _repair_cooldown_sec()
        if now - last < cooldown:
            logger.debug(
                "Tunnel %s repair skipped (cooldown %.1fs, listeners=%s)",
                spec.name,
                cooldown,
                _all_listener_pids(spec.probe_port),
            )
            return None
        _last_repair_monotonic[spec.name] = now

        logger.warning(
            "Tunnel %s unhealthy — repairing (namespace=%s, resource=%s, port=%s, listeners=%s)",
            spec.name,
            spec.namespace,
            spec.resource,
            spec.probe_port,
            _all_listener_pids(spec.probe_port),
        )
        try:
            _clear_broken_tunnel_listeners(spec)
        except RuntimeError as exc:
            logger.error(
                "Tunnel %s repair cannot clear port %s: %s",
                spec.name,
                spec.probe_port,
                exc,
            )
            return None

        _stop_tunnel(spec.name)

        if _try_reuse_healthy_forward(spec):
            logger.info(
                "Tunnel %s became healthy during repair — leaving existing forward",
                spec.name,
            )
            return None

        if spec.name == "clickhouse" and not _port_bindable(spec.probe_port):
            fallback_port = _select_clickhouse_fallback_port(spec.probe_port)
            if fallback_port is None:
                logger.error(
                    "Tunnel clickhouse: port %s not bindable and no fallback available",
                    spec.probe_port,
                )
                return None
            logger.warning(
                "Tunnel clickhouse: port %s not bindable; switching to fallback %s",
                spec.probe_port,
                fallback_port,
            )
            _retarget_clickhouse_port(spec, fallback_port)

        if not _port_is_free(spec.probe_port):
            logger.warning(
                "Tunnel %s: port %s still has listeners %s after cleanup; "
                "not starting another kubectl (wait for port release)",
                spec.name,
                spec.probe_port,
                _all_listener_pids(spec.probe_port),
            )
            return None

        try:
            proc = _start_port_forward(spec, kubeconfig)
        except RuntimeError as exc:
            logger.error("Tunnel %s repair failed to start kubectl: %s", spec.name, exc)
            return None

        _processes_by_name[spec.name] = _TunnelRuntime(proc=proc, external=False)
        return proc
    finally:
        _release_repair_lock(spec)


def _ensure_tunnel(spec: _TunnelSpec, kubeconfig: str) -> subprocess.Popen[bytes] | None:
    """Reuse здорового forward или repair/подъём своего."""
    if _try_reuse_healthy_forward(spec):
        runtime = _processes_by_name.get(spec.name)
        if runtime is not None and not runtime.external and runtime.proc is not None:
            return runtime.proc
        return None
    return _repair_broken_tunnel(spec, kubeconfig)


def _bootstrap_tunnels(kubeconfig: str, specs: list[_TunnelSpec]) -> None:
    for spec in specs:
        _ensure_tunnel(spec, kubeconfig)


def _tunnel_port_ready(
    _runtime: _TunnelRuntime | None,
    spec: _TunnelSpec,
) -> bool:
    """Туннель здоров: probe (TCP + HTTP для CH); мёртвый owned kubectl — нездоров."""
    if (
        _runtime is not None
        and not _runtime.external
        and _runtime.proc is not None
        and _runtime.proc.poll() is not None
    ):
        return False
    return _tunnel_probe_ready(spec)


def wait_for_dev_tunnels_ready(
    timeout_sec: float | None = None,
    specs: list[_TunnelSpec] | None = None,
) -> None:
    """Блокирует до готовности всех туннелей (probe на localhost).

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
            _postgres_select_1_smoke_check(tunnel_specs)
            _clickhouse_select_1_smoke_check(tunnel_specs)
            for spec in tunnel_specs:
                logger.info(_tunnel_ready_message(spec))
            logger.info("Dev k8s tunnels are ready on localhost")
            return
        time.sleep(_READY_POLL_INTERVAL_SEC)

    raise TimeoutError(
        "Dev k8s tunnels not ready within "
        f"{timeout_sec}s. Check kubectl access and DEV_TUNNEL_PG_RESOURCE "
        "(default svc/postgres-db-pooler, fallback pod/postgres-db-0)."
    )


def _clickhouse_select_1_smoke_check(specs: list[_TunnelSpec]) -> None:
    """Проверяет HTTP ``SELECT 1`` через локальный ClickHouse-туннель.

    Raises:
        TimeoutError: при ``DEV_TUNNEL_CH_SMOKE_STRICT=true`` (по умолчанию).
    """
    ch_spec = next((spec for spec in specs if spec.name == "clickhouse"), None)
    if ch_spec is None:
        return

    strict_mode = _str_env("DEV_TUNNEL_CH_SMOKE_STRICT", "false").lower() == "true"
    try:
        _clickhouse_http_select_1(ch_spec.probe_port, _ch_smoke_timeout_sec())
    except OSError as exc:
        message = (
            "Dev k8s tunnel probe passed but ClickHouse smoke SELECT 1 failed on "
            f"127.0.0.1:{ch_spec.probe_port} via {ch_spec.resource}: {exc}"
        )
        if strict_mode:
            raise TimeoutError(message) from exc
        logger.warning(
            "%s; continuing because DEV_TUNNEL_CH_SMOKE_STRICT=false",
            message,
        )
        return
    logger.info(
        "ClickHouse smoke OK: SELECT 1 on 127.0.0.1:%s (%s)",
        ch_spec.probe_port,
        ch_spec.resource,
    )


def _postgres_select_1_smoke_check(specs: list[_TunnelSpec]) -> None:
    """Проверяет ``SELECT 1`` через локальный PgBouncer-туннель.

    Проверка выполняется только при наличии переменных подключения к БД.
    Если ``psycopg``/``psycopg2`` недоступны, проверка пропускается с warning.
    По умолчанию это best-effort проверка: ошибка не роняет приложение.
    Для строгого режима установите ``DEV_TUNNEL_PG_SMOKE_STRICT=true``.

    Raises:
        TimeoutError: TCP-туннель есть, но ``SELECT 1`` не проходит.
    """
    pg_spec = next((spec for spec in specs if spec.name == "postgres"), None)
    if pg_spec is None:
        return

    dbname = os.environ.get("POSTGRES_DBNAME", "").strip()
    user = os.environ.get("POSTGRES_USER", "").strip()
    password = os.environ.get("POSTGRES_PASSWORD", "").strip()
    sslmode = os.environ.get("POSTGRES_SSL_MODE", "").strip() or "require"
    if not dbname or not user or not password:
        logger.info(
            "Postgres smoke check skipped: set POSTGRES_DBNAME/POSTGRES_USER/POSTGRES_PASSWORD"
        )
        return

    connector: Any | None = None
    strict_mode = _str_env("DEV_TUNNEL_PG_SMOKE_STRICT", "false").lower() == "true"
    try:
        import psycopg  # type: ignore[import-not-found]

        connector = psycopg
    except ImportError:
        try:
            import psycopg2  # type: ignore[import-not-found]

            connector = psycopg2
        except ImportError:
            logger.warning("Postgres smoke check skipped: psycopg/psycopg2 not installed")
            return

    try:
        with connector.connect(  # type: ignore[union-attr]
            host="127.0.0.1",
            port=pg_spec.probe_port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=3,
            sslmode=sslmode,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as exc:
        message = (
            "Dev k8s tunnel TCP is ready, but Postgres smoke SELECT 1 failed on "
            f"127.0.0.1:{pg_spec.probe_port} via {pg_spec.resource}: {exc}"
        )
        if strict_mode:
            raise TimeoutError(message) from exc
        logger.warning("%s; continuing because DEV_TUNNEL_PG_SMOKE_STRICT=false", message)
        return
    logger.info(
        "Postgres smoke OK: SELECT 1 on 127.0.0.1:%s (%s)",
        pg_spec.probe_port,
        pg_spec.resource,
    )


def _record_restart_failure(spec: _TunnelSpec) -> bool:
    """Учитывает неудачный restart; True если лимит ещё не исчерпан."""
    global _consecutive_restart_failures
    count = _consecutive_restart_failures.get(spec.name, 0) + 1
    _consecutive_restart_failures[spec.name] = count
    max_restarts = _max_tunnel_restarts()
    if count <= max_restarts:
        return True
    logger.error(
        "Tunnel %s restart limit exceeded (%s/%s): port %s still unhealthy. "
        "Check kubectl access to %s/%s or stop stale forward manually.",
        spec.name,
        count,
        max_restarts,
        spec.probe_port,
        spec.namespace,
        spec.resource,
    )
    return False


def _clear_restart_failure(spec: _TunnelSpec) -> None:
    _consecutive_restart_failures.pop(spec.name, None)


def _monitor_loop(
    kubeconfig: str,
    specs: list[_TunnelSpec],
    *,
    bootstrap: bool,
) -> None:
    """Watchdog: healthy forward не трогает; при probe FAIL — repair.

    Args:
        bootstrap: при True сначала поднимает туннели (порты ещё не были готовы).
    """
    try:
        if bootstrap:
            _bootstrap_tunnels(kubeconfig, specs)
            time.sleep(_STARTUP_WAIT_SEC)

        while True:
            time.sleep(_MONITOR_INTERVAL_SEC)
            for spec in specs:
                runtime = _processes_by_name.get(spec.name)
                if _try_reuse_healthy_forward(spec):
                    _clear_restart_failure(spec)
                    continue

                if (
                    runtime is not None
                    and not runtime.external
                    and runtime.proc is not None
                    and runtime.proc.poll() is not None
                ):
                    _log_tunnel_exit(spec, runtime.proc)

                if not _record_restart_failure(spec):
                    continue

                logger.warning(
                    "Tunnel %s probe failed, repair scheduled (external=%s, attempt=%s)",
                    spec.name,
                    runtime.external if runtime else None,
                    _consecutive_restart_failures.get(spec.name),
                )
                _repair_broken_tunnel(spec, kubeconfig)
                time.sleep(_STARTUP_WAIT_SEC)
    finally:
        _stop_owned_tunnels(reason="monitor thread exit")


def _shutdown_signal_handler(signum: int, _frame: object | None) -> None:
    """Останавливает owned kubectl и пробрасывает стандартное исключение Python.

    SIGINT → ``KeyboardInterrupt`` (как у дефолтного handler), чтобы asyncio/pytest/debugger
    ловили привычное исключение. SIGTERM → ``SystemExit(128 + signum)``.
    """
    logger.info("Cleanup: received signal %s", signum)
    _stop_owned_tunnels(reason=f"signal {signum}")
    if signum == signal.SIGINT:
        raise KeyboardInterrupt
    raise SystemExit(128 + signum)


def _register_cleanup_once() -> None:
    global _cleanup_registered
    if _cleanup_registered:
        return
    atexit.register(lambda: _stop_owned_tunnels(reason="atexit"))
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _shutdown_signal_handler)
        except (ValueError, OSError) as exc:
            logger.debug("Signal handler not registered for %s: %s", sig, exc)
    _cleanup_registered = True


def _dev_tunnels_enabled() -> bool:
    """True, если разрешён kubectl port-forward (явный opt-in)."""
    return _str_env("DEV_TUNNELS_ENABLED", "false").lower() == "true"


def start_dev_tunnels_monitor(*, wait_ready: bool = True) -> None:
    """Идемпотентно обеспечивает port-forward для локальной разработки.

    Без ``DEV_TUNNELS_ENABLED=true`` — no-op (приложение не поднимает туннели).

    Несколько Python-процессов: здоровый forward другого процесса переиспользуется
    (reuse + smoke), kubectl не поднимается и чужие PID не завершаются.
    Watchdog в каждом процессе только чинит probe FAIL.

    Проверка kubeconfig и ``_tunnel_specs()`` выполняются под ``_monitor_lock``,
    чтобы параллельные вызовы не гонялись с idempotency-guard и не поднимали
    ``FileNotFoundError`` у одного caller'а, пока другой уже стартовал monitor.

    Args:
        wait_ready: дождаться probe на localhost перед возвратом.
    """
    if not _dev_tunnels_enabled():
        logger.info(
            "Dev k8s tunnels skipped (DEV_TUNNELS_ENABLED is not true). "
            "Use external DB hosts in .env or scripts/dev-tunnels.ps1"
        )
        return

    global _monitor_started

    kubeconfig = ""
    specs: list[_TunnelSpec] = []
    monitor_bootstrap = False
    start_monitor_thread = False
    wait_specs_after_lock: list[_TunnelSpec] | None = None

    with _monitor_lock:
        if _monitor_started:
            if wait_ready:
                wait_specs_after_lock = _tunnel_specs()
        else:
            kubeconfig = str(_configured_kubeconfig_path())
            specs = _tunnel_specs()

            if _ports_ready(specs):
                logger.info(
                    "All dev tunnel ports already forwarded and healthy; "
                    "this process will reuse them (no new kubectl)"
                )
                for spec in specs:
                    _try_reuse_healthy_forward(spec)
                monitor_bootstrap = False
            else:
                monitor_bootstrap = True

            _monitor_started = True
            start_monitor_thread = True
            if wait_ready and not monitor_bootstrap:
                wait_specs_after_lock = specs

    if wait_specs_after_lock is not None:
        wait_for_dev_tunnels_ready(specs=wait_specs_after_lock)
        if not start_monitor_thread:
            return

    if not start_monitor_thread:
        return

    _register_cleanup_once()
    thread = threading.Thread(
        target=_monitor_loop,
        args=(kubeconfig, specs),
        kwargs={"bootstrap": monitor_bootstrap},
        name="dev-k8s-tunnels",
        daemon=True,
    )
    thread.start()
    mode = "bootstrap" if monitor_bootstrap else "reuse-only"
    logger.info(
        "Dev k8s tunnels monitor started (%s, kubeconfig=%s, PG=%s, CH HTTP=%s)",
        mode,
        kubeconfig,
        specs[0].probe_port,
        specs[1].probe_port,
    )
    if wait_ready and monitor_bootstrap:
        wait_for_dev_tunnels_ready(specs=specs)


def ensure_dev_tunnels(*, wait_ready: bool = True) -> None:
    """Публичный helper для локальных entrypoint-скриптов."""
    start_dev_tunnels_monitor(wait_ready=wait_ready)
