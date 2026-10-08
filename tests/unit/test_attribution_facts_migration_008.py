"""DDL boundary tests for reviewed attribution facts migration 008."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.clickhouse_migration_control_plane.corpus import immutable_fingerprint

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = (
    _ROOT / "scripts" / "clickhouse_migrations" / "008_create_attribution_facts.sql"
)
_RUNTIME_PACKAGE = _ROOT / "app" / "modules" / "attribution_facts"


def test_008_exact_hash_and_schema_contract_are_reviewed() -> None:
    raw = _MIGRATION.read_bytes()
    sql = raw.decode("utf-8")
    identity = next(
        version for version in immutable_fingerprint().versions if version.id == "008"
    )

    assert hashlib.sha256(raw).hexdigest() == identity.sha256
    assert identity.privilege_class == "schema_ddl"
    assert "CREATE TABLE IF NOT EXISTS default_db.attribution_fact_observations" in sql
    assert "CREATE TABLE IF NOT EXISTS default_db.attribution_day_reconciliation" in sql
    assert "attributed_gmv_rub" in sql
    assert "spend_rub" not in sql.lower()
    assert "ENGINE = MergeTree()" in sql
    assert " ON CLUSTER " not in sql.upper()
    assert "GRANT " not in sql.upper()


def test_runtime_attribution_package_contains_no_schema_ddl_execution() -> None:
    forbidden = ("CREATE TABLE", "ALTER TABLE", "DROP TABLE")
    for path in _RUNTIME_PACKAGE.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        source = path.read_text(encoding="utf-8")
        upper = source.upper()
        for token in forbidden:
            assert token not in upper, f"{path} contains runtime DDL token {token}"
