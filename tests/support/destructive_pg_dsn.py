"""Fail-closed validator для destructive PostgreSQL integration DSN.

Любой live PG путь с DROP/CREATE/Alembic MUST вызвать
``validate_destructive_test_database_url`` **до** ``create_engine`` /
``create_async_engine``. ``bool(TEST_DATABASE_URL)`` недостаточен.

Allowlist (централизованно, без копипасты по тестам):

* host: ``localhost`` | ``127.0.0.1``
* port: ``5433`` (docker-compose.test.yml → test_db)
* database: ``test_adv_bot_db`` (ровно это имя)
* opt-in: ``ALLOW_DESTRUCTIVE_TEST_DB=1`` (или true/yes/on)
* tunnels: ``DEV_TUNNELS_ENABLED`` и родственные env — hard-fail

Production/stage/dev имена БД запрещены явно.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.engine.url import URL, make_url

ALLOWED_PG_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1"})
ALLOWED_PG_PORT: int = 5433
ALLOWED_PG_DATABASE: str = "test_adv_bot_db"
ALLOW_DESTRUCTIVE_TEST_DB_ENV: str = "ALLOW_DESTRUCTIVE_TEST_DB"
TEST_DATABASE_URL_ENV: str = "TEST_DATABASE_URL"

# Имена, которые никогда не считаются тестовыми (даже на localhost).
FORBIDDEN_PG_DATABASES: frozenset[str] = frozenset(
    {
        "adv_updater",
        "postgres",
        "template0",
        "template1",
        "production",
        "prod",
        "stage",
        "staging",
        "dev",
        "development",
        "adv_bot",
        "adv-bot",
    }
)

# Env denylist: legacy tunnel flags must stay false/unset for destructive tests.
TUNNEL_TRUTHY_ENV_KEYS: tuple[str, ...] = ("DEV_TUNNELS_ENABLED",)
TUNNEL_PRESENT_ENV_KEYS: tuple[str, ...] = (
    "DEV_TUNNELS_KUBECONFIG",
    "DEV_TUNNEL_PG_LOCAL_PORT",
    "DEV_TUNNEL_CH_HTTP_PORT",
)


class DestructiveTestDatabaseError(RuntimeError):
    """DSN не прошёл fail-closed allowlist — подключение запрещено."""


@dataclass(frozen=True, slots=True)
class ValidatedDestructivePgDsn:
    """Нормализованный безопасный DSN после валидации (без секретов в repr)."""

    host: str
    port: int
    database: str
    drivername: str

    def render_redacted(self) -> str:
        """Строка для логов/ошибок без password/user."""
        return f"{self.drivername}://***@{self.host}:{self.port}/{self.database}"


def _parse_truthy_opt_in(raw: str | None) -> bool:
    """Fail-closed bool: только явные 1/true/yes/on."""
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_destructive_pg_opt_in_enabled(
    *,
    environ: dict[str, str] | None = None,
) -> bool:
    """Проверить ``ALLOW_DESTRUCTIVE_TEST_DB`` без сетевого I/O."""
    env = environ if environ is not None else os.environ
    return _parse_truthy_opt_in(env.get(ALLOW_DESTRUCTIVE_TEST_DB_ENV))


def assert_no_dev_tunnels_for_destructive_tests(
    *,
    environ: dict[str, str] | None = None,
) -> None:
    """Hard-fail если включены/настроены k8s dev tunnels (port-forward risk).

    Не выполняет сетевых проверок — только env.
    """
    env = environ if environ is not None else os.environ
    for key in TUNNEL_TRUTHY_ENV_KEYS:
        if _parse_truthy_opt_in(env.get(key)):
            raise DestructiveTestDatabaseError(
                f"Destructive tests refuse connect: {key} is enabled. "
                "Localhost may be a kubectl port-forward to production/stage. "
                "Disable tunnels (DEV_TUNNELS_ENABLED=false) before destructive "
                "pytest."
            )
    for key in TUNNEL_PRESENT_ENV_KEYS:
        raw = env.get(key)
        if raw is not None and str(raw).strip():
            raise DestructiveTestDatabaseError(
                f"Destructive tests refuse connect: {key} is set. "
                "Unset tunnel/port-forward env before destructive pytest "
                "(localhost allowlist is not enough if ports are forwarded)."
            )


def validate_destructive_test_database_url(
    dsn: str | None,
    *,
    allow_destructive: bool | None = None,
    environ: dict[str, str] | None = None,
    check_tunnels: bool = True,
) -> ValidatedDestructivePgDsn:
    """Валидировать DSN до любого ``create_engine``.

    Args:
        dsn: явный PostgreSQL DSN (не читать из env внутри без передачи).
        allow_destructive: явный opt-in; ``None`` → читать env.
        environ: подмена os.environ для unit-тестов.
        check_tunnels: проверять DEV_TUNNELS_* env (по умолчанию да).

    Returns:
        Нормализованный snapshot host/port/database.

    Raises:
        DestructiveTestDatabaseError: пустой DSN, не-PG, чужой host/port/db,
            запрещённое имя БД, отсутствует opt-in, tunnels enabled.
    """
    env = environ if environ is not None else os.environ
    if check_tunnels:
        assert_no_dev_tunnels_for_destructive_tests(environ=dict(env))

    if dsn is None or not str(dsn).strip():
        raise DestructiveTestDatabaseError(
            "Destructive PG DSN is empty — refuse connect "
            f"(set {TEST_DATABASE_URL_ENV} only for disposable local test DB)"
        )

    opt_in = (
        allow_destructive
        if allow_destructive is not None
        else is_destructive_pg_opt_in_enabled(environ=dict(env))
    )
    if not opt_in:
        raise DestructiveTestDatabaseError(
            "Destructive PG tests require explicit opt-in "
            f"{ALLOW_DESTRUCTIVE_TEST_DB_ENV}=1 — refuse connect"
        )

    try:
        url: URL = make_url(str(dsn).strip())
    except Exception:  # noqa: BLE001 — не пробрасываем parse exc (может содержать DSN)
        raise DestructiveTestDatabaseError(
            "Destructive PG DSN is not a valid SQLAlchemy URL — refuse connect"
        ) from None

    driver = (url.drivername or "").lower()
    if not driver.startswith("postgresql"):
        raise DestructiveTestDatabaseError(
            f"Destructive PG DSN must use postgresql scheme, got {driver!r}"
        )

    host = (url.host or "").strip().lower()
    if host not in ALLOWED_PG_HOSTS:
        raise DestructiveTestDatabaseError(
            f"Destructive PG host {host!r} is not allowlisted "
            f"(allowed={sorted(ALLOWED_PG_HOSTS)}) — refuse connect"
        )

    port = int(url.port) if url.port is not None else 5432
    if port != ALLOWED_PG_PORT:
        raise DestructiveTestDatabaseError(
            f"Destructive PG port {port} is not the test port "
            f"{ALLOWED_PG_PORT} — refuse connect"
        )

    database = (url.database or "").strip()
    if not database:
        raise DestructiveTestDatabaseError(
            "Destructive PG DSN has empty database name — refuse connect"
        )
    db_lower = database.lower()
    if db_lower in FORBIDDEN_PG_DATABASES:
        raise DestructiveTestDatabaseError(
            f"Destructive PG database {database!r} is forbidden "
            f"(production/stage/dev names) — refuse connect"
        )
    if database != ALLOWED_PG_DATABASE:
        raise DestructiveTestDatabaseError(
            f"Destructive PG database must be exactly {ALLOWED_PG_DATABASE!r}, "
            f"got {database!r} — refuse connect"
        )

    return ValidatedDestructivePgDsn(
        host=host,
        port=port,
        database=database,
        drivername=driver,
    )


def create_validated_async_engine_from_url(
    dsn: str | None,
    *,
    create_async_engine_fn: Callable[..., Any],
    environ: dict[str, str] | None = None,
    **engine_kwargs: Any,
) -> Any:
    """Validation-before-connect для async engine (conftest / fixtures).

    ``create_async_engine_fn`` вызывается **только** после успешной валидации.
    """
    validate_destructive_test_database_url(dsn, environ=environ)
    assert dsn is not None  # narrowed by validator
    return create_async_engine_fn(dsn, **engine_kwargs)


def create_validated_sync_engine_from_url(
    dsn: str,
    *,
    create_engine_fn: Callable[..., Any],
    environ: dict[str, str] | None = None,
    **engine_kwargs: Any,
) -> Any:
    """Validation-before-connect для sync engine."""
    validate_destructive_test_database_url(dsn, environ=environ)
    return create_engine_fn(dsn, **engine_kwargs)


def require_validated_live_pg_dsn_or_skip() -> str:
    """Для pytest live-тестов: skip если URL unset; error если URL невалиден.

    Returns:
        Исходный ``TEST_DATABASE_URL`` после успешной валидации.

    Raises:
        DestructiveTestDatabaseError: URL задан, но не прошёл allowlist.
    """
    import pytest

    raw = os.environ.get(TEST_DATABASE_URL_ENV)
    if raw is None or not str(raw).strip():
        pytest.skip(f"{TEST_DATABASE_URL_ENV} not set")
    validate_destructive_test_database_url(raw)
    return str(raw).strip()
