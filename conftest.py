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
# Redis: same IPv4 loopback as PG/CH (Windows localhost→::1 breaks compose Redis).
os.environ["REDIS_MASTER_HOST"] = _TEST_PG_HOST
os.environ["REDIS_REPLICA_HOST"] = _TEST_PG_HOST
os.environ["REDIS_HOST"] = _TEST_PG_HOST
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
os.environ["REDIS_MASTER_HOST"] = _TEST_PG_HOST
os.environ["REDIS_REPLICA_HOST"] = _TEST_PG_HOST
os.environ["REDIS_HOST"] = _TEST_PG_HOST
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

import pytest

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from typing import AsyncGenerator
# Переменные окружения для тестовой БД
TEST_DB_URL = (
    f"postgresql+asyncpg://test_user:test_password@{_TEST_PG_HOST}:5433/test_adv_bot_db"
)
COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "tests", "docker-compose.test.yml")

# Глобальное хранилище для emergency cleanup (crash path).
_DOCKER_CLEANUP_STATE = {"compose_cmd": None, "container_id": None}
# Session lifecycle handle (заполняется fixture ``_test_infra_lifecycle``).
_TEST_INFRA_LIFECYCLE = None

# Настройки orchestration destructive integration setup.
SETUP_DB_STARTUP_MAX_RETRIES = 120
SETUP_DB_STARTUP_SLEEP_SEC = 2
SETUP_DB_INIT_MAX_RETRIES = 10
SETUP_DB_INIT_BACKOFF_MAX_SEC = 10
SETUP_DB_SETTLE_SLEEP_SEC = 10
DOCKER_DIAGNOSTIC_MAX_LEN = 600

# Compat: _TEST_DB_READY отражает session PG readiness (не per-test).
_TEST_DB_READY = False


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


