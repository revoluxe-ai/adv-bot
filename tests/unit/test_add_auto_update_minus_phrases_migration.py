"""Unit tests for the auto_update_minus_phrases Alembic migration."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa


pytestmark = pytest.mark.unit


def _load_migration_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "alembic_" / "versions" / (
        "d1e2f3a4b5c6_add_auto_update_minus_phrases_to_advsetting.py"
    )
    spec = importlib.util.spec_from_file_location("minus_phrases_migration", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeOp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def add_column(self, *args, **kwargs) -> None:
        self.calls.append(("add_column", args, kwargs))

    def execute(self, *args, **kwargs) -> None:
        self.calls.append(("execute", args, kwargs))

    def alter_column(self, *args, **kwargs) -> None:
        self.calls.append(("alter_column", args, kwargs))

    def drop_column(self, *args, **kwargs) -> None:
        self.calls.append(("drop_column", args, kwargs))


def test_upgrade_sets_existing_rows_true_and_new_rows_false() -> None:
    module = _load_migration_module()
    fake_op = _FakeOp()
    module.op = fake_op

    module.upgrade()

    assert module.revision == "d1e2f3a4b5c6"
    assert module.down_revision == "92bdd3917621"

    add_column_call = fake_op.calls[0]
    assert add_column_call[0] == "add_column"
    assert add_column_call[1][0] == "advsetting"
    column = add_column_call[1][1]
    assert column.name == "auto_update_minus_phrases"
    assert isinstance(column.type, sa.Boolean)
    assert str(column.server_default.arg) == "false"

    execute_call = fake_op.calls[1]
    assert execute_call[0] == "execute"
    execute_sql = str(execute_call[1][0]).lower()
    assert "update advsetting" in execute_sql
    assert "set auto_update_minus_phrases = true" in execute_sql
    assert "where auto_update_minus_phrases is null" in execute_sql

    alter_call = fake_op.calls[2]
    assert alter_call[0] == "alter_column"
    assert alter_call[1][0] == "advsetting"
    assert alter_call[1][1] == "auto_update_minus_phrases"
    assert alter_call[2]["nullable"] is False
    assert str(alter_call[2]["server_default"].text) == "false"


def test_downgrade_drops_column() -> None:
    module = _load_migration_module()
    fake_op = _FakeOp()
    module.op = fake_op

    module.downgrade()

    assert fake_op.calls == [("drop_column", ("advsetting", "auto_update_minus_phrases"), {})]
