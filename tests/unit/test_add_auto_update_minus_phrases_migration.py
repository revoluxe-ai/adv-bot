"""Тесты spec stage-landing-readiness для schema-only migration."""

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

    def drop_column(self, *args, **kwargs) -> None:
        self.calls.append(("drop_column", args, kwargs))


def test_upgrade_adds_expand_column_and_defers_classifier_to_job() -> None:
    """Spec stage-landing-readiness: backfill не должен быть broad Alembic DML."""
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
    assert column.nullable is True
    assert fake_op.calls == [add_column_call]


def test_downgrade_drops_column() -> None:
    """Spec stage-landing-readiness: локальный recovery удаляет только колонку."""
    module = _load_migration_module()
    fake_op = _FakeOp()
    module.op = fake_op

    module.downgrade()

    assert fake_op.calls == [("drop_column", ("advsetting", "auto_update_minus_phrases"), {})]
