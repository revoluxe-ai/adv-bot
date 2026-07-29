# mypy: ignore-errors
# IMPORTANT: Set environment variables BEFORE any imports that might use them!
import os

# --- Fail-closed test network + secret scrub (до app imports) -----------------
# Proxy env не должен позволять обход localhost-only guard.
for _proxy_key in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
):
    os.environ.pop(_proxy_key, None)

# Force safe placeholder credentials (не production tokens).
os.environ["BOT_TOKEN"] = "test_token_123"
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token_123"
os.environ["WEBHOOK_SECRET"] = "test_secret"
os.environ["YOOKASSA_TOKEN"] = "test_yookassa"
os.environ["WB_TEST_MODE"] = "1"
os.environ["WB_TEST_TOKEN"] = "test_wb_token"
os.environ.pop("UNISENDER_GO_API_KEY", None)
os.environ.pop("UNISENDER_GO_INTEGRATION_TEST_RECIPIENT", None)
os.environ.pop("TEST_TELEGRAM_BOT_TOKEN", None)
os.environ.pop("TEST_TELEGRAM_CHAT_ID", None)

# Устанавливаем переменные окружения для тестовой БД ДО любых app-импортов.
# 127.0.0.1: на Windows Docker Desktop localhost (::1) часто даёт WinError 64.
_TEST_PG_HOST = "127.0.0.1"
os.environ["POSTGRES_MASTER_HOST"] = _TEST_PG_HOST
os.environ["POSTGRES_REPLICA_HOST"] = _TEST_PG_HOST
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_DBNAME"] = "test_adv_bot_db"
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "test_password"
os.environ["POSTGRES_SSL_MODE"] = "disable"
os.environ["POSTGRES_SSL_INSECURE"] = "true"

# FORCE override ClickHouse settings for tests (must connect to test container, not production!)
os.environ["CLICKHOUSE_PORT"] = "8124"  # HTTP port for test ClickHouse
os.environ["CLICK_HOUSE_HOST"] = _TEST_PG_HOST  # 127.0.0.1: Windows localhost (::1) → reset
os.environ["CLICK_HOUSE_USER"] = "CLICK_HOUSE_USER"  # Username from docker-compose.test.yml
os.environ["CLICK_HOUSE_PASSWORD"] = "password"  # Password from docker-compose.test.yml

# Обязательные переменные для работы settings
os.environ.setdefault("TELEGRAM_WEB_PORT", "8080")
os.environ.setdefault("CH_MAX_THREAD", "10")
os.environ.setdefault("BIDDER_STEP_RUB", "1")
os.environ["REDIS_MASTER_HOST"] = "localhost"
os.environ["REDIS_REPLICA_HOST"] = "localhost"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ.setdefault("MIN_SUM", "0")
os.environ.setdefault("COUNT_SEMAPHORE_TO_POSTGRES", "100")  # Большое значение для тестов
os.environ.setdefault("PG_POOL_SIZE", "5")
os.environ.setdefault("PG_MAX_OVERFLOW", "10")

TEST_DB_POSTGRES_URL = (
    f"postgresql://test_user:test_password@{_TEST_PG_HOST}:5433/test_adv_bot_db"
)
os.environ["TEST_DB_POSTGRES_URL"] = TEST_DB_POSTGRES_URL

import dotenv
# Загружаем .env, но НЕ перезаписываем уже установленные переменные окружения для тестов
dotenv.load_dotenv(override=False)

# Повторно форсим test endpoints после dotenv (на случай, если ключи отсутствовали
# до load и попали из .env).
os.environ["POSTGRES_MASTER_HOST"] = _TEST_PG_HOST
os.environ["POSTGRES_REPLICA_HOST"] = _TEST_PG_HOST
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_DBNAME"] = "test_adv_bot_db"
os.environ["CLICKHOUSE_PORT"] = "8124"
os.environ["CLICK_HOUSE_HOST"] = _TEST_PG_HOST
os.environ["REDIS_MASTER_HOST"] = "localhost"
os.environ["REDIS_REPLICA_HOST"] = "localhost"
os.environ["REDIS_HOST"] = "localhost"
os.environ["BOT_TOKEN"] = "test_token_123"
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token_123"
os.environ["YOOKASSA_TOKEN"] = "test_yookassa"
# После load_dotenv(override=False) отсутствующие ключи могли вернуться из .env —
# повторный scrub + пустые placeholders, чтобы live send-тесты skip'ались.
os.environ.pop("UNISENDER_GO_API_KEY", None)
os.environ.pop("UNISENDER_GO_INTEGRATION_TEST_RECIPIENT", None)
os.environ.pop("TEST_TELEGRAM_BOT_TOKEN", None)
os.environ.pop("TEST_TELEGRAM_CHAT_ID", None)
os.environ["UNISENDER_GO_API_KEY"] = ""
os.environ["UNISENDER_GO_INTEGRATION_TEST_RECIPIENT"] = ""
for _proxy_key in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "PROXY",
):
    os.environ.pop(_proxy_key, None)

# Network guard: запрет исходящих TCP вне loopback (до создания clients).
from tests.support.network_guard import install_network_guard
from tests.support.subprocess_guard import install_subprocess_guard

install_network_guard()
install_subprocess_guard()

from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

# В тестах guard включён по умолчанию; отдельные кейсы отключают через monkeypatch.
os.environ["STATS_FRESHNESS_GUARD_ENABLED"] = "true"

# Now it's safe to import modules that use settings
import asyncio
import re
from clickhouse_connect import get_async_client
from clickhouse_connect.driver.exceptions import DatabaseError
from fakeredis import FakeRedis
import aiofiles
from dependency_injector import containers
import fakeredis
import typing
if typing.TYPE_CHECKING:
    from app.core.di.app_container import AppContainer

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


# Подставляем заглушку для app.core.wb_api.http_request до реальных импортов
import types

mod_name = "app.core.wb_api.http_request"
import importlib


import subprocess
import time
import atexit
from datetime import datetime, timedelta

import pytest

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.pool import NullPool

from app.utils.db.base import BaseTable as Base

from typing import AsyncGenerator
# Переменные окружения для тестовой БД
TEST_DB_URL = (
    f"postgresql+asyncpg://test_user:test_password@{_TEST_PG_HOST}:5433/test_adv_bot_db"
)
COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "tests", "docker-compose.test.yml")

# Глобальное хранилище для cleanup контейнеров
_DOCKER_CLEANUP_STATE = {"compose_cmd": None, "container_id": None}

# Настройки orchestration destructive integration setup.
SETUP_DB_STARTUP_MAX_RETRIES = 120
SETUP_DB_STARTUP_SLEEP_SEC = 2
SETUP_DB_INIT_MAX_RETRIES = 10
SETUP_DB_INIT_BACKOFF_MAX_SEC = 10
SETUP_DB_SETTLE_SLEEP_SEC = 10
DOCKER_DIAGNOSTIC_MAX_LEN = 600


