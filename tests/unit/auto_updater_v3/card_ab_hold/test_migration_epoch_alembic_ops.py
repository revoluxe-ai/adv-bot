"""Статические проверки Alembic epoch migration (§19.5 / §22.5).

Live upgrade/downgrade: ``tests/integration/card_ab_hold/test_migration_epoch_live_pg.py``.
"""

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

_EPOCH_COLUMNS = [
    "card_ab_hold_phase",
    "card_ab_hold_warmup_started_at",
    "card_ab_hold_warmup_duration_hours",
    "card_ab_hold_generation",
    "card_ab_hold_wb_sync_idempotency_key",
    "card_ab_hold_pending_intent_json",
    "card_ab_hold_sync_status",
    "card_ab_hold_confirmed_keywords_json",
    "card_ab_hold_confirmed_target_places_json",
    "card_ab_hold_confirmed_auto_participation",
    "card_ab_hold_confirmed_auto_bid",
]


def _migration_drop_columns() -> list[str]:
    text = _MIGRATION.read_text(encoding="utf-8")
    tree = ast.parse(text)
    drop_cols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "drop_column":
                if node.args and isinstance(node.args[1], ast.Constant):
                    drop_cols.append(str(node.args[1].value))
    return drop_cols


@pytest.mark.unit
@pytest.mark.parametrize("col", _EPOCH_COLUMNS)
def test_orm_and_migration_define_epoch_column(col: str) -> None:
    """Каждая epoch-колонка присутствует в ORM и migration upgrade."""
    text = _MIGRATION.read_text(encoding="utf-8")
    assert col in text
    assert col in sa_inspect(AdvSetting).columns


@pytest.mark.unit
def test_migration_downgrade_drops_all_epoch_columns_only() -> None:
    """Downgrade удаляет ровно epoch-колонки; legacy mode/snapshot/degraded сохраняются."""
    drop_cols = _migration_drop_columns()
    for col in _EPOCH_COLUMNS:
        assert col in drop_cols
    assert "card_ab_hold_mode" not in drop_cols
    assert "card_ab_hold_allowed_phrases_snapshot" not in drop_cols
    assert "card_ab_hold_degraded" not in drop_cols


@pytest.mark.unit
def test_migration_check_constraint_warmup_min_24() -> None:
    text = _MIGRATION.read_text(encoding="utf-8")
    assert "ck_advsetting_card_ab_hold_warmup_duration_hours_min" in text
    assert "card_ab_hold_warmup_duration_hours >= 24" in text


@pytest.mark.unit
def test_migration_unique_idempotency_constraint_named() -> None:
    text = _MIGRATION.read_text(encoding="utf-8")
    assert "uq_advsetting_card_ab_hold_wb_sync_idempotency_key" in text
    assert "create_unique_constraint" in text
