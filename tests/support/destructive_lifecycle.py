"""Session-owned lifecycle для destructive PG/ClickHouse integration tests.

Гарантии:
* Compose up/down — не более одного раза на pytest process;
* PG schema / CH DDL — не более одного раза;
* validation/marker/opt-in/tunnels — до любых Docker/engine/client side effects;
* selective services: PG-only / CH-only / mixed;
* deterministic policy errors — NON_RETRYABLE (без sleep/retry);
* data reset — function-scoped, отдельно от schema bootstrap;
* sync schema runners вызываемые из async fixtures — через
  ``run_awaitable_from_sync`` (не nested ``asyncio.run``).

Не выполняет real Docker/PG/CH сам по себе без injected runners —
удобно для mock-only unit coverage.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, TypeVar

_T = TypeVar("_T")


def coerce_compose_stream(raw: object) -> str:
    """Нормализовать stdout/stderr compose/sync_run до str.

    Утечки ``MagicMock`` из unit-suite не должны доходить до ``re.sub`` в
    conftest scrub при teardown.
    """
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw).decode("utf-8", errors="replace")
    return ""


def coerce_compose_exit_code(raw: object) -> int | None:
    """Нормализовать returncode compose/sync_run до int.

    ``None`` означает pollution (``MagicMock`` / non-int): нельзя трактовать
    как ненулевой exit и поднимать ``DOCKER_STAGE=cleanup`` на случайном
    последнем тесте сессии.

    Args:
        raw: значение returncode из ``sync_run``.

    Returns:
        int exit code, либо ``None`` если значение не int (mock leak).
    """
    if isinstance(raw, bool):
        # bool — subclass int; для exit code не используем.
        return None
    if isinstance(raw, int):
        return raw
    return None


def run_awaitable_from_sync(awaitable: Awaitable[_T]) -> _T:
    """Выполнить awaitable из sync-кода, даже если уже есть running event loop.

    Session schema bootstrap (``init_pg_schema`` / ``init_ch_schema``) вызывается
    из sync ``TestInfraLifecycle.ensure_resources``, а тот — из async fixtures
    (``clickhouse_client``, …). Прямой ``asyncio.run`` в running loop →
    ``RuntimeError``. При отсутствии loop — обычный ``asyncio.run``; при
    наличии — отдельный thread + новый loop (без ``nest_asyncio``).

    Args:
        awaitable: корутина / awaitable для однократного запуска.

    Returns:
        Результат awaitable.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    def _in_thread() -> _T:
        return asyncio.run(awaitable)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_in_thread).result()

# --- Fixture / resource registries -------------------------------------------------

LIVE_PG_FIXTURE_NAMES: frozenset[str] = frozenset(
    {
        "setup_test_database",
        "async_engine",
        "async_session",
        "postgres_session",
        "reset_postgres_test_data",
        "pg_data_reset",
        # Note: ``complex_adv`` / ``sm_generator`` omitted — часто override'ятся
        # локальными mock fixtures; реальный PG path всё равно тянет
        # postgres_session/async_engine в fixturenames.
    }
)

LIVE_CH_FIXTURE_NAMES: frozenset[str] = frozenset(
    {
        "clickhouse_client",
        "reset_clickhouse_test_data",
        "ch_data_reset",
    }
)

LIVE_COMPOSE_FIXTURE_NAMES: frozenset[str] = LIVE_PG_FIXTURE_NAMES | LIVE_CH_FIXTURE_NAMES

COMPOSE_SERVICE_PG: str = "test_db"
COMPOSE_SERVICE_CH: str = "test_clickhouse"

TEST_INFRA_REUSE_ENV: str = "TEST_INFRA_REUSE"


class RetryClass(str, Enum):
    """Классификация ошибок lifecycle: retry только для transient."""

    NON_RETRYABLE = "non_retryable"
    TRANSIENT = "transient"


@dataclass(frozen=True, slots=True)
class TestResourceNeeds:
    """Какие disposable ресурсы нужны выбранному набору tests."""

    __test__: ClassVar[bool] = False

    needs_pg: bool = False
    needs_clickhouse: bool = False

    @property
    def needs_compose(self) -> bool:
        """True если нужен хотя бы один Compose service."""
        return self.needs_pg or self.needs_clickhouse

    @property
    def compose_services(self) -> tuple[str, ...]:
        """Имена compose services в стабильном порядке."""
        services: list[str] = []
        if self.needs_pg:
            services.append(COMPOSE_SERVICE_PG)
        if self.needs_clickhouse:
            services.append(COMPOSE_SERVICE_CH)
        return tuple(services)

    def union(self, other: "TestResourceNeeds") -> "TestResourceNeeds":
        """Объединить потребности (для session selection)."""
        return TestResourceNeeds(
            needs_pg=self.needs_pg or other.needs_pg,
            needs_clickhouse=self.needs_clickhouse or other.needs_clickhouse,
        )