def _create_test_async_engine(**kwargs: object):
    """Движок к тестовому Postgres в Docker; validation-before-connect.

    Требует ``ALLOW_DESTRUCTIVE_TEST_DB=1`` и запрещает DEV_TUNNELS_*.
    ``ssl=False`` для asyncpg на Windows.
    """
    from tests.support.destructive_pg_dsn import create_validated_async_engine_from_url

    connect_args = dict(kwargs.pop("connect_args", {}))  # type: ignore[arg-type]
    connect_args.setdefault("ssl", False)
    return create_validated_async_engine_from_url(
        TEST_DB_URL,
        create_async_engine_fn=create_async_engine,
        poolclass=NullPool,
        connect_args=connect_args,
        **kwargs,  # type: ignore[arg-type]
    )


def _sync_run(*args: str, timeout: float | None = None) -> tuple[int, str, str]:
    """Синхронный запуск команды с таймаутом. Возвращает (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
            errors="ignore",
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout while running: {' '.join(args)}"


def _truncate_diagnostic(raw_text: str, max_len: int = DOCKER_DIAGNOSTIC_MAX_LEN) -> str:
    """Ограничить длину диагностики для безопасного вывода."""
    if len(raw_text) <= max_len:
        return raw_text
    omitted = len(raw_text) - max_len
    return f"{raw_text[:max_len]}... <truncated {omitted} chars>"


def _scrub_sensitive_text(raw_text: str) -> str:
    """Fail-closed маскирование секретов в диагностическом тексте."""
    if not raw_text:
        return ""
    text = raw_text
    text = re.sub(
        r"(?i)(--(?:password|token|api-key))(?:\s+|=)(?:'[^']*'|\"[^\"]*\"|[^\s,;]+)",
        lambda match: f"{match.group(1)}=<redacted>",
        text,
    )
    text = re.sub(
        r"(?i)([A-Za-z][A-Za-z0-9+.\-]*://)([^/\s:@]+):([^@\s]+)@",
        r"\1<redacted>:<redacted>@",
        text,
    )
    text = re.sub(
        r"(?i)\b(PASSWORD|PASS|TOKEN|SECRET|API_KEY|DATABASE_URL|DSN)\b\s*([=:])\s*(?:'[^']*'|\"[^\"]*\"|[^\s,;]+)?",
        lambda match: f"{match.group(1)}{match.group(2)}<redacted>",
        text,
    )
    text = re.sub(
        r"(?i)\b[A-Za-z0-9._-]+(?:TOKEN|PASSWORD|SECRET|API_KEY|DATABASE_URL|DSN|PASS)[A-Za-z0-9._-]+\b",
        "<redacted>",
        text,
    )
    text = re.sub(
        r"(?i)Authorization\s*:\s*(Bearer|Basic)\s*(?:'[^']*'|\"[^\"]*\"|[^\s,;]+)",
        r"Authorization: \1 <redacted>",
        text,
    )
    return _truncate_diagnostic(text)


def _safe_command_repr(command: tuple[str, ...] | list[str]) -> str:
    """Построить безопасное allowlist-представление CLI команды."""
    sensitive_flags = {"--password", "--token", "--api-key"}
    rendered: list[str] = []
    redact_next = False
    for raw_arg in command:
        arg = str(raw_arg)
        lower = arg.lower()

        if redact_next:
            rendered.append("<redacted>")
            redact_next = False
            continue

        if lower in sensitive_flags:
            rendered.append(lower)
            redact_next = True
            continue

        if lower.startswith("--password="):
            rendered.append("--password=<redacted>")
            continue
        if lower.startswith("--token="):
            rendered.append("--token=<redacted>")
            continue
        if lower.startswith("--api-key="):
            rendered.append("--api-key=<redacted>")
            continue

        scrubbed = _scrub_sensitive_text(arg)
        if re.search(r"^[A-Za-z0-9._:/{}@,\-=+]+$", scrubbed):
            rendered.append(scrubbed)
        else:
            rendered.append("<redacted>")

    return _truncate_diagnostic(" ".join(rendered))


def _docker_stage_error(
    *,
    stage: str,
    command: tuple[str, ...] | list[str],
    exit_code: int,
    stderr: str,
    owner_action: str,
) -> RuntimeError:
    """Собрать RuntimeError для fail-closed Docker lifecycle."""
    safe_command = _safe_command_repr(command)
    safe_stderr = _scrub_sensitive_text((stderr or "").strip()) or "<empty>"
    safe_action = _scrub_sensitive_text(owner_action)
    return RuntimeError(
        f"[DOCKER_STAGE={stage}] exit_code={exit_code}; command={safe_command}; "
        f"stderr={safe_stderr}; owner_action={safe_action}"
    )


def _format_docker_warning(*, context: str, exit_code: int, stderr: str) -> str:
    """Собрать безопасный warning для Docker cleanup без raw stderr."""
    safe_context = _scrub_sensitive_text(context) or "<empty>"
    safe_stderr = _scrub_sensitive_text((stderr or "").strip()) or "<empty>"
    return _truncate_diagnostic(
        f"[WARNING] {safe_context}; rc={exit_code}; stderr={safe_stderr}"
    )


def _format_retry_diagnostic(
    *,
    operation: str,
    error: Exception,
    attempt: int,
    max_attempts: int,
    backoff_sec: int | float,
) -> str:
    """Собрать безопасный retry-log без raw exception текста."""
    safe_operation = _scrub_sensitive_text(operation) or "<empty>"
    safe_error_type = type(error).__name__
    safe_error = _scrub_sensitive_text(str(error)) or "<empty>"
    return _truncate_diagnostic(
        f"[WAIT] {safe_operation} failed ({safe_error_type}): {safe_error}. "
        f"Retry {attempt}/{max_attempts} in {backoff_sec}s..."
    )


def _is_non_retryable_init_error(exc: Exception) -> bool:
    """Классифицировать детерминированные init-ошибки, которые нельзя ретраить."""
    if isinstance(exc, (NotImplementedError, KeyboardInterrupt)):
        return True

    non_retryable_error_types: tuple[type[BaseException], ...] = (pytest.fail.Exception,)
    try:
        from tests.support.destructive_pg_dsn import DestructiveTestDatabaseError as _DST
        non_retryable_error_types = (_DST, pytest.fail.Exception)
    except Exception:
        pass

    if isinstance(exc, non_retryable_error_types):
        return True

    # Явно детерминированные infrastructure/configuration сигнатуры.
    if isinstance(exc, RuntimeError):
        msg = str(exc)
        deterministic_markers = (
            "DOCKER_STAGE=",
            "Docker Compose не найден",
            "command not found:",
            "network_guard internal error",
        )
        if any(marker in msg for marker in deterministic_markers):
            return True
    return False


def _raise_docker_stage_error(
    *,
    stage: str,
    command: tuple[str, ...] | list[str],
    exit_code: int,
    stderr: str,
    owner_action: str,
) -> None:
    """Сформировать fail-closed ошибку Docker-этапа с actionable текстом."""
    raise _docker_stage_error(
        stage=stage,
        command=command,
        exit_code=exit_code,
        stderr=stderr,
        owner_action=owner_action,
    )


def _docker_compose_preflight_or_raise() -> list[str]:
    """Проверить Docker CLI/daemon/compose до ``compose up``."""
    rc, _out, err = _sync_run("docker", "--version", timeout=5)
    if rc != 0:
        _raise_docker_stage_error(
            stage="detect",
            command=("docker", "--version"),
            exit_code=rc,
            stderr=err,
            owner_action="Установите Docker CLI и убедитесь, что `docker` доступен в PATH.",
        )

    rc, _out, err = _sync_run("docker", "info", "--format", "{{.ServerVersion}}", timeout=8)
    if rc != 0:
        _raise_docker_stage_error(
            stage="daemon",
            command=("docker", "info", "--format", "{{.ServerVersion}}"),
            exit_code=rc,
            stderr=err,
            owner_action="Запустите Docker daemon (Docker Desktop/Engine) и повторите прогон.",
        )

    rc, _out, err = _sync_run("docker", "compose", "version", timeout=8)
    if rc != 0:
        _raise_docker_stage_error(
            stage="compose",
            command=("docker", "compose", "version"),
            exit_code=rc,
            stderr=err,
            owner_action="Убедитесь, что Docker Compose plugin установлен и команда работает.",
        )
    return ["docker", "compose"]


def _detect_compose_cmd() -> list[str]:
    """Определяет доступную форму запуска compose: ['docker', 'compose'] или ['docker-compose']."""
    # Предпочитаем новый docker compose
    rc, *_ = _sync_run("docker", "compose", "version", timeout=5)
    if rc == 0:
        return ["docker", "compose"]
    # Фолбэк на старый docker-compose
    rc, *_ = _sync_run("docker-compose", "version", timeout=5)
    if rc == 0:
        return ["docker-compose"]
    return []


def _emergency_cleanup():
    """Аварийная очистка контейнеров при выходе из pytest (если нормальный teardown провалился)."""
    cid = _DOCKER_CLEANUP_STATE.get("container_id")
    cmd = _DOCKER_CLEANUP_STATE.get("compose_cmd")

    if cid:
        print(f"\n[EMERGENCY CLEANUP] Force removing container: {cid}")
        _sync_run("docker", "stop", "-t", "1", cid, timeout=5)
        _sync_run("docker", "rm", "-f", cid, timeout=5)

    if cmd:
        print(f"\n[EMERGENCY CLEANUP] Compose down: {COMPOSE_FILE}")
        _sync_run(*cmd, "-f", COMPOSE_FILE, "down", "-v", "--timeout", "1", timeout=15)


# Регистрируем emergency cleanup на случай краша pytest
atexit.register(_emergency_cleanup)


@pytest.fixture(scope="session")
def docker_compose_cmd() -> list[str]:
    """Определяет команду Docker Compose после fail-closed preflight."""
    cmd = _docker_compose_preflight_or_raise()
    _DOCKER_CLEANUP_STATE["compose_cmd"] = cmd
    return cmd


_TEST_DB_READY = False
_TEST_DB_INITIALIZED = False


def _require_destructive_local(request: pytest.FixtureRequest) -> None:
    """Fail-closed: destructive fixtures требуют marker до Docker/engine/DDL."""
    from tests.support.destructive_markers import require_destructive_local_marker

    require_destructive_local_marker(request)


@pytest.fixture(scope="session")
def _destructive_db_session_teardown(docker_compose_cmd):
    """Session lifecycle: teardown compose только в конце (без setup)."""
    yield
    print(f"\n[CLEANUP] Stopping Docker Compose: {COMPOSE_FILE}")
    cid = _DOCKER_CLEANUP_STATE.get("container_id")
    if cid:
        _sync_run("docker", "stop", "-t", "2", cid, timeout=10)
    rc, _, err = _sync_run(
        *docker_compose_cmd,
        "-f",
        COMPOSE_FILE,
        "down",
        "-v",
        "--remove-orphans",
        "--timeout",
        "1",
        timeout=20,
    )
    if rc != 0:
        print(
            _format_docker_warning(
                context="compose down failed",
                exit_code=rc,
                stderr=err,
            )
        )
    if cid:
        _sync_run("docker", "rm", "-f", cid, timeout=10)
        _DOCKER_CLEANUP_STATE["container_id"] = None
    _DOCKER_CLEANUP_STATE["compose_cmd"] = None
    print("[OK] Cleanup complete.")


@pytest.fixture
def setup_test_database(request):
    """Поднять disposable test PG/CH (один раз за session) после marker check.

    Требует ``@pytest.mark.destructive_local`` на тесте. Opt-in env недостаточен.
    """
    _require_destructive_local(request)
    from tests.support.destructive_pg_dsn import (
        DestructiveTestDatabaseError,
        validate_destructive_test_database_url,
    )

    # Fail-closed preflight BEFORE any docker compose interaction.
    validate_destructive_test_database_url(TEST_DB_URL, environ=dict(os.environ))

    docker_compose_cmd = _docker_compose_preflight_or_raise()

    global _TEST_DB_READY
    _TEST_DB_READY = False
    _DOCKER_CLEANUP_STATE["compose_cmd"] = docker_compose_cmd
    compose_attempted = False
    compose_started = False
    container_id = ""
    print(f"\n[SETUP] Starting Docker Compose: {COMPOSE_FILE}")
    try:
        # --- Запуск Docker Compose ---
        # Если test_db уже healthy — только ``up -d`` (без force-recreate).
        compose_up_args = ["up", "-d"]
        _rc_ps, cid_out, _ = _sync_run(
            *docker_compose_cmd, "-f", COMPOSE_FILE, "ps", "-q", "test_db", timeout=10
        )
        if cid_out.strip():
            rc_inspect, status_out, _ = _sync_run(
                "docker",
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                cid_out.strip(),
                timeout=10,
            )
            if rc_inspect == 0 and status_out.strip() == "healthy":
                print("[OK] Reusing running test_db container (skip --force-recreate).")
            else:
                compose_up_args = ["up", "-d", "--build", "--force-recreate"]
        else:
            compose_up_args = ["up", "-d", "--build", "--force-recreate"]

        compose_attempted = True
        rc, _out, err = _sync_run(
            *docker_compose_cmd, "-f", COMPOSE_FILE, *compose_up_args, timeout=180
        )
        if rc != 0:
            _raise_docker_stage_error(
                stage="up",
                command=(*docker_compose_cmd, "-f", COMPOSE_FILE, *compose_up_args),
                exit_code=rc,
                stderr=err,
                owner_action=(
                    "Проверьте `docker compose -f tests/docker-compose.test.yml logs` "
                    "и исправьте конфигурацию контейнеров."
                ),
            )
        compose_started = True

        # --- Ожидание запуска контейнера ---
        last_health_command: tuple[str, ...] = (
            *docker_compose_cmd,
            "-f",
            COMPOSE_FILE,
            "ps",
            "-q",
            "test_db",
        )
        last_health_exit_code = 0
        last_health_stderr = ""
        for i in range(SETUP_DB_STARTUP_MAX_RETRIES):
            _rc_ps, cid_out, err_ps = _sync_run(
                *docker_compose_cmd, "-f", COMPOSE_FILE, "ps", "-q", "test_db", timeout=10
            )
            last_health_command = (
                *docker_compose_cmd,
                "-f",
                COMPOSE_FILE,
                "ps",
                "-q",
                "test_db",
            )
            last_health_exit_code = _rc_ps
            last_health_stderr = err_ps
            container_id = cid_out.strip()
            if container_id:
                _DOCKER_CLEANUP_STATE["container_id"] = container_id
                rc, status_out, err_inspect = _sync_run(
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}nohealth{{end}}",
                    container_id,
                    timeout=10,
                )
                last_health_command = (
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}nohealth{{end}}",
                    container_id,
                )
                last_health_exit_code = rc
                last_health_stderr = err_inspect
                status = status_out.strip() if rc == 0 else "unknown"

                if status.endswith(" healthy"):
                    print("[OK] Test database is healthy.")
                    break

                print(
                    f"[WAIT] Waiting for test database... Attempt {i + 1}/"
                    f"{SETUP_DB_STARTUP_MAX_RETRIES} (status: {status})"
                )
            else:
                print(
                    f"[WAIT] Waiting for test database... Attempt {i + 1}/"
                    f"{SETUP_DB_STARTUP_MAX_RETRIES} (status: no container yet)"
                )
            time.sleep(SETUP_DB_STARTUP_SLEEP_SEC)
        else:
            _raise_docker_stage_error(
                stage="health",
                command=last_health_command,
                exit_code=last_health_exit_code,
                stderr=(
                    f"{last_health_stderr} | timed out waiting for healthy status "
                    f"after {SETUP_DB_STARTUP_MAX_RETRIES} attempts"
                ),
                owner_action=(
                    "Проверьте healthcheck/логи контейнера test_db и увеличьте "
                    "ресурсы Docker при необходимости."
                ),
            )

        print("[DB] Resetting PostgreSQL schema for tests...")

        # --- Ensure pg_hba.conf allows host connections ---
        if container_id:
            hba_patch_cmd = (
                'set -e; '
                'HBA="$PGDATA/pg_hba.conf"; '
                'MARKER="# added by pytest conftest (allow host connections for tests)"; '
                'if ! grep -q "$MARKER" "$HBA"; then '
                '  printf "\\n%s\\n" "$MARKER" >> "$HBA"; '
                '  printf "host    all             all             0.0.0.0/0               trust\\n" >> "$HBA"; '
                '  printf "host    all             all             ::/0                    trust\\n" >> "$HBA"; '
                '  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select pg_reload_conf();" >/dev/null; '
                'fi'
            )
            _sync_run("docker", "exec", container_id, "sh", "-lc", hba_patch_cmd, timeout=20)

        # После health=healthy на Windows host-коннект может стабилизироваться не сразу.
        time.sleep(SETUP_DB_SETTLE_SLEEP_SEC)

        async def init_schema_and_seed() -> None:
            """Пересоздать public-схему и сидировать wbcabinet id=1."""
            engine = _create_test_async_engine()
            try:
                async with engine.begin() as conn:
                    await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
                    await conn.execute(text("CREATE SCHEMA IF NOT EXISTS public;"))
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
                    from app.modules.common_slaves.wildberries.models.models import (
                        AdvKeyword,
                        AdvSetting,
                        WBAutoBudgetTopUp,
                        WBBalancePayment,
                        WBBonusPayment,
                        WBCard,
                        WBCategory,
                        WBToken,
                        WBUserCabinet,
                        KeywordSetting,
                    )
                    from app.modules.billing.event_manager.models import BillingEvent
                    from app.modules.wb_adv_updater.modules.balance_exp_informer.models import (
                        BalanceReminder,
                    )
                    from app.utils.db.models import Invite, User

                    await conn.run_sync(Base.metadata.create_all)

                    initial_wb_cabinet_data = {
                        "id": 1,
                        "shop_id": "test_shop_id",
                        "active": True,
                        "expiration_time": datetime.now() + timedelta(days=7),
                        "balance": 0.0,
                        "bonus": 0.0,
                        "demo": True,
                        "expiration_alarm_days_pass": None,
                    }
                    insert_stmt = insert(WBCabinet).values(initial_wb_cabinet_data)
                    on_conflict_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=["id"],
                        set_={
                            k: v
                            for k, v in initial_wb_cabinet_data.items()
                            if k != "id"
                        },
                    )
                    await conn.execute(on_conflict_stmt)
                    await conn.execute(
                        text(
                            "SELECT setval(pg_get_serial_sequence('wbcabinet', 'id'), "
                            "(SELECT COALESCE(MAX(id), 1) FROM wbcabinet));"
                        )
                    )
            finally:
                await engine.dispose()

        for attempt in range(1, SETUP_DB_INIT_MAX_RETRIES + 1):
            init_coro = init_schema_and_seed()
            try:
                asyncio.run(init_coro)
                break
            except KeyboardInterrupt:
                init_coro.close()
                # Deterministic owner interruption: never retry.
                raise
            except (DestructiveTestDatabaseError, pytest.fail.Exception):
                # Deterministic safety/owner interruption: never retry.
                raise
            except Exception as exc:  # noqa: BLE001
                if _is_non_retryable_init_error(exc):
                    raise
                if attempt >= SETUP_DB_INIT_MAX_RETRIES:
                    raise
                backoff_sec = min(2 * attempt, SETUP_DB_INIT_BACKOFF_MAX_SEC)
                print(
                    _format_retry_diagnostic(
                        operation="Test DB init",
                        error=exc,
                        attempt=attempt,
                        max_attempts=SETUP_DB_INIT_MAX_RETRIES,
                        backoff_sec=backoff_sec,
                    )
                )
                time.sleep(backoff_sec)

        print("[OK] Test database setup complete.")
        _TEST_DB_READY = True
        yield
    finally:
        primary_exception = sys.exc_info()[1]
        if isinstance(primary_exception, GeneratorExit):
            # Generator close() is normal fixture finalization path, not a primary test/setup error.
            primary_exception = None
        cleanup_error: RuntimeError | None = None
        try:
            if compose_attempted:
                print(f"\n[CLEANUP] Compose down: {COMPOSE_FILE}")
                try:
                    rc, _out, err = _sync_run(
                        *docker_compose_cmd,
                        "-f",
                        COMPOSE_FILE,
                        "down",
                        "-v",
                        "--remove-orphans",
                        "--timeout",
                        "1",
                        timeout=20,
                    )
                    if rc != 0:
                        cleanup_error = _docker_stage_error(
                            stage="cleanup",
                            command=(
                                *docker_compose_cmd,
                                "-f",
                                COMPOSE_FILE,
                                "down",
                                "-v",
                                "--remove-orphans",
                                "--timeout",
                                "1",
                            ),
                            exit_code=rc,
                            stderr=err,
                            owner_action=(
                                "Проверьте права Docker/состояние daemon и повторите "
                                "cleanup вручную: `docker compose -f tests/docker-compose.test.yml "
                                "down -v --remove-orphans`."
                            ),
                        )
                except Exception as exc:  # noqa: BLE001
                    cleanup_error = _docker_stage_error(
                        stage="cleanup",
                        command=(
                            *docker_compose_cmd,
                            "-f",
                            COMPOSE_FILE,
                            "down",
                            "-v",
                            "--remove-orphans",
                            "--timeout",
                            "1",
                        ),
                        exit_code=(
                            124 if isinstance(exc, subprocess.TimeoutExpired) else -1
                        ),
                        stderr=str(exc),
                        owner_action=(
                            "Проверьте доступность Docker daemon и повторите cleanup "
                            "вручную."
                        ),
                    )
        finally:
            _TEST_DB_READY = False
            _DOCKER_CLEANUP_STATE["container_id"] = None
            _DOCKER_CLEANUP_STATE["compose_cmd"] = None
        if cleanup_error is not None:
            if primary_exception is None:
                raise cleanup_error
            print(f"[WARNING] Cleanup failure ignored due to primary exception: {cleanup_error}")


@pytest.fixture(scope="function", name="async_engine")
async def _async_engine(request, setup_test_database):
    """Создаёт async движок для каждого destructive_local теста."""
    _require_destructive_local(request)
    engine = _create_test_async_engine(echo=False)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(name="async_session")
async def _async_session(request, async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Создаёт async сессию с откатом после теста (destructive_local only)."""
    _require_destructive_local(request)
    async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        trans = await session.begin()
        try:
            yield session
        finally:
            if trans.is_active:
                await trans.rollback()
            await session.close()



