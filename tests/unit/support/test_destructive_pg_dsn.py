"""Unit: fail-closed validator для destructive PostgreSQL test DSN.

Без сети и без create_engine — только allowlist / opt-in / tunnel правила.
Engine factory — mock; ``assert_not_called`` при каждом отказе.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.support.destructive_pg_dsn import (
    ALLOWED_PG_DATABASE,
    ALLOWED_PG_PORT,
    DestructiveTestDatabaseError,
    assert_no_dev_tunnels_for_destructive_tests,
    create_validated_async_engine_from_url,
    create_validated_sync_engine_from_url,
    validate_destructive_test_database_url,
)

_VALID = (
    f"postgresql+asyncpg://u:p@127.0.0.1:{ALLOWED_PG_PORT}/{ALLOWED_PG_DATABASE}"
)
_OPT_IN = {"ALLOW_DESTRUCTIVE_TEST_DB": "1"}


@pytest.mark.unit
def test_valid_localhost_with_opt_in() -> None:
    """Allowlist: 127.0.0.1:5433/test_adv_bot_db + opt-in."""
    got = validate_destructive_test_database_url(_VALID, environ=_OPT_IN)
    assert got.host == "127.0.0.1"
    assert got.port == ALLOWED_PG_PORT
    assert got.database == ALLOWED_PG_DATABASE
    redacted = got.render_redacted()
    assert "***" in redacted
    assert ":p@" not in redacted
    assert "password" not in redacted.lower()


@pytest.mark.unit
def test_valid_localhost_hostname_with_opt_in() -> None:
    """Allowlist: localhost hostname."""
    dsn = (
        f"postgresql://u:p@localhost:{ALLOWED_PG_PORT}/{ALLOWED_PG_DATABASE}"
    )
    got = validate_destructive_test_database_url(dsn, environ=_OPT_IN)
    assert got.host == "localhost"


@pytest.mark.unit
@pytest.mark.parametrize(
    "dsn",
    [
        None,
        "",
        "   ",
    ],
)
def test_empty_dsn_refused(dsn: str | None) -> None:
    """Пустой DSN — refuse до engine."""
    with pytest.raises(DestructiveTestDatabaseError, match="empty"):
        validate_destructive_test_database_url(dsn, environ=_OPT_IN)


@pytest.mark.unit
def test_missing_opt_in_refused() -> None:
    """Без ALLOW_DESTRUCTIVE_TEST_DB=1 — refuse."""
    with pytest.raises(DestructiveTestDatabaseError, match="opt-in"):
        validate_destructive_test_database_url(_VALID, environ={})


@pytest.mark.unit
def test_prod_host_refused() -> None:
    """Production FQDN не в allowlist."""
    dsn = (
        f"postgresql://u:p@postgres-db-0.postgres-db.prod-adv-bot.svc.cluster.local:"
        f"{ALLOWED_PG_PORT}/{ALLOWED_PG_DATABASE}"
    )
    with pytest.raises(DestructiveTestDatabaseError, match="not allowlisted"):
        validate_destructive_test_database_url(dsn, environ=_OPT_IN)


@pytest.mark.unit
def test_external_ip_refused() -> None:
    """Внешний IP — refuse (DOCUMENTATION IP, без connect)."""
    dsn = f"postgresql://u:p@203.0.113.10:{ALLOWED_PG_PORT}/{ALLOWED_PG_DATABASE}"
    with pytest.raises(DestructiveTestDatabaseError, match="not allowlisted"):
        validate_destructive_test_database_url(dsn, environ=_OPT_IN)


@pytest.mark.unit
def test_wrong_port_refused() -> None:
    """Порт 5432 (prod default) — refuse."""
    dsn = f"postgresql://u:p@127.0.0.1:5432/{ALLOWED_PG_DATABASE}"
    with pytest.raises(DestructiveTestDatabaseError, match="not the test port"):
        validate_destructive_test_database_url(dsn, environ=_OPT_IN)


@pytest.mark.unit
@pytest.mark.parametrize(
    "database",
    ["adv_updater", "postgres", "production", "stage", "adv_bot", "development"],
)
def test_forbidden_database_names_refused(database: str) -> None:
    """Имена prod/stage/dev БД запрещены даже на localhost."""
    dsn = f"postgresql://u:p@127.0.0.1:{ALLOWED_PG_PORT}/{database}"
    with pytest.raises(DestructiveTestDatabaseError):
        validate_destructive_test_database_url(dsn, environ=_OPT_IN)


@pytest.mark.unit
def test_non_pg_scheme_refused() -> None:
    """mysql:// и пр. — refuse."""
    dsn = f"mysql://u:p@127.0.0.1:{ALLOWED_PG_PORT}/{ALLOWED_PG_DATABASE}"
    with pytest.raises(DestructiveTestDatabaseError, match="postgresql"):
        validate_destructive_test_database_url(dsn, environ=_OPT_IN)