@dataclass
class TestInfraSessionState:
    """Счётчики и флаги одного pytest process для destructive infra."""

    __test__: ClassVar[bool] = False

    requested_services: set[str] = field(default_factory=set)
    started_services: set[str] = field(default_factory=set)
    compose_started_by_pytest: bool = False
    compose_up_count: int = 0
    compose_down_count: int = 0
    pg_ready: bool = False
    clickhouse_ready: bool = False
    pg_schema_initialized: bool = False
    clickhouse_schema_initialized: bool = False
    pg_schema_init_count: int = 0
    clickhouse_schema_init_count: int = 0
    pg_data_reset_count: int = 0
    clickhouse_data_reset_count: int = 0
    health_check_counts: dict[str, int] = field(default_factory=dict)
    reuse_mode: bool = False
    primary_failure: BaseException | None = None


def discover_resource_needs_from_fixturenames(
    fixturenames: Iterable[str],
) -> TestResourceNeeds:
    """Вычислить resource needs по именам fixtures item'а."""
    names = set(fixturenames)
    return TestResourceNeeds(
        needs_pg=bool(names & LIVE_PG_FIXTURE_NAMES),
        needs_clickhouse=bool(names & LIVE_CH_FIXTURE_NAMES),
    )


def discover_session_resource_needs(items: Sequence[Any]) -> TestResourceNeeds:
    """Union resource needs по всем collected items."""
    needs = TestResourceNeeds()
    for item in items:
        fixturenames = getattr(item, "fixturenames", ()) or ()
        needs = needs.union(discover_resource_needs_from_fixturenames(fixturenames))
    return needs


def item_uses_live_fixtures(item: Any) -> bool:
    """True если item прямо/транзитивно использует live PG/CH fixture."""
    fixturenames = set(getattr(item, "fixturenames", ()) or ())
    return bool(fixturenames & LIVE_COMPOSE_FIXTURE_NAMES)


def is_reuse_mode_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    """Explicit ``TEST_INFRA_REUSE=1`` — не down'ить чужие containers."""
    env = environ if environ is not None else os.environ
    raw = env.get(TEST_INFRA_REUSE_ENV)
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def classify_lifecycle_error(exc: BaseException) -> RetryClass:
    """Классифицировать ошибку: deterministic → NON_RETRYABLE."""
    if isinstance(exc, (KeyboardInterrupt, SystemExit, NotImplementedError)):
        return RetryClass.NON_RETRYABLE

    # Lazy import: pytest / domain errors may be unavailable in pure AST tests.
    try:
        import pytest

        if isinstance(exc, pytest.fail.Exception):
            return RetryClass.NON_RETRYABLE
    except Exception:  # noqa: BLE001
        pass

    try:
        from tests.support.destructive_clickhouse import DestructiveTestClickHouseError
        from tests.support.destructive_pg_dsn import DestructiveTestDatabaseError

        if isinstance(exc, (DestructiveTestDatabaseError, DestructiveTestClickHouseError)):
            return RetryClass.NON_RETRYABLE
    except Exception:  # noqa: BLE001
        pass

    if isinstance(exc, RuntimeError):
        msg = str(exc)
        deterministic_markers = (
            "DOCKER_STAGE=",
            "Docker Compose не найден",
            "command not found:",
            "network_guard internal error",
            "requires @destructive_local",
            "refuse connect",
            "refuse Docker",
            "DEV_TUNNELS_",
            "ALLOW_DESTRUCTIVE_TEST_",
            "not allowlisted",
            "forbidden",
            "opt-in",
        )
        if any(marker in msg for marker in deterministic_markers):
            return RetryClass.NON_RETRYABLE

    return RetryClass.TRANSIENT