# Фикстура для доступа к mock access (простая версия)
@pytest.fixture(name="access_mock_simple")
def _access_mock():
    mock = MagicMock()
    mock.wb_cabinet = MagicMock(spec="WBCabinet")
    mock.wb_cabinet.id = 1
    mock.wb_cabinet.shop_id = "test_shop_id"
    return mock


try:
    # If a previous stub without __file__ exists, remove it to allow real import
    if mod_name in sys.modules and not getattr(sys.modules[mod_name], "__file__", None):
        del sys.modules[mod_name]
    m = importlib.import_module(mod_name)

    # Защитим декоратор на случай проблем с импортом/циклическими зависимостями
    def _try_except_decorator_stub(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

    try:
        setattr(m, "try_except_decorator", _try_except_decorator_stub)
    except Exception:
        pass
except Exception:
    # During early test phases some deps may be missing — create a stub module
    stub_mod = types.ModuleType(mod_name)

    def try_except_decorator(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

    # Do not stub 'requests' here; tests should mock HTTP behavior themselves
    stub_mod.try_except_decorator = try_except_decorator
    sys.modules[mod_name] = stub_mod


from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    KeywordStat,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBToken

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Настраиваем переменные окружения для тестов
os.environ["PYTHONPATH"] = str(project_root)


def pytest_configure(config) -> None:
    """
    Конфигурация pytest для корректного поиска и запуска тестов
    """
    # Добавляем метки для тестов
    config.addinivalue_line("markers", "fast: быстрый набор тестов для быстрого прогона")
    config.addinivalue_line("markers", "unit: маркирует unit-тесты")
    config.addinivalue_line("markers", "integration: маркирует интеграционные тесты")
    config.addinivalue_line(
        "markers",
        "destructive_local: destructive local PG/CH fixtures "
        "(opt-in ALLOW_DESTRUCTIVE_TEST_*; not selected by -m integration alone)",
    )


def pytest_collection_modifyitems(config, items: list[pytest.Item]) -> None:
    """
    Каждый тест получает ровно один тип: unit или integration.
    - tests/unit/ -> unit; tests/integration/ -> integration.
    - tests/unit/ получают marker fast **только если нет explicit integration
      и нет destructive_local**.
    - ``destructive_local`` никогда не получает ``fast`` и не получает auto
      ``integration`` (только явный marker ``destructive_local``).
    - Остальные без маркера типа -> unit по умолчанию.
    """

    def _has_mark(item: pytest.Item, name: str) -> bool:
        if name in item.keywords:
            return True
        return item.get_closest_marker(name) is not None

    for item in items:
        path = str(item.fspath).replace("\\", "/")
        is_unit_path = "/tests/unit/" in path or path.endswith("/tests/unit")
        has_unit = _has_mark(item, "unit")
        has_integration = _has_mark(item, "integration")
        has_destructive = _has_mark(item, "destructive_local")

        # destructive_local / integration never get auto-fast.
        if (
            is_unit_path
            and not has_integration
            and not has_destructive
            and not _has_mark(item, "fast")
        ):
            item.add_marker(pytest.mark.fast)

        if has_destructive:
            # Never auto-add integration/unit/fast. Selection: -m destructive_local
            continue

        if has_unit or has_integration:
            continue
        if "/integration/" in path or "integration" in item.fspath.basename or "/tests_entry_points/" in path:
            item.add_marker(pytest.mark.integration)
        elif is_unit_path:
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in path or path.endswith("/tests/integration"):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)

    # Fail-closed collection: plain -m integration / -m fast must not select
    # destructive_local even if a test also carries @pytest.mark.integration.
    markexpr = (getattr(config.option, "markexpr", None) or "").strip()
    markexpr_compact = markexpr.replace(" ", "")
    if markexpr and "destructive_local" not in markexpr_compact:
        if (
            markexpr_compact == "integration"
            or markexpr_compact == "fast"
            or markexpr_compact.startswith("integrationand")
            or markexpr_compact.startswith("fastand")
            or markexpr_compact.endswith("andintegration")
            or markexpr_compact.endswith("andfast")
        ):
            items[:] = [i for i in items if not _has_mark(i, "destructive_local")]
@pytest.fixture
def tokens_mock() -> list[MagicMock]:
    token_mock = MagicMock(spec=WBToken)
    return [token_mock]


@pytest.fixture
def wb_cabinet_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def access_mock(tokens_mock, wb_cabinet_mock):
    from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
    access_mock = MagicMock(spec=WBCabinetAccess)
    access_mock.tokens = tokens_mock
    access_mock.wb_cabinet = wb_cabinet_mock
    return access_mock


@pytest.fixture
def adv_setting_mock():
    adv_setting_mock = MagicMock(spec=AdvSetting)
    adv_setting_mock.adv_id = 25040169
    adv_setting_mock.nmids = [222811118]
    adv_setting_mock.search_adv_id = None
    adv_setting_mock.active_status = "started"
    adv_setting_mock.plan_for_sales_for_day = None
    adv_setting_mock.target_price_for_order = None
    adv_setting_mock.max_price_for_order = None
    adv_setting_mock.automatic_version = 2
    adv_setting_mock.aggressiveness = 3
    return adv_setting_mock


@pytest.fixture
def session_mock(): # Удаляем result_mock из аргументов
    session_mock = MagicMock()
    session_mock.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=[]))) # Задаем подходящее значение
    session_mock.commit = AsyncMock(return_value=None)
    return session_mock