@pytest.mark.unit
def test_encoded_credentials_not_leaked_in_parse_error() -> None:
    """Невалидный URL с password — сообщение без секрета."""
    dsn = "not-a-url://user:SuperSecretPass@host/db"
    with pytest.raises(DestructiveTestDatabaseError) as ei:
        validate_destructive_test_database_url(dsn, environ=_OPT_IN)
    assert "SuperSecretPass" not in str(ei.value)


@pytest.mark.unit
def test_dev_tunnels_enabled_hard_fail() -> None:
    env = {**_OPT_IN, "DEV_TUNNELS_ENABLED": "true"}
    with pytest.raises(DestructiveTestDatabaseError, match="DEV_TUNNELS_ENABLED"):
        validate_destructive_test_database_url(_VALID, environ=env)


@pytest.mark.unit
def test_dev_tunnel_port_env_hard_fail() -> None:
    env = {**_OPT_IN, "DEV_TUNNEL_PG_LOCAL_PORT": "15432"}
    with pytest.raises(DestructiveTestDatabaseError, match="DEV_TUNNEL_PG_LOCAL_PORT"):
        assert_no_dev_tunnels_for_destructive_tests(environ=env)


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_dsn",
    [
        f"postgresql://u:p@203.0.113.10:{ALLOWED_PG_PORT}/{ALLOWED_PG_DATABASE}",
        f"postgresql://u:p@127.0.0.1:5432/{ALLOWED_PG_DATABASE}",
        f"postgresql://u:p@127.0.0.1:{ALLOWED_PG_PORT}/adv_bot",
        "",
    ],
)
def test_async_engine_factory_not_called_on_each_refusal(bad_dsn: str) -> None:
    """create_async_engine_fn не вызывается при любом отказе валидации."""
    factory = MagicMock()
    env = dict(_OPT_IN) if bad_dsn.strip() else dict(_OPT_IN)
    with pytest.raises(DestructiveTestDatabaseError):
        create_validated_async_engine_from_url(
            bad_dsn if bad_dsn.strip() else None,  # type: ignore[arg-type]
            create_async_engine_fn=factory,
            environ=env,
        )
    factory.assert_not_called()


@pytest.mark.unit
def test_async_engine_factory_not_called_without_opt_in() -> None:
    factory = MagicMock()
    with pytest.raises(DestructiveTestDatabaseError, match="opt-in"):
        create_validated_async_engine_from_url(
            _VALID,
            create_async_engine_fn=factory,
            environ={},
        )
    factory.assert_not_called()


@pytest.mark.unit
def test_sync_engine_factory_not_called_when_tunnels_enabled() -> None:
    factory = MagicMock()
    with pytest.raises(DestructiveTestDatabaseError, match="DEV_TUNNELS"):
        create_validated_sync_engine_from_url(
            _VALID,
            create_engine_fn=factory,
            environ={**_OPT_IN, "DEV_TUNNELS_ENABLED": "1"},
        )
    factory.assert_not_called()


@pytest.mark.unit
def test_engine_factory_called_only_after_valid_dsn() -> None:
    factory = MagicMock(return_value="engine")
    got = create_validated_async_engine_from_url(
        _VALID,
        create_async_engine_fn=factory,
        environ=_OPT_IN,
    )
    assert got == "engine"
    factory.assert_called_once()


@pytest.mark.unit
def test_bootstrap_engine_factory_not_called_when_dsn_invalid() -> None:
    """Клиент/engine factory не вызывается при невалидном DSN (контракт bootstrap)."""
    from tests.integration.card_ab_hold import _live_pg_bootstrap as boot

    factory = MagicMock()
    with (
        patch.object(boot, "create_engine", factory),
        patch.dict(
            "os.environ",
            {"ALLOW_DESTRUCTIVE_TEST_DB": "1", "TEST_DATABASE_URL": ""},
            clear=False,
        ),
    ):
        with pytest.raises(DestructiveTestDatabaseError):
            boot.create_validated_sync_engine(
                "postgresql://u:p@203.0.113.10:5433/test_adv_bot_db"
            )
    factory.assert_not_called()
