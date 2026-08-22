"""Migration compatibility: epoch PG defaults без live DB (§19.5 / §22.5)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect

from app.modules.common_slaves.wildberries.models.models import AdvSetting

_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "alembic_"
    / "versions"
    / "d0e1f2a3b4c5_add_card_ab_hold_epoch_lifecycle_fields.py"
)


@pytest.mark.unit
def test_migration_source_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration {_MIGRATION}"


@pytest.mark.unit
def test_migration_phase_nullable() -> None:
    """``card_ab_hold_phase`` MUST be nullable (legacy MVP-1 NULL)."""
    text = _MIGRATION.read_text(encoding="utf-8")
    assert '"card_ab_hold_phase"' in text or "'card_ab_hold_phase'" in text
    assert "nullable=True" in text
    mapper = sa_inspect(AdvSetting)
    col = mapper.columns["card_ab_hold_phase"]
    assert col.nullable is True
    assert col.default is None or col.default.arg is None


@pytest.mark.unit
def test_migration_generation_default_zero() -> None:
    """generation default/server_default = 0."""
    text = _MIGRATION.read_text(encoding="utf-8")
    assert "card_ab_hold_generation" in text
    assert 'server_default=sa.text("0")' in text
    col = sa_inspect(AdvSetting).columns["card_ab_hold_generation"]
    assert col.server_default is not None
    assert str(col.server_default.arg) == "0"
    assert col.default.arg == 0


@pytest.mark.unit
def test_migration_sync_status_default_none() -> None:
    """sync_status default ``none``."""
    text = _MIGRATION.read_text(encoding="utf-8")
    assert "card_ab_hold_sync_status" in text
    assert "server_default=sa.text(\"'none'\")" in text
    col = sa_inspect(AdvSetting).columns["card_ab_hold_sync_status"]
    assert col.server_default is not None
    assert str(col.server_default.arg) == "'none'"


@pytest.mark.unit
def test_migration_unique_idempotency_key() -> None:
    """Unique constraint on ``card_ab_hold_wb_sync_idempotency_key``."""
    text = _MIGRATION.read_text(encoding="utf-8")
    assert "uq_advsetting_card_ab_hold_wb_sync_idempotency_key" in text
    col = sa_inspect(AdvSetting).columns["card_ab_hold_wb_sync_idempotency_key"]
    assert col.unique is True


@pytest.mark.unit
def test_migration_downgrade_drops_epoch_cols_only() -> None:
    """Downgrade MUST NOT drop legacy mode/snapshot/degraded columns."""
    text = _MIGRATION.read_text(encoding="utf-8")
    tree = ast.parse(text)
    drop_cols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "drop_column":
                if node.args and isinstance(node.args[1], ast.Constant):
                    drop_cols.append(str(node.args[1].value))
    assert "card_ab_hold_mode" not in drop_cols
    assert "card_ab_hold_allowed_phrases_snapshot" not in drop_cols
    assert "card_ab_hold_degraded" not in drop_cols
    assert "card_ab_hold_phase" in drop_cols
    assert "card_ab_hold_generation" in drop_cols