@pytest.fixture
def get_async_session_mock(session_mock) -> MagicMock:
    session_maker_mock = MagicMock()
    session_maker_mock.__aenter__ = AsyncMock(return_value=session_mock)
    get_session_maker_mock = MagicMock(return_value=session_maker_mock)
    return get_session_maker_mock


from pytest import fixture


@fixture
def keywords_mocks() -> list[CalculatedKeyword]:
    """Создаёт список тестовых CalculatedKeyword с разными статусами.

    Включает:
    - 5 ключевых слов в whitelist (hard_status=2), 1 из них best
    - 2 ключевых слова в blacklist (hard_status=0)
    - 2 ключевых слова в тестировании (hard_status=1)
    """
    from tests.factories.keyword_pipeline import (
        GoodKeywordFactory,
        BadKeywordFactory,
        TestingKeywordFactory,
        BestKeywordFactory,
    )

    keywords = []
    # 1 лучшее ключевое слово (whitelist, best_keyword_status=True)
    keywords.append(BestKeywordFactory())
    # 4 хороших ключевых слова (whitelist, best_keyword_status=False)
    keywords.extend(GoodKeywordFactory.create_batch(4, state__best_keyword_status=False))
    # 2 плохих ключевых слова (blacklist)
    keywords.extend(BadKeywordFactory.create_batch(2))
    # 2 в тестировании
    keywords.extend(TestingKeywordFactory.create_batch(2))

    return keywords


