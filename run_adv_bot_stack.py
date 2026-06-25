"""Локальный supervisor prod-стека adv-bot.

Зеркалирует deployment'ы namespace ``prod-adv-bot``:
``run-update-active-shop-ids``, ``run-shop-update-worker``, ``adv-bot-updater``,
``wb-sky-bot``, ``adv-bot-asq-worker``.

Запуск локально::

    poetry run python run_adv_bot_stack.py

Порядок старта:
1. проверка, что запуск только локальный;
2. kubectl port-forward PostgreSQL/pgbouncer;
3. ожидание доступности локального порта БД;
4. active shop ids;
5. пауза bootstrap;
6. shop worker;
7. updater, bot, ARQ.

Важно:
- этот файл НЕ предназначен для запуска внутри Kubernetes;
- port-forward включён только для локального запуска;
- если окружение похоже на production/k8s, supervisor завершится с ошибкой.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import dotenv

from python_modules.logger import setup_logging

dotenv.load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent

DEFAULT_BOOTSTRAP_SEC = 15.0
SUPERVISOR_POLL_SEC = 2.0
SHUTDOWN_WAIT_SEC = 10.0

DEFAULT_K8S_NAMESPACE = "prod-adv-bot"
DEFAULT_POSTGRES_K8S_TARGET = "svc/postgres-db-pooler"
DEFAULT_POSTGRES_LOCAL_HOST = "127.0.0.1"
DEFAULT_POSTGRES_LOCAL_PORT = 5433
DEFAULT_POSTGRES_REMOTE_PORT = 5432
DEFAULT_PORT_WAIT_SEC = 45.0

ServiceGroup = Literal["bootstrap", "core", "parallel"]
START_ORDER: tuple[ServiceGroup, ...] = ("bootstrap", "core", "parallel")


@dataclass(frozen=True)
class ServiceSpec:
    """Описание долгоживущего процесса, соответствующего k8s deployment."""

    name: str
    argv: tuple[str, ...]
    group: ServiceGroup
    k8s_deployment: str


@dataclass
class ManagedProcess:
    """Запущенный дочерний процесс с метаданными для supervisor."""

    spec: ServiceSpec
    process: subprocess.Popen[bytes] | None = None
    restart_count: int = 0


@dataclass
class ManagedForward:
    """Запущенный kubectl port-forward."""

    name: str
    process: subprocess.Popen[bytes] | None
    local_host: str
    local_port: int
    target: str
    external: bool = False


def _python_script(script_name: str) -> tuple[str, ...]:
    return (sys.executable, str(REPO_ROOT / script_name))


def _arq_worker_argv() -> tuple[str, ...]:
    return (
        sys.executable,
        "-m",
        "arq",
        "app.arq_workers.workers.WorkerSettings",
    )


DEFAULT_SERVICES: tuple[ServiceSpec, ...] = (
    ServiceSpec(
        name="active_shop_ids",
        argv=_python_script("run_update_active_shop_ids.py"),
        group="bootstrap",
        k8s_deployment="run-update-active-shop-ids",
    ),
    ServiceSpec(
        name="shop_worker",
        argv=_python_script("run_shop_update_worker.py"),
        group="core",
        k8s_deployment="run-shop-update-worker",
    ),
    ServiceSpec(
        name="updater",
        argv=_python_script("updater.py"),
        group="parallel",
        k8s_deployment="adv-bot-updater",
    ),
    ServiceSpec(
        name="client_bot",
        argv=_python_script("client_bot_run.py"),
        group="parallel",
        k8s_deployment="wb-sky-bot",
    ),
    ServiceSpec(
        name="arq_worker",
        argv=_arq_worker_argv(),
        group="parallel",
        k8s_deployment="adv-bot-asq-worker",
    ),
)


def _env_value(name: str) -> str:
    return os.getenv(name, "").strip().lower()


def is_probably_kubernetes() -> bool:
    """Определяет запуск внутри pod'а.

    Это защита от случайного запуска локального supervisor в k8s.
    """
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return True
    if Path("/var/run/secrets/kubernetes.io/serviceaccount").exists():
        return True
    return False


def is_local_environment() -> bool:
    """Разрешает запуск только для local/dev окружения.

    Поддерживаем несколько частых имён переменных, чтобы не ломать текущий .env.
    """
    values = {
        _env_value("APP_ENV"),
        _env_value("ENV"),
        _env_value("ENVIRONMENT"),
        _env_value("WB_SKY_ENV"),
        _env_value("RUN_ENV"),
    }
    values.discard("")

    if not values:
        # Для локального запуска часто env вообще не задан.
        return True

    return bool(values & {"local", "dev", "development"})


def assert_local_only(*, allow_non_local: bool) -> None:
    """Жёсткий guard: этот supervisor только для локали."""
    if allow_non_local:
        logger.warning(
            "Флаг --allow-non-local включён. Локальный guard отключён вручную."
        )
        return

    if is_probably_kubernetes():
        raise RuntimeError(
            "run_adv_bot_stack.py нельзя запускать внутри Kubernetes/pod. "
            "Это локальный supervisor с kubectl port-forward."
        )

    if not is_local_environment():
        raise RuntimeError(
            "Окружение не похоже на local/dev. "
            "Этот файл разрешён только для локального запуска. "
            "Поставь APP_ENV=local или ENVIRONMENT=local."
        )


def is_tcp_open(host: str, port: int, *, timeout_sec: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except OSError:
        return False


def wait_tcp_port(
    host: str,
    port: int,
    *,
    timeout_sec: float,
    process: subprocess.Popen[bytes] | None = None,
    process_name: str = "process",
) -> None:
    """Ждёт, пока локальный TCP-порт станет доступен.

    Если передан process и он умер раньше порта — падаем сразу.
    """
    deadline = time.monotonic() + timeout_sec
    last_return_code: int | None = None

    while time.monotonic() < deadline:
        if is_tcp_open(host, port):
            return

        if process is not None:
            return_code = process.poll()
            if return_code is not None:
                last_return_code = return_code
                break

        time.sleep(0.5)

    if last_return_code is not None:
        raise RuntimeError(
            f"{process_name} завершился до открытия порта "
            f"{host}:{port}, exit_code={last_return_code}"
        )

    raise RuntimeError(
        f"Порт {host}:{port} не стал доступен за {timeout_sec:.1f} с"
    )


def build_local_child_env(
    *,
    enable_postgres_forward: bool,
    postgres_host: str,
    postgres_port: int,
) -> dict[str, str]:
    """Окружение для дочерних процессов.

    Не трогаем DATABASE_URL, потому что неизвестно, как именно проект собирает DSN.
    Но прокидываем стандартные host/port переменные, если код читает их отдельно.
    """
    env = dict(os.environ)

    if enable_postgres_forward:
        env.setdefault("APP_ENV", "local")
        env.setdefault("ENVIRONMENT", "local")

        env["POSTGRES_HOST"] = postgres_host
        env["POSTGRES_PORT"] = str(postgres_port)
        env["PGHOST"] = postgres_host
        env["PGPORT"] = str(postgres_port)

    return env


def start_postgres_port_forward(
    *,
    namespace: str,
    target: str,
    local_host: str,
    local_port: int,
    remote_port: int,
    wait_sec: float,
) -> ManagedForward:
    """Стартует kubectl port-forward для PostgreSQL/pgbouncer."""
    if is_tcp_open(local_host, local_port):
        logger.info(
            "Postgres port-forward already available on %s:%s; reusing existing listener",
            local_host,
            local_port,
        )
        return ManagedForward(
            name="postgres",
            process=None,
            local_host=local_host,
            local_port=local_port,
            target=target,
            external=True,
        )

    argv = (
        "kubectl",
        "-n",
        namespace,
        "port-forward",
        target,
        f"{local_port}:{remote_port}",
        "--address",
        local_host,
    )

    logger.info("Запуск postgres port-forward: %s", " ".join(argv))

    process = subprocess.Popen(
        argv,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    wait_tcp_port(
        local_host,
        local_port,
        timeout_sec=wait_sec,
        process=process,
        process_name="postgres port-forward",
    )

    logger.info(
        "Postgres port-forward готов: %s:%s -> %s:%s",
        local_host,
        local_port,
        target,
        remote_port,
    )

    return ManagedForward(
        name="postgres",
        process=process,
        local_host=local_host,
        local_port=local_port,
        target=target,
    )


def stop_forward(
    forward: ManagedForward,
    *,
    wait_sec: float = SHUTDOWN_WAIT_SEC,
) -> None:
    """Останавливает kubectl port-forward."""
    if forward.external:
        logger.info(
            "Skip stopping external port-forward %s: %s:%s -> %s",
            forward.name,
            forward.local_host,
            forward.local_port,
            forward.target,
        )
        return

    proc = forward.process
    if proc is None or proc.poll() is not None:
        return

    logger.info(
        "Остановка port-forward %s: %s:%s -> %s",
        forward.name,
        forward.local_host,
        forward.local_port,
        forward.target,
    )

    try:
        proc.terminate()
    except OSError:
        logger.exception("terminate() не удался для port-forward %s", forward.name)
        return

    try:
        proc.wait(timeout=wait_sec)
        return
    except subprocess.TimeoutExpired:
        logger.warning(
            "port-forward %s не завершился за %.1f с, kill",
            forward.name,
            wait_sec,
        )

    try:
        proc.kill()
        proc.wait(timeout=5)
    except OSError:
        logger.exception("kill() не удался для port-forward %s", forward.name)


def filter_services(
    services: Sequence[ServiceSpec],
    *,
    only: frozenset[str] | None,
    exclude: frozenset[str],
) -> tuple[ServiceSpec, ...]:
    """Отбирает сервисы по ``--only`` / ``--exclude``, сохраняя порядок DEFAULT_SERVICES."""
    known = {spec.name for spec in services}

    if only is not None:
        unknown = only - known
        if unknown:
            raise ValueError(
                f"Неизвестные сервисы в --only: {sorted(unknown)}. "
                f"Доступны: {sorted(known)}"
            )

    result: list[ServiceSpec] = []
    for spec in services:
        if only is not None and spec.name not in only:
            continue
        if spec.name in exclude:
            continue
        result.append(spec)

    if not result:
        raise ValueError("После фильтрации не осталось сервисов для запуска")

    return tuple(result)


def services_in_start_order(services: Sequence[ServiceSpec]) -> list[ServiceSpec]:
    """Сортирует выбранные сервисы по фазам bootstrap → core → parallel."""
    by_group: dict[ServiceGroup, list[ServiceSpec]] = {
        group: [] for group in START_ORDER
    }

    for spec in services:
        by_group[spec.group].append(spec)

    ordered: list[ServiceSpec] = []
    for group in START_ORDER:
        ordered.extend(by_group[group])

    return ordered


def start_process(
    spec: ServiceSpec,
    *,
    separate_windows: bool,
    env: dict[str, str],
) -> subprocess.Popen[bytes]:
    """Стартует один дочерний процесс."""
    logger.info(
        "Запуск %s (k8s: %s): %s",
        spec.name,
        spec.k8s_deployment,
        " ".join(spec.argv),
    )

    if separate_windows and os.name == "nt":
        return subprocess.Popen(
            spec.argv,
            cwd=REPO_ROOT,
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

    return subprocess.Popen(spec.argv, cwd=REPO_ROOT, env=env)


def stop_process(
    managed: ManagedProcess,
    *,
    wait_sec: float = SHUTDOWN_WAIT_SEC,
) -> None:
    """Останавливает дочерний процесс: terminate → wait → kill."""
    proc = managed.process
    if proc is None or proc.poll() is not None:
        return

    try:
        proc.terminate()
    except OSError:
        logger.exception("terminate() не удался для %s", managed.spec.name)
        return

    try:
        proc.wait(timeout=wait_sec)
        return
    except subprocess.TimeoutExpired:
        logger.warning(
            "Процесс %s не завершился за %.1f с, kill",
            managed.spec.name,
            wait_sec,
        )

    try:
        proc.kill()
        proc.wait(timeout=5)
    except OSError:
        logger.exception("kill() не удался для %s", managed.spec.name)


def staggered_start(
    managed: dict[str, ManagedProcess],
    ordered_specs: Sequence[ServiceSpec],
    *,
    bootstrap_sec: float,
    separate_windows: bool,
    env: dict[str, str],
) -> None:
    """Стартует сервисы по фазам: bootstrap → sleep → core → parallel."""
    specs_by_group: dict[ServiceGroup, list[ServiceSpec]] = {
        group: [] for group in START_ORDER
    }

    for spec in ordered_specs:
        specs_by_group[spec.group].append(spec)

    def _start_group(group: ServiceGroup) -> None:
        for spec in specs_by_group[group]:
            entry = managed[spec.name]
            entry.process = start_process(
                spec,
                separate_windows=separate_windows,
                env=env,
            )

    if specs_by_group["bootstrap"]:
        _start_group("bootstrap")

        if specs_by_group["core"] or specs_by_group["parallel"]:
            logger.info(
                "Ожидание bootstrap %.1f с перед следующими сервисами",
                bootstrap_sec,
            )
            time.sleep(bootstrap_sec)

    if specs_by_group["core"]:
        _start_group("core")

    if specs_by_group["parallel"]:
        _start_group("parallel")


def run_supervisor(
    services: Sequence[ServiceSpec],
    *,
    bootstrap_sec: float,
    separate_windows: bool,
    auto_restart: bool,
    child_env: dict[str, str],
) -> None:
    """Запускает стек и при ``auto_restart`` перезапускает упавшие процессы."""
    ordered = services_in_start_order(services)
    managed: dict[str, ManagedProcess] = {
        spec.name: ManagedProcess(spec=spec) for spec in ordered
    }

    shutdown_requested = False

    def _handle_shutdown(signum: int, _frame: object | None) -> None:
        nonlocal shutdown_requested
        logger.info("Получен сигнал %s, остановка стека...", signum)
        shutdown_requested = True

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    try:
        staggered_start(
            managed,
            ordered,
            bootstrap_sec=bootstrap_sec,
            separate_windows=separate_windows,
            env=child_env,
        )

        if not auto_restart:
            logger.info(
                "Режим --no-restart: ожидание завершения дочерних процессов"
            )
            while not shutdown_requested:
                if all(
                    entry.process is not None and entry.process.poll() is not None
                    for entry in managed.values()
                ):
                    break
                time.sleep(SUPERVISOR_POLL_SEC)
            return

        while not shutdown_requested:
            for entry in managed.values():
                proc = entry.process
                if proc is None:
                    continue
                if proc.poll() is None:
                    continue

                entry.restart_count += 1
                logger.error(
                    "Процесс %s завершился (exit_code=%s), перезапуск #%s",
                    entry.spec.name,
                    proc.returncode,
                    entry.restart_count,
                )

                entry.process = start_process(
                    entry.spec,
                    separate_windows=separate_windows,
                    env=child_env,
                )

            time.sleep(SUPERVISOR_POLL_SEC)

    finally:
        logger.info("Остановка всех сервисов стека...")
        for entry in managed.values():
            stop_process(entry)


def print_service_list(services: Sequence[ServiceSpec]) -> None:
    """Печатает таблицу сервисов для ``--list``."""
    for spec in services:
        print(
            f"{spec.name:16} group={spec.group:10} "
            f"k8s={spec.k8s_deployment}"
        )
        print(f"  {' '.join(spec.argv)}")


def _parse_name_set(raw: str | None) -> frozenset[str] | None:
    if raw is None:
        return None

    names = {part.strip() for part in raw.split(",") if part.strip()}
    return frozenset(names) if names else frozenset()


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI для локального supervisor."""
    parser = argparse.ArgumentParser(
        description="Локальный supervisor prod-стека adv-bot с kubectl port-forward",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="Показать сервисы и выйти",
    )
    parser.add_argument(
        "--only",
        metavar="NAMES",
        help="Запустить только перечисленные сервисы через запятую",
    )
    parser.add_argument(
        "--exclude",
        metavar="NAMES",
        default="",
        help="Исключить сервисы через запятую",
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Не перезапускать упавшие процессы",
    )
    parser.add_argument(
        "--bootstrap-sec",
        type=float,
        default=DEFAULT_BOOTSTRAP_SEC,
        help=(
            "Пауза после bootstrap-фазы перед core/parallel "
            f"(default: {DEFAULT_BOOTSTRAP_SEC})"
        ),
    )
    parser.add_argument(
        "--separate-windows",
        action="store_true",
        help="На Windows: отдельная консоль на каждый процесс",
    )

    parser.add_argument(
        "--no-port-forward",
        action="store_true",
        help="Не запускать kubectl port-forward PostgreSQL",
    )
    parser.add_argument(
        "--k8s-namespace",
        default=DEFAULT_K8S_NAMESPACE,
        help=f"k8s namespace для port-forward (default: {DEFAULT_K8S_NAMESPACE})",
    )
    parser.add_argument(
        "--postgres-target",
        default=DEFAULT_POSTGRES_K8S_TARGET,
        help=(
            "k8s target для PostgreSQL port-forward "
            f"(default: {DEFAULT_POSTGRES_K8S_TARGET})"
        ),
    )
    parser.add_argument(
        "--postgres-local-host",
        default=DEFAULT_POSTGRES_LOCAL_HOST,
        help=(
            "Локальный host для PostgreSQL port-forward "
            f"(default: {DEFAULT_POSTGRES_LOCAL_HOST})"
        ),
    )
    parser.add_argument(
        "--postgres-local-port",
        type=int,
        default=DEFAULT_POSTGRES_LOCAL_PORT,
        help=(
            "Локальный порт PostgreSQL port-forward "
            f"(default: {DEFAULT_POSTGRES_LOCAL_PORT})"
        ),
    )
    parser.add_argument(
        "--postgres-remote-port",
        type=int,
        default=DEFAULT_POSTGRES_REMOTE_PORT,
        help=(
            "Удалённый порт PostgreSQL/pgbouncer "
            f"(default: {DEFAULT_POSTGRES_REMOTE_PORT})"
        ),
    )
    parser.add_argument(
        "--port-wait-sec",
        type=float,
        default=DEFAULT_PORT_WAIT_SEC,
        help=(
            "Сколько ждать открытия локального порта "
            f"(default: {DEFAULT_PORT_WAIT_SEC})"
        ),
    )
    parser.add_argument(
        "--allow-non-local",
        action="store_true",
        help="Опасно: отключить local-only guard",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа supervisor."""
    args = build_arg_parser().parse_args(argv)

    try:
        assert_local_only(allow_non_local=args.allow_non_local)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 2

    only = _parse_name_set(args.only)
    exclude = _parse_name_set(args.exclude) or frozenset()

    try:
        selected = filter_services(
            DEFAULT_SERVICES,
            only=only,
            exclude=exclude,
        )
    except ValueError as exc:
        logger.error("%s", exc)
        return 2

    if args.list:
        print_service_list(selected)
        return 0

    forwards: list[ManagedForward] = []

    enable_postgres_forward = not args.no_port_forward

    child_env = build_local_child_env(
        enable_postgres_forward=enable_postgres_forward,
        postgres_host=args.postgres_local_host,
        postgres_port=args.postgres_local_port,
    )

    logger.info(
        "Старт локального стека (%s): %s",
        len(selected),
        ", ".join(spec.name for spec in selected),
    )

    try:
        if enable_postgres_forward:
            forwards.append(
                start_postgres_port_forward(
                    namespace=args.k8s_namespace,
                    target=args.postgres_target,
                    local_host=args.postgres_local_host,
                    local_port=args.postgres_local_port,
                    remote_port=args.postgres_remote_port,
                    wait_sec=args.port_wait_sec,
                )
            )
        else:
            logger.warning(
                "PostgreSQL port-forward отключён. "
                "Проверяю только доступность %s:%s",
                args.postgres_local_host,
                args.postgres_local_port,
            )
            wait_tcp_port(
                args.postgres_local_host,
                args.postgres_local_port,
                timeout_sec=args.port_wait_sec,
                process=None,
                process_name="external postgres",
            )

        run_supervisor(
            selected,
            bootstrap_sec=args.bootstrap_sec,
            separate_windows=args.separate_windows,
            auto_restart=not args.no_restart,
            child_env=child_env,
        )

    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    finally:
        for forward in reversed(forwards):
            stop_forward(forward)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
