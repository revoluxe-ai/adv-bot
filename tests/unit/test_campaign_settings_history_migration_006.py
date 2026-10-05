"""DDL boundary tests for reviewed campaign settings history migration 006."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.clickhouse_migration_control_plane.corpus import immutable_fingerprint

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = (
    _ROOT
    / "scripts"
    / "clickhouse_migrations"
    / "006_create_campaign_settings_history.sql"
)
_RUNTIME_PACKAGE = _ROOT / "app" / "modules" / "campaign_settings_history"


def test_006_exact_hash_and_schema_contract_are_reviewed() -> None:
    """Spec campaign-settings-history: 006 has reviewed bytes and exact table shape."""
    raw = _MIGRATION.read_bytes()
    sql = raw.decode("utf-8")
    identity = next(
        version
        for version in immutable_fingerprint().versions
        if version.id == "006"
    )

    assert hashlib.sha256(raw).hexdigest() == identity.sha256
    assert identity.filename == _MIGRATION.name
    assert identity.privilege_class == "schema_ddl"
    assert "CREATE TABLE IF NOT EXISTS default_db.campaign_settings_history" in sql
    for column_contract in (
        "observed_at DateTime64(3, 'UTC')",
        "snapshot_id UUID",
        "adv_setting_id UInt64",
        "wb_cabinet_id UInt64",
        "shop_id String",
        "adv_id Nullable(UInt64)",
        "search_adv_id Nullable(UInt64)",
        "schema_version UInt16",
        "state_hash FixedString(64)",
        "payload_json String",
    ):
        assert column_contract in sql
    assert "ENGINE = MergeTree()" in sql
    assert "PARTITION BY toYYYYMM(observed_at)" in sql
    assert (
        "ORDER BY (wb_cabinet_id, adv_setting_id, observed_at, snapshot_id)"
        in sql
    )
    assert " ON CLUSTER " not in sql.upper()
    assert "GRANT " not in sql.upper()


def test_runtime_history_package_contains_no_schema_ddl_execution() -> None:
    """Spec campaign-settings-history: runtime SELECT/INSERT layer cannot own DDL."""
    forbidden = (
        "CREATE TABLE",
        "ALTER TABLE",
        "DROP TABLE",
        "006_create_campaign_settings_history.sql",
    )

    for path in _RUNTIME_PACKAGE.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        upper = source.upper()
        for token in forbidden[:3]:
            assert token not in upper, f"{path.name} contains runtime DDL token {token}"
        assert forbidden[3] not in source