@pytest.fixture(name='front_too_many_requests_str', scope='function')
async def front_too_many_requests_str() -> AsyncGenerator[str, None]:
    async with aiofiles.open('tests/wb_front_responses/too-many-requests.txt',
                             mode='r',
                             encoding='utf-8') as f:
        content = await f.read()
        yield content




# TODO: Разработать методологию оценки сроков разработки новых фич, багфиксов и рефакторингов, а также стратегии укладывания в сроки.


@pytest.fixture(name="di_container", scope="function")
async def di_container() -> AsyncGenerator["AppContainer", None]:
    from app.core.di.app_container import  AppContainer
    AppContainer.wiring_config = containers.WiringConfiguration()
    container = AppContainer()

    yield container



@pytest.fixture(scope="function")
async def postgres_session(request, async_engine):
    """Async PG session для destructive_local tests."""
    _require_destructive_local(request)
    async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope='function')
async def fake_redis():
    """Создает фейковый Redis для тестов (асинхронная версия)."""
    redis = await fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        yield redis
    finally:
        try:
            await redis.flushall()  # очищаем после теста
            await redis.aclose()
        except RuntimeError as exc:
            if "Event loop is closed" not in str(exc):
                raise


from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import ComplexAdv
from tests.factories.complex_adv import create_complex_adv_seed





