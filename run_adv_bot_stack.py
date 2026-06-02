"""Локальный supervisor prod-стека adv-bot.

Зеркалирует deployment'ы namespace ``prod-adv-bot``:
``run-update-active-shop-ids``, ``run-shop-update-worker``, ``adv-bot-updater``,
``wb-sky-bot``, ``adv-bot-asq-worker``.

Запуск::

    poetry run python run_adv_bot_stack.py

Порядок старта: active shop ids → пауза (bootstrap) → shop worker → updater, bot, ARQ.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
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

ServiceGroup = Literal["bootstrap", "core", "parallel"]
START_ORDER: tuple[ServiceGroup, ...] = ("bootstrap", "core", "parallel")


@dataclass(frozen=True)
class ServiceSpec:
    """Описание долгоживущего процесса, соответствующего k8s deployment."""

    name: str
    argv: tuple[str, ...]
    group: ServiceGroup
    k8s_deployment: str


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


@dataclass
class ManagedProcess:
    """Запущенный дочерний процесс с метаданными для supervisor."""

    spec: ServiceSpec
    process: subprocess.Popen[bytes] | None = None
    restart_count: int = 0


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


def _popen_kwargs(separate_windows: bool) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "cwd": REPO_ROOT,
        "env": os.environ.copy(),
    }
    if separate_windows and os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    return kwargs


def start_process(
    spec: ServiceSpec,
    *,
    separate_windows: bool,
) -> subprocess.Popen[bytes]:
    """Стартует один дочерний процесс."""
    logger.info(
        "Запуск %s (k8s: %s): %s",
        spec.name,
        spec.k8s_deployment,
        " ".join(spec.argv),
    )
    return subprocess.Popen(spec.argv, **_popen_kwargs(separate_windows))


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
            "Процесс %s не завершился за %s с, kill",
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
            entry.process = start_process(spec, separate_windows=separate_windows)

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
        description="Локальный supervisor prod-стека adv-bot (зеркало prod-adv-bot k8s)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Показать сервисы и выйти",
    )
    parser.add_argument(
        "--only",
        metavar="NAMES",
        help="Запустить только перечисленные сервисы (через запятую)",
    )
    parser.add_argument(
        "--exclude",
        metavar="NAMES",
        default="",
        help="Исключить сервисы (через запятую)",
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
        help=f"Пауза после bootstrap-фазы перед core/parallel (default: {DEFAULT_BOOTSTRAP_SEC})",
    )
    parser.add_argument(
        "--separate-windows",
        action="store_true",
        help="На Windows: отдельная консоль на каждый процесс",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа supervisor."""
    args = build_arg_parser().parse_args(argv)

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

    logger.info(
        "Старт стека (%s): %s",
        len(selected),
        ", ".join(spec.name for spec in selected),
    )
    try:
        run_supervisor(
            selected,
            bootstrap_sec=args.bootstrap_sec,
            separate_windows=args.separate_windows,
            auto_restart=not args.no_restart,
        )
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