def _build_test_alembic_config() -> Config:
    """Возвращает Alembic Config, принудительно направленный в test PostgreSQL."""
    project_root = os.path.dirname(__file__)
    config = Config(os.path.join(project_root, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(project_root, "alembic_"))
    config.set_main_option("prepend_sys_path", project_root)
    config.set_main_option("sqlalchemy.url", TEST_DB_POSTGRES_URL)
    return config


def _run_test_db_migrations_to_head() -> tuple[list[str], list[str]]:
    """Ставит test DB на актуальные Alembic heads и проверяет ревизии и колонку."""
    config = _build_test_alembic_config()
    script = ScriptDirectory.from_config(config)
    expected_heads = sorted(script.get_heads())

    engine = create_engine(TEST_DB_POSTGRES_URL, poolclass=NullPool)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.stamp(config, "heads")

        with engine.connect() as connection:
            current_rows = connection.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num")
            ).scalars()
            current_heads = sorted(current_rows)

            has_minus_phrases_column = connection.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'advsetting'
                          AND column_name = 'auto_update_minus_phrases'
                    )
                    """
                )
            ).scalar_one()
    finally:
        engine.dispose()

    if current_heads != expected_heads:
        raise RuntimeError(
            "Test DB Alembic migration mismatch: "
            f"current={current_heads}, head={expected_heads}, url={TEST_DB_POSTGRES_URL}"
        )

    if not has_minus_phrases_column:
        raise RuntimeError(
            "Test DB migration verification failed: "
            "column public.advsetting.auto_update_minus_phrases is missing after Alembic upgrade."
        )

    return current_heads, expected_heads


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


def _coerce_diagnostic_text(raw: object) -> str:
    """Нормализовать stderr/stdout до str для scrub.

    Non-str (``None``, ``MagicMock`` от утечки mock'ов в suite) → ``""``,
    чтобы teardown lifecycle не падал ``TypeError`` в ``re.sub``.
    """
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw).decode("utf-8", errors="replace")
    return ""


def _truncate_diagnostic(raw_text: str, max_len: int = DOCKER_DIAGNOSTIC_MAX_LEN) -> str:
    """Ограничить длину диагностики для безопасного вывода."""
    text = _coerce_diagnostic_text(raw_text)
    if len(text) <= max_len:
        return text
    omitted = len(text) - max_len
    return f"{text[:max_len]}... <truncated {omitted} chars>"


def _scrub_sensitive_text(raw_text: object) -> str:
    """Fail-closed маскирование секретов в диагностическом тексте."""
    text = _coerce_diagnostic_text(raw_text)
    if not text:
        return ""
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
    stderr: object,
    owner_action: object,
) -> RuntimeError:
    """Собрать RuntimeError для fail-closed Docker lifecycle."""
    safe_command = _safe_command_repr(command)
    safe_stderr = (
        _scrub_sensitive_text(_coerce_diagnostic_text(stderr).strip()) or "<empty>"
    )
    safe_action = _scrub_sensitive_text(owner_action) or "<empty>"
    return RuntimeError(
        f"[DOCKER_STAGE={stage}] exit_code={exit_code}; command={safe_command}; "
        f"stderr={safe_stderr}; owner_action={safe_action}"
    )


def _format_docker_warning(*, context: object, exit_code: int, stderr: object) -> str:
    """Собрать безопасный warning для Docker cleanup без raw stderr."""
    safe_context = _scrub_sensitive_text(context) or "<empty>"
    safe_stderr = (
        _scrub_sensitive_text(_coerce_diagnostic_text(stderr).strip()) or "<empty>"
    )
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
    from tests.support.destructive_lifecycle import RetryClass, classify_lifecycle_error

    return classify_lifecycle_error(exc) is RetryClass.NON_RETRYABLE


def _resolve_test_infra_lifecycle(request: pytest.FixtureRequest):
    """Получить session lifecycle ПОСЛЕ marker/validation gate.

    Unit tests могут inject'ить ``request._test_infra_lifecycle``.
    """
    injected = getattr(request, "_test_infra_lifecycle", None)
    if injected is not None:
        return injected
    return request.getfixturevalue("_test_infra_lifecycle")


def _validate_pg_preflight() -> None:
    """Fail-closed PG DSN/opt-in/tunnels до Docker/engine."""
    from tests.support.destructive_pg_dsn import validate_destructive_test_database_url

    validate_destructive_test_database_url(TEST_DB_URL, environ=dict(os.environ))


def _validate_ch_preflight() -> None:
    """Fail-closed CH endpoint/opt-in/tunnels до Docker/client."""
    from tests.support.destructive_clickhouse import (
        ALLOWED_CH_DATABASE,
        validate_destructive_clickhouse_endpoint,
    )

    validate_destructive_clickhouse_endpoint(
        host=os.environ.get("CLICK_HOUSE_HOST", _TEST_PG_HOST),
        port=os.environ.get("CLICKHOUSE_PORT", "8124"),
        database=ALLOWED_CH_DATABASE,
        username=os.environ.get("CLICK_HOUSE_USER"),
        environ=dict(os.environ),
    )


def _probe_pg_test_endpoint() -> None:
    """Live loopback probe для ``TEST_INFRA_REUSE`` без Docker API.

    Вызывается только после ``validate_destructive_test_database_url``.
    """
    from tests.support.destructive_pg_dsn import (
        DestructiveTestDatabaseError,
        validate_destructive_test_database_url,
    )

    validate_destructive_test_database_url(TEST_DB_POSTGRES_URL, environ=dict(os.environ))
    engine = create_engine(
        TEST_DB_POSTGRES_URL,
        poolclass=NullPool,
        connect_args={"connect_timeout": 5},
    )
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except DestructiveTestDatabaseError:
        raise
    except Exception as exc:
        raise DestructiveTestDatabaseError(
            "TEST_INFRA_REUSE: PostgreSQL endpoint unhealthy on validated "
            f"loopback test port — {type(exc).__name__}"
        ) from exc
    finally:
        engine.dispose()


def _probe_ch_test_endpoint() -> None:
    """Live loopback HTTP probe для ``TEST_INFRA_REUSE`` без Docker API."""
    import base64
    import urllib.error
    import urllib.request

    from tests.support.destructive_clickhouse import (
        ALLOWED_CH_DATABASE,
        DestructiveTestClickHouseError,
        validate_destructive_clickhouse_endpoint,
    )

    host = os.environ.get("CLICK_HOUSE_HOST", _TEST_PG_HOST)
    port = os.environ.get("CLICKHOUSE_PORT", "8124")
    username = os.environ.get("CLICK_HOUSE_USER", "CLICK_HOUSE_USER")
    password = os.environ.get("CLICK_HOUSE_PASSWORD", "password")
    validate_destructive_clickhouse_endpoint(
        host=host,
        port=port,
        database=ALLOWED_CH_DATABASE,
        username=username,
        environ=dict(os.environ),
    )
    ping_url = f"http://{host}:{port}/ping"
    req = urllib.request.Request(ping_url, method="GET")
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                raise DestructiveTestClickHouseError(
                    "TEST_INFRA_REUSE: ClickHouse /ping returned "
                    f"status {resp.status} on validated loopback test port"
                )
    except DestructiveTestClickHouseError:
        raise
    except urllib.error.URLError as exc:
        raise DestructiveTestClickHouseError(
            "TEST_INFRA_REUSE: ClickHouse endpoint unhealthy on validated "
            f"loopback test port — {type(exc).__name__}"
        ) from exc
    except Exception as exc:
        raise DestructiveTestClickHouseError(
            "TEST_INFRA_REUSE: ClickHouse endpoint probe failed on validated "
            f"loopback test port — {type(exc).__name__}"
        ) from exc


def _run_pg_schema_bootstrap() -> None:
    """Session-once PG DROP/CREATE + create_all + baseline seed + Alembic verify.

    Вызывается из sync ``ensure_resources``; может идти из-под async fixture —
    поэтому не ``asyncio.run`` напрямую (см. ``run_awaitable_from_sync``).

    После ORM bootstrap вызывает ``_run_test_db_migrations_to_head`` для проверки
    Alembic heads и критичных колонок (intent replay 72221e27b).
    """
    from tests.support.destructive_lifecycle import run_awaitable_from_sync
    from tests.support.destructive_pg_reset import init_postgres_schema_and_seed

    async def _run() -> None:
        engine = _create_test_async_engine()
        try:
            await init_postgres_schema_and_seed(engine)
        finally:
            await engine.dispose()

    run_awaitable_from_sync(_run())
    current_heads, expected_heads = _run_test_db_migrations_to_head()
    print(
        "[OK] Test DB Alembic heads verified. "
        f"current={current_heads} head={expected_heads}"
    )


def _run_ch_schema_bootstrap() -> None:
    """Session-once ClickHouse DDL через temporary validated client.

    См. ``_run_pg_schema_bootstrap``: bridge обязателен при вызове из
    async ``clickhouse_client`` → ``ensure_resources``.
    """
    from tests.support.destructive_ch_reset import apply_clickhouse_session_ddl
    from tests.support.destructive_clickhouse import (
        ALLOWED_CH_DATABASE,
        create_validated_async_clickhouse_client,
    )
    from tests.support.destructive_lifecycle import run_awaitable_from_sync

    async def _run() -> None:
        client = await create_validated_async_clickhouse_client(
            host=os.environ.get("CLICK_HOUSE_HOST", _TEST_PG_HOST),
            port=int(os.environ.get("CLICKHOUSE_PORT", "8124")),
            database=ALLOWED_CH_DATABASE,
            username=os.environ.get("CLICK_HOUSE_USER", "CLICK_HOUSE_USER"),
            password=os.environ.get("CLICK_HOUSE_PASSWORD", "password"),
            get_async_client_fn=get_async_client,
        )
        try:
            await client.command("SELECT 1")
            await apply_clickhouse_session_ddl(client)
        finally:
            client.close()

    run_awaitable_from_sync(_run())

def _build_test_infra_lifecycle():
    """Собрать session-owned lifecycle с runners из conftest."""
    from tests.support.destructive_lifecycle import (
        TestInfraLifecycle,
        TestInfraSessionState,
        is_reuse_mode_enabled,
    )

    state = TestInfraSessionState(reuse_mode=is_reuse_mode_enabled())
    return TestInfraLifecycle(
        state=state,
        compose_file=COMPOSE_FILE,
        sync_run=_sync_run,
        docker_preflight=_docker_compose_preflight_or_raise,
        validate_pg=_validate_pg_preflight,
        validate_ch=_validate_ch_preflight,
        probe_pg=_probe_pg_test_endpoint,
        probe_ch=_probe_ch_test_endpoint,
        init_pg_schema=_run_pg_schema_bootstrap,
        init_ch_schema=_run_ch_schema_bootstrap,
        raise_docker_stage=_raise_docker_stage_error,
        sleep_fn=time.sleep,
        startup_max_retries=SETUP_DB_STARTUP_MAX_RETRIES,
        startup_sleep_sec=SETUP_DB_STARTUP_SLEEP_SEC,
        settle_sleep_sec=SETUP_DB_SETTLE_SLEEP_SEC,
        init_max_retries=SETUP_DB_INIT_MAX_RETRIES,
        format_retry_diagnostic=_format_retry_diagnostic,
    )


def _raise_docker_stage_error(
    *,
    stage: str,
    command: tuple[str, ...] | list[str],
    exit_code: int,
    stderr: object,
    owner_action: object,
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
def _test_infra_lifecycle():
    """Session owner: Compose/schema bootstrap once; teardown once.

    Сам по себе НЕ стартует Docker — только создаёт lifecycle object.
    Side effects происходят через ``ensure_resources`` после gate.
    """
    global _TEST_INFRA_LIFECYCLE, _TEST_DB_READY
    lifecycle = _build_test_infra_lifecycle()
    _TEST_INFRA_LIFECYCLE = lifecycle
    _DOCKER_CLEANUP_STATE["compose_cmd"] = None
    primary_exc: BaseException | None = None
    try:
        yield lifecycle
    except BaseException as exc:  # noqa: BLE001 — preserve for teardown
        primary_exc = exc
        raise
    finally:
        try:
            lifecycle.teardown(primary_exception=primary_exc)
        finally:
            _TEST_INFRA_LIFECYCLE = None
            _TEST_DB_READY = False
            _DOCKER_CLEANUP_STATE["container_id"] = None
            _DOCKER_CLEANUP_STATE["compose_cmd"] = None


def _require_destructive_local(request: pytest.FixtureRequest) -> None:
    """Fail-closed: destructive fixtures требуют marker до Docker/engine/DDL."""
    from tests.support.destructive_markers import require_destructive_local_marker

    require_destructive_local_marker(request)


@pytest.fixture
def setup_test_database(request):
    """Ensure PG compose+schema (session-once) после marker/DSN gate.

    Function-scoped entrypoint: gate → validate → dynamic lifecycle acquisition.
    Compose down выполняется только в session teardown, не здесь.
    """
    global _TEST_DB_READY
    _require_destructive_local(request)
    from tests.support.destructive_lifecycle import TestResourceNeeds

    # Fail-closed preflight BEFORE any docker compose interaction.
    _validate_pg_preflight()

    lifecycle = _resolve_test_infra_lifecycle(request)
    _DOCKER_CLEANUP_STATE["compose_cmd"] = None
    try:
        lifecycle.ensure_resources(TestResourceNeeds(needs_pg=True))
        _TEST_DB_READY = bool(lifecycle.state.pg_ready)
        if lifecycle.state.compose_started_by_pytest:
            _DOCKER_CLEANUP_STATE["compose_cmd"] = lifecycle._compose_cmd
        print("[OK] Test database setup complete (session-scoped schema).")
        yield
    except BaseException as exc:  # noqa: BLE001
        # Partial failure: session teardown still owns cleanup.
        lifecycle.state.primary_failure = exc
        raise


@pytest.fixture(scope="function", name="async_engine")
async def _async_engine(request, setup_test_database, reset_postgres_test_data):
    """Function-scoped AsyncEngine (pytest-asyncio 0.21 loop safety).

    Compose/schema — session-once через ``setup_test_database``.
    Data reset — function-scoped через ``reset_postgres_test_data``.
    """
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


@pytest.fixture
async def reset_postgres_test_data(request, setup_test_database):
    """Function-scoped PG data reset (до test body, один раз).

    Не autouse: активируется только через PG fixture dependency chain.
    """
    _require_destructive_local(request)
    from tests.support.destructive_pg_reset import (
        reset_postgres_test_data as _reset_pg,
    )

    lifecycle = _resolve_test_infra_lifecycle(request)
    engine = _create_test_async_engine()
    try:
        await _reset_pg(engine, restore_baseline=True)
        lifecycle.record_pg_data_reset()
    finally:
        await engine.dispose()
    yield



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

    # Collection-time resource discovery + live-fixture marker invariant.
    from tests.support.destructive_lifecycle import (
        discover_session_resource_needs,
        item_uses_live_fixtures,
    )

    config._test_infra_needs = discover_session_resource_needs(items)  # type: ignore[attr-defined]
    missing_marker: list[str] = []
    for item in items:
        if item_uses_live_fixtures(item) and not _has_mark(item, "destructive_local"):
            missing_marker.append(item.nodeid)
    if missing_marker:
        raise pytest.UsageError(
            "Live PG/CH fixtures require @pytest.mark.destructive_local. "
            "Offenders:\n- " + "\n- ".join(missing_marker)
        )
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
    adv_setting_mock.bot_active = False
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
async def clickhouse_client(request):
    """Function-scoped GuardedClickHouseClient; schema DDL — session-once.

    Gate → CH validation → lifecycle.ensure(CH) → client → data reset → yield.
    Compose down — только session teardown. Не зависит от PG setup.
    """
    _require_destructive_local(request)
    from tests.support.destructive_ch_reset import (
        apply_clickhouse_session_ddl,
        reset_clickhouse_test_data,
    )
    from tests.support.destructive_clickhouse import (
        ALLOWED_CH_DATABASE,
        create_validated_async_clickhouse_client,
    )
    from tests.support.destructive_lifecycle import TestResourceNeeds

    _validate_ch_preflight()
    lifecycle = _resolve_test_infra_lifecycle(request)
    lifecycle.ensure_resources(TestResourceNeeds(needs_clickhouse=True))

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
                client.close()
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

    if not lifecycle.state.clickhouse_schema_initialized:
        await apply_clickhouse_session_ddl(client)
        lifecycle.state.clickhouse_schema_initialized = True
        lifecycle.state.clickhouse_schema_init_count += 1

    await reset_clickhouse_test_data(client)
    lifecycle.record_ch_data_reset()

    try:
        yield client
    finally:
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