# TODO: Внедрить исполнителя, который будет тормозить не эффективные РК и запускать потом их снова
# TODO Сделать более информативно какие РК сколько жрут
# TODO: Сделать исполнителя, который будет глушить слова сверху вниз и снизу вверх
# TODO Сделать дашборд по эффективности работы платных клиентов и самому писать им - это будет про-активная поддержка. С сортировкой по эффективности

@pytest.fixture(scope='function')
async def complex_adv(request, postgres_session: AsyncSession) -> AsyncGenerator[ComplexAdv, None]:
    """Создает ComplexAdv на реальном PG. Требует ``destructive_local``."""
    _require_destructive_local(request)

    await postgres_session.begin()
    seed = await create_complex_adv_seed(postgres_session)
    await postgres_session.refresh(
        seed.adv_setting, attribute_names=["wb_cabinet"]
    )
    cabinet_shop_id = seed.adv_setting.wb_cabinet.shop_id

    async def get_keywords_func(
        _: ComplexAdv, *, cache_only: bool = True
    ) -> list[CalculatedKeyword]:
        if not cache_only:
            raise RuntimeError("cache_only=False disabled in tests")
        return seed.calculated_keywords

    complex_adv = ComplexAdv(
        shop_id=cabinet_shop_id,
        get_keywords_func=get_keywords_func,
        adv_setting=seed.adv_setting,
        search_adv=seed.search_adv,
    )

    yield complex_adv
    await postgres_session.rollback()



@pytest.fixture(scope='function')
def complex_adv_mock():
    mock_adv = MagicMock(spec=ComplexAdv)
    mock_adv.get_keywords = AsyncMock(return_value=[])
    mock_adv.adv_setting = MagicMock()
    mock_adv.adv_setting.adv_id = 99999
    mock_adv.adv_setting.name = "Тестовая РК"
    mock_adv.adv_setting.auto_update_white_list = True
    mock_adv.adv_setting.auto_update_target_place = True
    mock_adv.adv_setting.auto_update_exponent = True
    mock_adv.adv_setting._search_adv = None
    mock_adv.search_adv = None
    mock_adv.shop_id = "test_shop"
    return mock_adv




@pytest.fixture(scope='function')
async def sm_generator(postgres_session):
    class _FakeSessionMaker:
        def __call__(self, *args, **kwargs):
            return self  # имитируем async context
        async def __aenter__(self):
            return postgres_session
        async def __aexit__(self, exc_type, exc, tb):
            pass

    return _FakeSessionMaker()


@pytest.fixture(autouse=True)
def _enforce_test_network_and_subprocess_guards():
    """Invariant: после каждого теста guards должны быть установлены.

    Если тест снял guard и не восстановил — немедленная переустановка + fail.
    """
    from tests.support.network_guard import (
        install_network_guard,
        is_network_guard_installed,
    )
    from tests.support.subprocess_guard import (
        install_subprocess_guard,
        is_subprocess_guard_installed,
    )

    if not is_network_guard_installed():
        install_network_guard()
    if not is_subprocess_guard_installed():
        install_subprocess_guard()
    yield
    leaked = False
    msgs: list[str] = []
    if not is_network_guard_installed():
        install_network_guard()
        leaked = True
        msgs.append("network guard was uninstalled without restore")
    if not is_subprocess_guard_installed():
        install_subprocess_guard()
        leaked = True
        msgs.append("subprocess guard was uninstalled without restore")
    if leaked:
        pytest.fail(
            "Test guard lifecycle violation: "
            + "; ".join(msgs)
            + " — guards reinstalled",
            pytrace=False,
        )


