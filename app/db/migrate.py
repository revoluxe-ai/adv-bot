"""
Безопасный entrypoint Alembic upgrade для Kubernetes Job.

Один SQLAlchemy Connection: identity checks, advisory lock, commit, затем
Alembic через Config.attributes['connection']. Не создаёт второй Engine
для upgrade.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.pool import NullPool

MIGRATION_LOCK_ID = 731_984_123


class MigrationOutcome(str, Enum):
    """Коды исхода migration Job (MVP без FAILED_ROLLED_BACK)."""

    SUCCESS = "SUCCESS"
    SUCCESS_NOOP = "SUCCESS_NOOP"
    SUCCESS_ALREADY_APPLIED = "SUCCESS_ALREADY_APPLIED"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    LOCK_NOT_ACQUIRED = "LOCK_NOT_ACQUIRED"
    PARTIAL_OR_UNKNOWN = "PARTIAL_OR_UNKNOWN"


@dataclass(frozen=True)
class MigrationResult:
    """Результат прогона migrate wrapper."""

    outcome: MigrationOutcome
    detail: str
    database_heads: tuple[str, ...]
    target: str


def _emit(result: MigrationResult) -> None:
    """Печатает машиночитаемый JSON-исход в stdout."""
    payload = {
        "outcome": result.outcome.value,
        "detail": result.detail,
        "database_heads": list(result.database_heads),
        "target": result.target,
        "release_id": os.environ.get("RELEASE_ID", ""),
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _require_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required for migration Job")
    return url


def _parse_expected_current_sets() -> list[frozenset[str]]:
    raw = os.environ.get("EXPECTED_CURRENT_REVISION_SETS", "").strip()
    if not raw:
        raise RuntimeError("EXPECTED_CURRENT_REVISION_SETS JSON is required")
    data = json.loads(raw)
    if not isinstance(data, list) or not data:
        raise RuntimeError("EXPECTED_CURRENT_REVISION_SETS must be a non-empty list of sets")
    sets: list[frozenset[str]] = []
    for item in cast(list[Any], data):
        if not isinstance(item, list) or not item:
            raise RuntimeError("each current revision set must be a non-empty list")
        sets.append(frozenset(str(x) for x in cast(list[Any], item)))
    return sets


def _resolve_target(script: ScriptDirectory) -> str:
    explicit = os.environ.get("EXPECTED_TARGET_REVISION", "").strip()
    if explicit:
        return explicit
    if os.environ.get("ALLOW_UPGRADE_HEAD", "").strip() == "1":
        heads = script.get_heads()
        if len(heads) != 1:
            raise RuntimeError(f"expected exactly one script head, got {heads}")
        return heads[0]
    raise RuntimeError("EXPECTED_TARGET_REVISION is required (or ALLOW_UPGRADE_HEAD=1)")


def _script_heads(script: ScriptDirectory) -> frozenset[str]:
    return frozenset(script.get_heads())


def _db_heads(connection: Connection) -> frozenset[str]:
    """Текущие heads БД; отсутствующая alembic_version ≡ BASE (только 42P01)."""
    try:
        rows = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).fetchall()
    except ProgrammingError as exc:
        orig = getattr(exc, "orig", None)
        pgcode = getattr(orig, "pgcode", None)
        # Strict: only undefined_table. Permission denied / other codes must raise.
        if pgcode == "42P01":
            try:
                connection.rollback()
            except Exception:  # noqa: BLE001
                pass
            return frozenset({"BASE"})
        raise
    if not rows:
        return frozenset({"BASE"})
    return frozenset(str(r[0]) for r in rows)


def _validate_target_is_unique_head(
    script: ScriptDirectory, target: str
) -> MigrationResult | None:
    """Target обязан быть единственным script head (не любой ancestor)."""
    script_heads = _script_heads(script)
    if len(script_heads) != 1:
        return MigrationResult(
            MigrationOutcome.PRECONDITION_FAILED,
            f"script directory must have exactly one head, got {sorted(script_heads)}",
            tuple(),
            target,
        )
    head = next(iter(script_heads))
    if target != head:
        known = {rev.revision for rev in script.walk_revisions()}
        if target not in known:
            detail = f"target {target} not in script directory"
        else:
            detail = (
                f"target {target} is not the unique script head {head}; "
                "refusing incomplete-schema upgrade"
            )
        return MigrationResult(
            MigrationOutcome.PRECONDITION_FAILED,
            detail,
            tuple(),
            target,
        )
    return None


def _run_identity_checks(connection: Connection) -> None:
    row = connection.execute(
        text(
            "SELECT current_database() AS db, current_user AS usr, "
            "pg_backend_pid() AS pid, pg_is_in_recovery() AS recovering"
        )
    ).mappings().one()
    if bool(row["recovering"]):
        raise RuntimeError("refusing to migrate: pg_is_in_recovery() is true")
    print(
        json.dumps(
            {
                "identity": {
                    "database": row["db"],
                    "user": row["usr"],
                    "pid": row["pid"],
                    "recovering": bool(row["recovering"]),
                }
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


def _acquire_lock(connection: Connection) -> bool:
    acquired = connection.execute(
        text("SELECT pg_try_advisory_lock(:lock_id)"),
        {"lock_id": MIGRATION_LOCK_ID},
    ).scalar_one()
    return bool(acquired)


def _release_lock(connection: Connection) -> None:
    connection.execute(
        text("SELECT pg_advisory_unlock(:lock_id)"),
        {"lock_id": MIGRATION_LOCK_ID},
    )


def _maybe_set_role(connection: Connection) -> None:
    if os.environ.get("SET_ROLE_APP_OWNER", "").strip() != "1":
        return
    connection.execute(text("SET ROLE app_owner"))


def _maybe_reset_role(connection: Connection) -> None:
    if os.environ.get("SET_ROLE_APP_OWNER", "").strip() != "1":
        return
    connection.execute(text("RESET ROLE"))


def run_migration(engine: Engine | None = None) -> MigrationResult:
    """Выполняет guarded Alembic upgrade на одном Connection."""
    url = _require_database_url()
    own_engine = engine is None
    if engine is None:
        engine = create_engine(url, poolclass=NullPool, pool_pre_ping=True)

    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    target = _resolve_target(script)
    allowed_current = _parse_expected_current_sets()

    bad_target = _validate_target_is_unique_head(script, target)
    if bad_target is not None:
        if own_engine:
            engine.dispose()
        return bad_target

    receipt_state = os.environ.get("MIGRATION_RECEIPT_STATE", "").strip().upper()
    connection: Connection | None = None
    upgrade_started = False
    migrations_finished = False
    try:
        connection = engine.connect()
        _run_identity_checks(connection)
        if not _acquire_lock(connection):
            connection.commit()
            return MigrationResult(
                MigrationOutcome.LOCK_NOT_ACQUIRED,
                "Another database migration is already running",
                tuple(),
                target,
            )
        connection.commit()  # close autobegin after lock acquire path start

        # Re-enter for checks with lock held (session lock survives commit)
        current = _db_heads(connection)
        if current not in allowed_current:
            _release_lock(connection)
            connection.commit()
            return MigrationResult(
                MigrationOutcome.PRECONDITION_FAILED,
                f"current heads {sorted(current)} not in allowed sets",
                tuple(sorted(current)),
                target,
            )

        target_set = frozenset({target})
        if current == target_set:
            if receipt_state in {"MIGRATED", "SUCCEEDED", "NOOP", "COMPLETED"}:
                _release_lock(connection)
                connection.commit()
                return MigrationResult(
                    MigrationOutcome.SUCCESS_ALREADY_APPLIED,
                    "heads already at target with receipt",
                    tuple(sorted(current)),
                    target,
                )
            # first no-op for this release
            _release_lock(connection)
            connection.commit()
            return MigrationResult(
                MigrationOutcome.SUCCESS_NOOP,
                "heads already at target; created logical no-op path",
                tuple(sorted(current)),
                target,
            )

        _maybe_set_role(connection)
        connection.commit()  # mandatory before Alembic

        alembic_cfg.attributes["connection"] = connection

        # True only when Alembic actually enters run_migrations (see env.py).
        # Import/settings/configure failures before that stay PRECONDITION_FAILED.
        def _on_migrations_begin() -> None:
            nonlocal upgrade_started
            upgrade_started = True

        alembic_cfg.attributes["on_migrations_begin"] = _on_migrations_begin
        command.upgrade(alembic_cfg, target)
        # Alembic returned — revision DDL finished (or no-op upgrade path).
        migrations_finished = True

        after = _db_heads(connection)
        if after != target_set:
            try:
                _maybe_reset_role(connection)
                _release_lock(connection)
                connection.commit()
            except Exception:  # noqa: BLE001
                pass
            return MigrationResult(
                MigrationOutcome.PARTIAL_OR_UNKNOWN,
                f"after upgrade heads {sorted(after)} != target {target}",
                tuple(sorted(after)),
                target,
            )

        # Schema is at target: cleanup errors must not become PARTIAL_OR_UNKNOWN.
        cleanup_note = ""
        try:
            _maybe_reset_role(connection)
            _release_lock(connection)
            connection.commit()
        except Exception as cleanup_exc:  # noqa: BLE001
            cleanup_note = (
                f"; cleanup warning: {type(cleanup_exc).__name__}: {cleanup_exc}"
            )
            try:
                connection.invalidate()
            except Exception:  # noqa: BLE001
                pass
        return MigrationResult(
            MigrationOutcome.SUCCESS,
            f"upgrade completed{cleanup_note}",
            tuple(sorted(after)),
            target,
        )
    except Exception as exc:  # noqa: BLE001 — map to outcome codes
        if migrations_finished:
            # Upgrade returned OK; failure was in verify/cleanup. Confirm heads.
            heads: tuple[str, ...] = tuple()
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:  # noqa: BLE001
                    pass
                try:
                    heads = tuple(sorted(_db_heads(connection)))
                except Exception:  # noqa: BLE001
                    heads = tuple()
                try:
                    _maybe_reset_role(connection)
                    _release_lock(connection)
                    connection.commit()
                except Exception:  # noqa: BLE001
                    try:
                        connection.invalidate()
                    except Exception:  # noqa: BLE001
                        pass
            if heads and frozenset(heads) == frozenset({target}):
                return MigrationResult(
                    MigrationOutcome.SUCCESS,
                    (
                        "upgrade completed; post-upgrade error ignored: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                    heads,
                    target,
                )
            return MigrationResult(
                MigrationOutcome.PARTIAL_OR_UNKNOWN,
                f"post-upgrade verify failed: {type(exc).__name__}: {exc}",
                heads,
                target,
            )

        outcome = (
            MigrationOutcome.PARTIAL_OR_UNKNOWN
            if upgrade_started
            else MigrationOutcome.PRECONDITION_FAILED
        )
        heads = tuple()
        if connection is not None:
            try:
                connection.rollback()
            except Exception:  # noqa: BLE001
                pass
            try:
                heads = tuple(sorted(_db_heads(connection)))
            except Exception:  # noqa: BLE001
                heads = tuple()
            try:
                _release_lock(connection)
                connection.commit()
            except Exception:  # noqa: BLE001
                try:
                    connection.invalidate()
                except Exception:  # noqa: BLE001
                    pass
        return MigrationResult(outcome, f"{type(exc).__name__}: {exc}", heads, target)

    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001
                pass
        if own_engine:
            engine.dispose()


def main() -> int:
    """CLI entrypoint: 0 только для успешных исходов; всегда JSON outcome."""
    try:
        result = run_migration()
    except (RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        result = MigrationResult(
            MigrationOutcome.PRECONDITION_FAILED,
            f"{type(exc).__name__}: {exc}",
            tuple(),
            os.environ.get("EXPECTED_TARGET_REVISION", "").strip(),
        )
    _emit(result)
    if result.outcome in {
        MigrationOutcome.SUCCESS,
        MigrationOutcome.SUCCESS_NOOP,
        MigrationOutcome.SUCCESS_ALREADY_APPLIED,
    }:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
