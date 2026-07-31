"""Unit: ветки исходов app.db.migrate без живой БД."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.db.migrate import MigrationOutcome, main, run_migration


@pytest.fixture
def env_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("EXPECTED_TARGET_REVISION", "f2a3b4c5d6e7")
    monkeypatch.setenv(
        "EXPECTED_CURRENT_REVISION_SETS",
        '[["d0e1f2a3b4c5"],["f2a3b4c5d6e7"],["BASE"]]',
    )


def test_lock_not_acquired(env_ok: None) -> None:
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value = conn
    conn.execute.side_effect = [
        MagicMock(
            mappings=lambda: MagicMock(
                one=lambda: {
                    "db": "db",
                    "usr": "u",
                    "pid": 1,
                    "recovering": False,
                }
            )
        ),
        MagicMock(scalar_one=lambda: False),
    ]
    with patch("app.db.migrate.ScriptDirectory") as sd:
        sd.from_config.return_value.get_heads.return_value = ["f2a3b4c5d6e7"]
        sd.from_config.return_value.walk_revisions.return_value = [
            SimpleNamespace(revision="f2a3b4c5d6e7")
        ]
        result = run_migration(engine=engine)
    assert result.outcome == MigrationOutcome.LOCK_NOT_ACQUIRED


def test_success_noop_when_already_at_target(env_ok: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MIGRATION_RECEIPT_STATE", raising=False)
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value = conn

    def execute(stmt, params=None):  # noqa: ANN001
        sql = str(stmt)
        if "pg_is_in_recovery" in sql:
            return MagicMock(
                mappings=lambda: MagicMock(
                    one=lambda: {
                        "db": "db",
                        "usr": "u",
                        "pid": 1,
                        "recovering": False,
                    }
                )
            )
        if "pg_try_advisory_lock" in sql:
            return MagicMock(scalar_one=lambda: True)
        if "alembic_version" in sql:
            return MagicMock(fetchall=lambda: [("f2a3b4c5d6e7",)])
        if "pg_advisory_unlock" in sql:
            return MagicMock()
        return MagicMock()

    conn.execute.side_effect = execute
    with patch("app.db.migrate.ScriptDirectory") as sd:
        sd.from_config.return_value.get_heads.return_value = ["f2a3b4c5d6e7"]
        sd.from_config.return_value.walk_revisions.return_value = [
            SimpleNamespace(revision="f2a3b4c5d6e7")
        ]
        result = run_migration(engine=engine)
    assert result.outcome == MigrationOutcome.SUCCESS_NOOP


def test_non_head_target_rejected(env_ok: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ancestor id must not upgrade below the unique script head."""
    monkeypatch.setenv("EXPECTED_TARGET_REVISION", "d0e1f2a3b4c5")
    engine = MagicMock()
    with patch("app.db.migrate.ScriptDirectory") as sd:
        sd.from_config.return_value.get_heads.return_value = ["f2a3b4c5d6e7"]
        sd.from_config.return_value.walk_revisions.return_value = [
            SimpleNamespace(revision="d0e1f2a3b4c5"),
            SimpleNamespace(revision="f2a3b4c5d6e7"),
        ]
        result = run_migration(engine=engine)
    assert result.outcome == MigrationOutcome.PRECONDITION_FAILED
    assert "not the unique script head" in result.detail
    engine.connect.assert_not_called()