@pytest.fixture(autouse=True)
async def clean_db(request: pytest.FixtureRequest):
    """Очищает ключевые таблицы до и после destructive_local теста.

    Unit / без поднятой БД — no-op. Если БД готова и будет TRUNCATE —
    требуется ``destructive_local`` (fail до engine).
    """
    if request.node.get_closest_marker("unit") is not None:
        yield
        return
    if not _TEST_DB_READY:
        yield
        return

    _require_destructive_local(request)

    truncate_sql = text(
        # Чистим данные, которые часто создаются тестами.
        # Включаем wbcabinet, чтобы тесты могли стабильно создавать кабинет с id=1
        # (иначе возможны UniqueViolation на pkey при сидировании).
        'TRUNCATE "user", wbcabinet, wbusercabinet, wbbalancepayment, wbbonuspayment, '
        "payment, keywordsetting, advsetting, balancereminder, billing_event RESTART IDENTITY CASCADE"
    )

    async def _truncate() -> None:
        engine = _create_test_async_engine()
        async with engine.begin() as conn:
            await conn.execute(truncate_sql)
        await engine.dispose()

    await _truncate()
    yield
    await _truncate()


@pytest.fixture(scope='function')
def main_di_container() -> "AppContainer":
    from app.core.di.app_container import AppContainer
    container = AppContainer()
    return container




@pytest.fixture(scope='function')
def di_containner_for_adv_auto_updater_v2(main_di_container, fake_redis: FakeRedis) -> "AppContainer":
    main_di_container.wiring_config.modules = ['app.core.redis_cache',  # Отключаем автоматическое встраивание зависимостей
                                       "old_modules.setting_auto_updater_v2.adv_control_system."
                                       "executors.target_place_executor.utils",
                                       ]
    main_di_container.redis_client.override(fake_redis)
    return main_di_container