def run_with_bounded_retry(
    operation: Callable[[], Any],
    *,
    max_attempts: int,
    sleep_fn: Callable[[float], None] = time.sleep,
    backoff_sec_fn: Callable[[int], float] | None = None,
    on_retry: Callable[[BaseException, int, float], None] | None = None,
) -> Any:
    """Выполнить operation с bounded retry только для TRANSIENT ошибок.

    Args:
        operation: sync callable.
        max_attempts: верхняя граница попыток (>=1).
        sleep_fn: injectable sleep (для unit tests).
        backoff_sec_fn: attempt (1-based) → delay seconds.
        on_retry: callback(error, attempt, backoff) перед sleep.

    Returns:
        Результат operation.

    Raises:
        Исходное исключение без retry для NON_RETRYABLE;
        последнее TRANSIENT после исчерпания бюджета.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def _default_backoff(attempt: int) -> float:
        return float(min(2 * attempt, 10))

    backoff_fn = backoff_sec_fn or _default_backoff
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except BaseException as exc:  # noqa: BLE001 — classify then decide
            last_exc = exc
            if classify_lifecycle_error(exc) is RetryClass.NON_RETRYABLE:
                raise
            if attempt >= max_attempts:
                raise
            delay = backoff_fn(attempt)
            if on_retry is not None:
                on_retry(exc, attempt, delay)
            sleep_fn(delay)
    assert last_exc is not None
    raise last_exc


@dataclass
class TestInfraLifecycle:
    """Единый session owner Compose/PG/CH bootstrap.

    Все side-effect runners inject'ятся — unit tests подменяют без Docker.
    """

    __test__: ClassVar[bool] = False

    state: TestInfraSessionState
    compose_file: str
    sync_run: Callable[..., tuple[int, str, str]]
    docker_preflight: Callable[[], list[str]]
    validate_pg: Callable[[], None]
    validate_ch: Callable[[], None]
    init_pg_schema: Callable[[], None]
    init_ch_schema: Callable[[], None]
    raise_docker_stage: Callable[..., None]
    sleep_fn: Callable[[float], None] = time.sleep
    startup_max_retries: int = 120
    startup_sleep_sec: float = 2.0
    settle_sleep_sec: float = 10.0
    init_max_retries: int = 10
    format_retry_diagnostic: Callable[..., str] | None = None
    _compose_cmd: list[str] | None = field(default=None, init=False, repr=False)

    def ensure_resources(self, needs: TestResourceNeeds) -> None:
        """Validation → selective Compose → schema bootstrap (идемпотентно)."""
        if not needs.needs_compose:
            return

        # 1) Static validation BEFORE any docker/subprocess.
        self._assert_subprocess_opt_in()
        if needs.needs_pg:
            self.validate_pg()
        if needs.needs_clickhouse:
            self.validate_ch()

        for service in needs.compose_services:
            self.state.requested_services.add(service)

        missing = [
            svc for svc in needs.compose_services if svc not in self.state.started_services
        ]
        if missing:
            self._compose_up(tuple(missing))
            for svc in missing:
                self._wait_healthy(svc)
                self.state.started_services.add(svc)

        if needs.needs_pg and not self.state.pg_schema_initialized:
            self._init_pg_with_retry()
            self.state.pg_schema_initialized = True
            self.state.pg_ready = True

        if needs.needs_clickhouse and not self.state.clickhouse_schema_initialized:
            self._init_ch_with_retry()
            self.state.clickhouse_schema_initialized = True
            self.state.clickhouse_ready = True

    def record_pg_data_reset(self) -> None:
        """Учесть function-scoped PG data reset."""
        self.state.pg_data_reset_count += 1

    def record_ch_data_reset(self) -> None:
        """Учесть function-scoped CH data reset."""
        self.state.clickhouse_data_reset_count += 1

    def teardown(self, *, primary_exception: BaseException | None = None) -> None:
        """Session teardown: compose down только если pytest сам поднимал."""
        if primary_exception is not None:
            self.state.primary_failure = primary_exception

        cleanup_error: BaseException | None = None
        try:
            if self.state.compose_started_by_pytest and self.state.compose_up_count > 0:
                if self.state.reuse_mode:
                    # Reuse: не останавливаем containers, которые могли быть внешними.
                    # Но если compose_started_by_pytest — мы всё же владеем up;
                    # reuse mode означает «не down», даже если up был нашим
                    # (explicit TEST_INFRA_REUSE=1).
                    return
                cleanup_error = self._compose_down()
        finally:
            self.state.pg_ready = False
            self.state.clickhouse_ready = False
            self.state.started_services.clear()
            self._compose_cmd = None

        if cleanup_error is not None:
            if self.state.primary_failure is None and primary_exception is None:
                raise cleanup_error
            # Не маскируем primary failure.
            print(
                f"[WARNING] Cleanup failure ignored due to primary exception: "
                f"{cleanup_error}"
            )

    def _assert_subprocess_opt_in(self) -> None:
        """Fail-closed: Docker subprocess требует ALLOW_DESTRUCTIVE_TEST_SUBPROCESS."""
        from tests.support.subprocess_guard import (
            ALLOW_DESTRUCTIVE_TEST_SUBPROCESS_ENV,
            is_destructive_subprocess_opt_in_enabled,
        )

        if not is_destructive_subprocess_opt_in_enabled():
            raise RuntimeError(
                "Destructive Compose requires explicit opt-in "
                f"{ALLOW_DESTRUCTIVE_TEST_SUBPROCESS_ENV}=1 — refuse Docker"
            )

    def _compose_up(self, services: tuple[str, ...]) -> None:
        """Compose up выбранных services (один lifecycle call-агрегат)."""
        if self._compose_cmd is None:
            self._compose_cmd = self.docker_preflight()

        compose_up_args = self._decide_up_args(services)
        reusing_external_healthy = "--force-recreate" not in compose_up_args
        rc, _out, err = self.sync_run(
            *self._compose_cmd,
            "-f",
            self.compose_file,
            *compose_up_args,
            *services,
            timeout=180,
        )
        self.state.compose_up_count += 1
        # External /opsx-test-env stack: healthy reuse must not claim pytest ownership.
        if not reusing_external_healthy:
            self.state.compose_started_by_pytest = True
        if rc != 0:
            self.raise_docker_stage(
                stage="up",
                command=(
                    *self._compose_cmd,
                    "-f",
                    self.compose_file,
                    *compose_up_args,
                    *services,
                ),
                exit_code=rc,
                stderr=err,
                owner_action=(
                    "Проверьте `docker compose -f tests/docker-compose.test.yml logs` "
                    "и исправьте конфигурацию контейнеров."
                ),
            )

    def _decide_up_args(self, services: tuple[str, ...]) -> list[str]:
        """Reuse healthy containers без force-recreate; иначе rebuild."""
        assert self._compose_cmd is not None
        all_healthy = True
        for service in services:
            _rc, cid_out, _ = self.sync_run(
                *self._compose_cmd,
                "-f",
                self.compose_file,
                "ps",
                "-q",
                service,
                timeout=10,
            )
            cid = (cid_out or "").strip()
            if not cid:
                all_healthy = False
                break
            rc_inspect, status_out, _ = self.sync_run(
                "docker",
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                cid,
                timeout=10,
            )
            status = (status_out or "").strip() if rc_inspect == 0 else ""
            is_healthy = status == "healthy" or status.endswith(" healthy")
            if rc_inspect != 0 or not is_healthy:
                all_healthy = False
                break
        if all_healthy and services:
            return ["up", "-d"]
        return ["up", "-d", "--build", "--force-recreate"]

    def _wait_healthy(self, service: str) -> None:
        """Ожидание health только для одного service, один раз."""
        assert self._compose_cmd is not None
        self.state.health_check_counts[service] = (
            self.state.health_check_counts.get(service, 0) + 1
        )
        last_health_command: tuple[str, ...] = (
            *self._compose_cmd,
            "-f",
            self.compose_file,
            "ps",
            "-q",
            service,
        )
        last_health_exit_code = 0
        last_health_stderr = ""
        container_id = ""
        for i in range(self.startup_max_retries):
            _rc_ps, cid_out, err_ps = self.sync_run(
                *self._compose_cmd,
                "-f",
                self.compose_file,
                "ps",
                "-q",
                service,
                timeout=10,
            )
            last_health_command = (
                *self._compose_cmd,
                "-f",
                self.compose_file,
                "ps",
                "-q",
                service,
            )
            last_health_exit_code = _rc_ps
            last_health_stderr = err_ps
            container_id = (cid_out or "").strip()
            if container_id:
                rc, status_out, err_inspect = self.sync_run(
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Status}} {{if .State.Health}}"
                    "{{.State.Health.Status}}{{else}}nohealth{{end}}",
                    container_id,
                    timeout=10,
                )
                last_health_command = (
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Status}} {{if .State.Health}}"
                    "{{.State.Health.Status}}{{else}}nohealth{{end}}",
                    container_id,
                )
                last_health_exit_code = rc
                last_health_stderr = err_inspect
                status = (status_out or "").strip() if rc == 0 else "unknown"
                if status.endswith(" healthy"):
                    print(f"[OK] Service {service} is healthy.")
                    if service == COMPOSE_SERVICE_PG and self.settle_sleep_sec > 0:
                        self.sleep_fn(self.settle_sleep_sec)
                    return
                print(
                    f"[WAIT] Waiting for {service}... Attempt {i + 1}/"
                    f"{self.startup_max_retries} (status: {status})"
                )
            else:
                print(
                    f"[WAIT] Waiting for {service}... Attempt {i + 1}/"
                    f"{self.startup_max_retries} (status: no container yet)"
                )
            self.sleep_fn(self.startup_sleep_sec)

        self.raise_docker_stage(
            stage="health",
            command=last_health_command,
            exit_code=last_health_exit_code,
            stderr=(
                f"{last_health_stderr} | timed out waiting for healthy status "
                f"after {self.startup_max_retries} attempts"
            ),
            owner_action=(
                f"Проверьте healthcheck/логи контейнера {service} и увеличьте "
                "ресурсы Docker при необходимости."
            ),
        )

    def _init_pg_with_retry(self) -> None:
        """PG schema bootstrap с bounded retry только для transient."""

        def _op() -> None:
            self.init_pg_schema()

        def _on_retry(exc: BaseException, attempt: int, delay: float) -> None:
            if self.format_retry_diagnostic is not None:
                print(
                    self.format_retry_diagnostic(
                        operation="Test DB init",
                        error=exc,
                        attempt=attempt,
                        max_attempts=self.init_max_retries,
                        backoff_sec=delay,
                    )
                )

        run_with_bounded_retry(
            _op,
            max_attempts=self.init_max_retries,
            sleep_fn=self.sleep_fn,
            on_retry=_on_retry,
        )
        self.state.pg_schema_init_count += 1
        print("[OK] PostgreSQL schema bootstrap complete.")

    def _init_ch_with_retry(self) -> None:
        """CH DDL bootstrap с bounded retry только для transient."""

        def _op() -> None:
            self.init_ch_schema()

        def _on_retry(exc: BaseException, attempt: int, delay: float) -> None:
            if self.format_retry_diagnostic is not None:
                print(
                    self.format_retry_diagnostic(
                        operation="ClickHouse schema init",
                        error=exc,
                        attempt=attempt,
                        max_attempts=self.init_max_retries,
                        backoff_sec=delay,
                    )
                )

        run_with_bounded_retry(
            _op,
            max_attempts=self.init_max_retries,
            sleep_fn=self.sleep_fn,
            on_retry=_on_retry,
        )
        self.state.clickhouse_schema_init_count += 1
        print("[OK] ClickHouse schema bootstrap complete.")

    def _compose_down(self) -> BaseException | None:
        """Compose down; возвращает cleanup error вместо raise при primary failure."""
        cmd = self._compose_cmd or ["docker", "compose"]
        try:
            rc_raw, _out, err = self.sync_run(
                *cmd,
                "-f",
                self.compose_file,
                "down",
                "-v",
                "--remove-orphans",
                "--timeout",
                "1",
                timeout=20,
            )
            self.state.compose_down_count += 1
            rc = coerce_compose_exit_code(rc_raw)
            if rc is None:
                # MagicMock/non-int returncode (subprocess.run pollution) —
                # не поднимать DOCKER_STAGE=cleanup на victim-тесте сессии.
                print(
                    "[WARNING] compose down returncode is non-int "
                    f"(type={type(rc_raw).__name__!r}); treating as mock "
                    "pollution, skip fail-closed cleanup raise."
                )
                return None
            if rc != 0:
                try:
                    self.raise_docker_stage(
                        stage="cleanup",
                        command=(
                            *cmd,
                            "-f",
                            self.compose_file,
                            "down",
                            "-v",
                            "--remove-orphans",
                            "--timeout",
                            "1",
                        ),
                        exit_code=rc,
                        stderr=coerce_compose_stream(err),
                        owner_action=(
                            "Проверьте права Docker/состояние daemon и повторите "
                            "cleanup вручную."
                        ),
                    )
                except BaseException as exc:  # noqa: BLE001
                    return exc
        except BaseException as exc:  # noqa: BLE001
            self.state.compose_down_count += 1
            try:
                import subprocess

                exit_code = 124 if isinstance(exc, subprocess.TimeoutExpired) else -1
            except Exception:  # noqa: BLE001
                exit_code = -1
            try:
                self.raise_docker_stage(
                    stage="cleanup",
                    command=(
                        *cmd,
                        "-f",
                        self.compose_file,
                        "down",
                        "-v",
                        "--remove-orphans",
                        "--timeout",
                        "1",
                    ),
                    exit_code=exit_code,
                    stderr=str(exc),
                    owner_action=(
                        "Проверьте доступность Docker daemon и повторите cleanup "
                        "вручную."
                    ),
                )
            except BaseException as wrapped:  # noqa: BLE001
                return wrapped
        return None