def test_main_emits_json_on_missing_env(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("EXPECTED_TARGET_REVISION", "f2a3b4c5d6e7")
    code = main()
    assert code == 1
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["outcome"] == "PRECONDITION_FAILED"
    assert "DATABASE_URL" in payload["detail"]


def test_db_heads_missing_table_is_base() -> None:
    from sqlalchemy.exc import ProgrammingError

    from app.db.migrate import _db_heads

    conn = MagicMock()
    err = ProgrammingError(
        "SELECT version_num FROM alembic_version",
        {},
        Exception("relation \"alembic_version\" does not exist"),
    )
    err.orig = SimpleNamespace(pgcode="42P01")
    conn.execute.side_effect = err
    assert _db_heads(conn) == frozenset({"BASE"})
    conn.rollback.assert_called()


def test_db_heads_permission_denied_not_base() -> None:
    from sqlalchemy.exc import ProgrammingError

    from app.db.migrate import _db_heads

    conn = MagicMock()
    err = ProgrammingError(
        "SELECT version_num FROM alembic_version",
        {},
        Exception("permission denied for table alembic_version"),
    )
    err.orig = SimpleNamespace(pgcode="42501")
    conn.execute.side_effect = err
    with pytest.raises(ProgrammingError):
        _db_heads(conn)


def test_upgrade_import_failure_is_precondition_not_partial(
    env_ok: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failures before run_migrations must not be PARTIAL_OR_UNKNOWN."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value = conn

    def execute(stmt, params=None):  # noqa: ANN001
        sql = str(stmt)
        if "pg_is_in_recovery" in sql:
            return MagicMock(
                mappings=lambda: MagicMock(
                    one=lambda: {
                        "db": "db",
                        "usr": "u",
                        "pid": 1,
                        "recovering": False,
                    }
                )
            )
        if "pg_try_advisory_lock" in sql:
            return MagicMock(scalar_one=lambda: True)
        if "alembic_version" in sql:
            return MagicMock(fetchall=lambda: [("d0e1f2a3b4c5",)])
        if "pg_advisory_unlock" in sql:
            return MagicMock()
        return MagicMock()

    conn.execute.side_effect = execute

    def boom(_cfg, _target):  # noqa: ANN001
        raise RuntimeError("env import failed before migrations")

    with patch("app.db.migrate.ScriptDirectory") as sd:
        sd.from_config.return_value.get_heads.return_value = ["f2a3b4c5d6e7"]
        sd.from_config.return_value.walk_revisions.return_value = [
            SimpleNamespace(revision="f2a3b4c5d6e7"),
            SimpleNamespace(revision="d0e1f2a3b4c5"),
        ]
        with patch("app.db.migrate.command.upgrade", side_effect=boom):
            result = run_migration(engine=engine)
    assert result.outcome == MigrationOutcome.PRECONDITION_FAILED
    assert "env import failed" in result.detail


def test_upgrade_after_migrations_begin_is_partial(
    env_ok: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Once on_migrations_begin fires, failures are PARTIAL_OR_UNKNOWN."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value = conn

    def execute(stmt, params=None):  # noqa: ANN001
        sql = str(stmt)
        if "pg_is_in_recovery" in sql:
            return MagicMock(
                mappings=lambda: MagicMock(
                    one=lambda: {
                        "db": "db",
                        "usr": "u",
                        "pid": 1,
                        "recovering": False,
                    }
                )
            )
        if "pg_try_advisory_lock" in sql:
            return MagicMock(scalar_one=lambda: True)
        if "alembic_version" in sql:
            return MagicMock(fetchall=lambda: [("d0e1f2a3b4c5",)])
        if "pg_advisory_unlock" in sql:
            return MagicMock()
        return MagicMock()

    conn.execute.side_effect = execute

    def boom(cfg, _target):  # noqa: ANN001
        cb = cfg.attributes.get("on_migrations_begin")
        assert callable(cb)
        cb()
        raise RuntimeError("DDL failed mid-upgrade")

    with patch("app.db.migrate.ScriptDirectory") as sd:
        sd.from_config.return_value.get_heads.return_value = ["f2a3b4c5d6e7"]
        sd.from_config.return_value.walk_revisions.return_value = [
            SimpleNamespace(revision="f2a3b4c5d6e7"),
            SimpleNamespace(revision="d0e1f2a3b4c5"),
        ]
        with patch("app.db.migrate.command.upgrade", side_effect=boom):
            result = run_migration(engine=engine)
    assert result.outcome == MigrationOutcome.PARTIAL_OR_UNKNOWN
    assert "DDL failed" in result.detail


def test_post_upgrade_cleanup_error_still_success(env_ok: None) -> None:
    """Cleanup failure after successful upgrade must not be PARTIAL_OR_UNKNOWN."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value = conn
    calls = {"n": 0}

    def execute(stmt, params=None):  # noqa: ANN001
        sql = str(stmt)
        if "pg_is_in_recovery" in sql:
            return MagicMock(
                mappings=lambda: MagicMock(
                    one=lambda: {
                        "db": "db",
                        "usr": "u",
                        "pid": 1,
                        "recovering": False,
                    }
                )
            )
        if "pg_try_advisory_lock" in sql:
            return MagicMock(scalar_one=lambda: True)
        if "alembic_version" in sql:
            # Before upgrade: parent; after upgrade: head
            calls["n"] += 1
            if calls["n"] == 1:
                return MagicMock(fetchall=lambda: [("d0e1f2a3b4c5",)])
            return MagicMock(fetchall=lambda: [("f2a3b4c5d6e7",)])
        if "pg_advisory_unlock" in sql:
            raise RuntimeError("unlock failed after upgrade")
        return MagicMock()

    conn.execute.side_effect = execute

    def ok_upgrade(cfg, _target):  # noqa: ANN001
        cb = cfg.attributes.get("on_migrations_begin")
        if callable(cb):
            cb()

    with patch("app.db.migrate.ScriptDirectory") as sd:
        sd.from_config.return_value.get_heads.return_value = ["f2a3b4c5d6e7"]
        sd.from_config.return_value.walk_revisions.return_value = [
            SimpleNamespace(revision="f2a3b4c5d6e7"),
            SimpleNamespace(revision="d0e1f2a3b4c5"),
        ]
        with patch("app.db.migrate.command.upgrade", side_effect=ok_upgrade):
            result = run_migration(engine=engine)
    assert result.outcome == MigrationOutcome.SUCCESS
    assert "cleanup warning" in result.detail