@pytest.fixture(scope="function")
async def clickhouse_client(request, setup_test_database):
    """
    Создаёт async-клиент ClickHouse (GuardedClickHouseClient).

    Fail-closed: marker ``destructive_local`` + endpoint validator + SQL gate.
    Database: ``test_adv_bot_clickhouse`` (не prod ``default_db``).
    """
    _require_destructive_local(request)
    from tests.support.destructive_clickhouse import (
        ALLOWED_CH_DATABASE,
        create_validated_async_clickhouse_client,
    )

    host = os.environ.get("CLICK_HOUSE_HOST", _TEST_PG_HOST)
    port = int(os.environ.get("CLICKHOUSE_PORT", "8124"))
    user = os.environ.get("CLICK_HOUSE_USER", "CLICK_HOUSE_USER")
    password = os.environ.get("CLICK_HOUSE_PASSWORD", "password")
    database = ALLOWED_CH_DATABASE

    client = await create_validated_async_clickhouse_client(
        host=host,
        port=port,
        database=database,
        username=user,
        password=password,
        get_async_client_fn=get_async_client,
    )

    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        try:
            await client.command("SELECT 1")
            print("[OK] ClickHouse HTTP endpoint is ready.")
            break
        except DatabaseError as exc:
            if attempt == max_attempts:
                raise
            print(
                _format_retry_diagnostic(
                    operation="ClickHouse not ready",
                    error=exc,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    backoff_sec=1,
                )
            )
            await asyncio.sleep(1)


    print("[OK] ClickHouse async client created")

    # Добавим небольшую задержку, чтобы ClickHouse полностью инициализировался
    await asyncio.sleep(5)

    # Создаём таблицы ClickHouse, если их нет
    await client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.full_adv_wb_stat (
            adv_id Int32,
            date Date,
            views Int32,
            clicks Int32,
            spend Float64,
            added_to_cart Int32,
            orders Int32,
            sum_price_orders Float64,
            version Float64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, date, version)
    """)

    await client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.advkeyword_new (
            adv_id Int32,
            text String,
            date Date,
            clicks_state AggregateFunction(argMax, Int32, Float64),
            views_state AggregateFunction(argMax, Int32, Float64),
            spend_state AggregateFunction(argMax, Float64, Float64),
            version Float64
        ) ENGINE = AggregatingMergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, text, date)
    """)

    await client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.clusters_adv_stats (
            adv_id UInt32,
            nmid UInt64,
            wb_category LowCardinality(String),
            norm_query LowCardinality(String),
            views UInt32,
            clicks UInt32,
            ctr Float64,
            cpm Float64,
            add_to_cart UInt32,
            orders UInt32,
            cpc Float64,
            avr_pos Float64,
            date Date,
            spend Nullable(Float64) DEFAULT NULL,
            timestamp DateTime default now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (wb_category, nmid, norm_query, date, timestamp)
        SETTINGS index_granularity = 8192
    """)

    await client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.adv_events_ticks (
            norm_query LowCardinality(String),
            ts DateTime,
            d_views UInt32,
            d_clicks UInt32,
            nmid UInt64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(ts)
        ORDER BY (norm_query, nmid, ts)
        SETTINGS index_granularity = 8192
    """)

    await client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.wb_common_stat (
            nmid UInt64,
            date Date,
            open_card UInt32,
            add_to_cart UInt32,
            orders UInt32,
            orders_sum Float64,
            buy_outs UInt32,
            buyouts_sum_rub Float64 DEFAULT 0,
            version Float64,
            INDEX idx_wb_common_stat_date date TYPE minmax GRANULARITY 1
        )
        ENGINE = ReplacingMergeTree(version)
        ORDER BY (nmid, date)
        SETTINGS index_granularity = 8192
    """)

    await client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.plan_fact_stats (
            adv_id Int32,
            shop_id String,
            date Date,
            timestamp DateTime,
            plan_orders Nullable(Int32),
            plan_target_pay_for_order Nullable(Int32),
            plan_max_pay_for_order Nullable(Int32),
            fact_predict_orders Nullable(Float64),
            fact_original_orders Nullable(Float64),
            fact_pay_for_order Nullable(Float64),
            fact_method Nullable(String),
            version Float64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, date, timestamp)
        SETTINGS index_granularity = 8192
    """)

    await client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.fact_stat_states (
            bucket_start DateTime,
            shop_id String,
            complex_adv_id Int64,
            views_adv_sum Int64,
            clicks_adv_sum Int64,
            carts_adv_sum Int64,
            orders_adv_sum Int64,
            spend_adv_sum_rub Int64,
            orders_sum_adv_rub Int64,
            open_card_sum Int64,
            carts_card_sum Int64,
            orders_card_sum Int64,
            orders_sum_card_rub Int64,
            buy_outs_sum Int64,
            src_ts DateTime,
            version Int64,
            event_date Date DEFAULT toDate(0),
            event_id Int64 DEFAULT 0
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(event_date)
        ORDER BY (complex_adv_id, event_date, event_id, src_ts)
        SETTINGS index_granularity = 8192
    """)

    # Создаём таблицу advkeyword (источник для Materialized Views)
    await client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.advkeyword (
            adv_id UInt64,
            date Date,
            text String,
            views UInt32,
            clicks UInt32,
            spend Float64,
            version UInt64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, date, text, version)
        SETTINGS index_granularity = 8192
    """)

    # Создаём Materialized View: advkeyword_daily_mv
    await client.command("""
        DROP VIEW IF EXISTS test_adv_bot_clickhouse.advkeyword_daily_mv
    """)
    await client.command("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS test_adv_bot_clickhouse.advkeyword_daily_mv
        (
            `adv_id` UInt64,
            `date` Date,
            `text` String,
            `clicks` AggregateFunction(argMax, UInt32, UInt64),
            `views` AggregateFunction(argMax, UInt32, UInt64),
            `spend` AggregateFunction(argMax, Float64, UInt64)
        )
        ENGINE = AggregatingMergeTree
        PARTITION BY toYYYYMM(date)
        ORDER BY (adv_id, date, text)
        SETTINGS index_granularity = 8192
        AS
        SELECT
            adv_id,
            date,
            text,
            argMaxState(clicks, version) AS clicks,
            argMaxState(views, version) AS views,
            argMaxState(spend, version) AS spend
        FROM test_adv_bot_clickhouse.advkeyword
        GROUP BY adv_id, date, text
    """)

    # Создаём Materialized View: cumulative_views
    # ВАЖНО: SummingMergeTree автоматически суммирует числовые колонки, поэтому НЕ используем sum() в SELECT
    await client.command("""
        DROP VIEW IF EXISTS test_adv_bot_clickhouse.cumulative_views
    """)
    await client.command("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS test_adv_bot_clickhouse.cumulative_views
        (
            `adv_id` UInt64,
            `text` String,
            `date` Date,
            `total_views` UInt64,
            `total_clicks` UInt64,
            `total_spend` Float64
        )
        ENGINE = SummingMergeTree
        ORDER BY (adv_id, text, date)
        SETTINGS index_granularity = 8192
        AS
        SELECT
            adv_id,
            text,
            date,
            views AS total_views,
            clicks AS total_clicks,
            spend AS total_spend
        FROM test_adv_bot_clickhouse.advkeyword
    """)

    # Создаём Materialized View: mv_clusters_daily
    # Агрегирует данные из clusters_adv_stats по дням с использованием AggregatingMergeTree
    await client.command("""
        DROP VIEW IF EXISTS test_adv_bot_clickhouse.mv_clusters_daily
    """)
    await client.command("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS test_adv_bot_clickhouse.mv_clusters_daily
        (
            `nmid` UInt64,
            `text` LowCardinality(String),
            `date` Date,
            `views_state` AggregateFunction(argMax, UInt32, DateTime),
            `clicks_state` AggregateFunction(argMax, UInt32, DateTime),
            `add_to_cart_state` AggregateFunction(argMax, UInt32, DateTime),
            `orders_state` AggregateFunction(argMax, UInt32, DateTime),
            `cpm_state` AggregateFunction(argMax, Float64, DateTime),
            `cpc_state` AggregateFunction(argMax, Float64, DateTime),
            `ts_state` AggregateFunction(max, DateTime)
        )
        ENGINE = AggregatingMergeTree
        ORDER BY (nmid, text, date)
        SETTINGS index_granularity = 8192
        AS
        SELECT nmid,
               norm_query AS text,
               date,
               argMaxState(views, timestamp) AS views_state,
               argMaxState(clicks, timestamp) AS clicks_state,
               argMaxState(add_to_cart, timestamp) AS add_to_cart_state,
               argMaxState(orders, timestamp) AS orders_state,
               argMaxState(cpm, timestamp) AS cpm_state,
               argMaxState(cpc, timestamp) AS cpc_state,
               maxState(timestamp) AS ts_state
        FROM test_adv_bot_clickhouse.clusters_adv_stats
        GROUP BY nmid, text, date
    """)

    # Создаём Materialized View: mv_clusters_daily_agg
    await client.command("""
        DROP VIEW IF EXISTS test_adv_bot_clickhouse.mv_clusters_daily_agg
    """)
    await client.command("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS test_adv_bot_clickhouse.mv_clusters_daily_agg
        (
            `adv_id` UInt32,
            `nmid` UInt64,
            `norm_query` LowCardinality(String),
            `date` Date,
            `views_state` AggregateFunction(argMax, UInt32, DateTime),
            `clicks_state` AggregateFunction(argMax, UInt32, DateTime),
            `carts_state` AggregateFunction(argMax, UInt32, DateTime),
            `orders_state` AggregateFunction(argMax, UInt32, DateTime),
            `cpm_state` AggregateFunction(argMax, Float64, DateTime),
            `ts_state` AggregateFunction(max, DateTime)
        )
        ENGINE = AggregatingMergeTree()
        ORDER BY (adv_id, nmid, norm_query, date)
        SETTINGS index_granularity = 8192
        AS
        SELECT
            adv_id,
            nmid,
            norm_query,
            date,
            argMaxState(views, timestamp) AS views_state,
            argMaxState(clicks, timestamp) AS clicks_state,
            argMaxState(add_to_cart, timestamp) AS carts_state,
            argMaxState(orders, timestamp) AS orders_state,
            argMaxState(cpm, timestamp) AS cpm_state,
            maxState(timestamp) AS ts_state
        FROM test_adv_bot_clickhouse.clusters_adv_stats
        GROUP BY adv_id, nmid, norm_query, date
    """)

    # Создаём Materialized View: mv_clusters_last_state
    # Хранит последнее состояние для каждого nmid + text
    await client.command("""
        DROP VIEW IF EXISTS test_adv_bot_clickhouse.mv_clusters_last_state
    """)
    await client.command("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS test_adv_bot_clickhouse.mv_clusters_last_state
        (
            `nmid` UInt64,
            `text` LowCardinality(String),
            `last_avg_pos_state` AggregateFunction(argMax, Float64, DateTime),
            `last_cpc_state` AggregateFunction(argMax, Float64, DateTime),
            `last_cpm_state` AggregateFunction(argMax, Float64, DateTime),
            `last_ts_state` AggregateFunction(max, DateTime)
        )
        ENGINE = AggregatingMergeTree
        ORDER BY (nmid, text)
        SETTINGS index_granularity = 8192
        AS
        SELECT nmid,
               norm_query AS text,
               argMaxState(avr_pos, timestamp) AS last_avg_pos_state,
               argMaxState(cpc, timestamp) AS last_cpc_state,
               argMaxState(cpm, timestamp) AS last_cpm_state,
               maxState(timestamp) AS last_ts_state
        FROM test_adv_bot_clickhouse.clusters_adv_stats
        GROUP BY nmid, norm_query
    """)

    print("[OK] ClickHouse tables created/checked")

    yield client


    client.close()
    print("[OK] ClickHouse client closed")


@pytest.fixture(scope='function')
def app_container():
    from app.core.di.app_container import AppContainer
    container = AppContainer()
    return container


@pytest.fixture(scope='function')
def bidder_keywords_300() -> list[CalculatedKeyword]:
    from tests.factories.keyword_pipeline import CalculatedKeywordFactory
    return CalculatedKeywordFactory.create_batch(300)
