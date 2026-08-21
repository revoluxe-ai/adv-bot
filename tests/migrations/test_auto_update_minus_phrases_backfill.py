"""Тесты spec stage-landing-readiness для release backfill."""

from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.engine import Connection

from app.db.auto_update_minus_phrases_backfill import (
    apply_auto_update_minus_phrases_backfill,
    preview_auto_update_minus_phrases,
)

pytestmark = pytest.mark.unit


class _Result:
    """Минимальный capture-результат SQLAlchemy для SQL-path теста."""

    def __init__(
        self,
        *,
        mapping: dict[str, int] | None = None,
        scalar: int | None = None,
        rowcount: int = 0,
    ) -> None:
        self._mapping = mapping
        self._scalar = scalar
        self.rowcount = rowcount

    def mappings(self) -> _Result:
        return self

    def one(self) -> dict[str, int]:
        assert self._mapping is not None
        return self._mapping

    def scalar_one(self) -> int:
        assert self._scalar is not None
        return self._scalar


class _Connection:
    """Capture fake, сохраняющий реальный SQL boundary без patch функции."""

    def __init__(
        self,
        *,
        updated: int,
        incompatible: int,
        fail_on_constraint: bool = False,
    ) -> None:
        self.updated = updated
        self.incompatible = incompatible
        self.fail_on_constraint = fail_on_constraint
        self.sql: list[str] = []

    def execute(self, statement: Any) -> _Result:
        sql = str(statement)
        self.sql.append(sql)
        normalized = " ".join(sql.split()).lower()
        if self.fail_on_constraint and "set not null" in normalized:
            raise RuntimeError("interrupted before constraint completion")
        if "count(*) as total_records" in normalized:
            return _Result(
                mapping={
                    "total_records": 5,
                    "null_records": 2,
                    "active_records": 2,
                    "inactive_records": 3,
                    "expected_enabled_records": 1,
                    "expected_disabled_records": 1,
                }
            )
        if normalized.startswith("update advsetting"):
            return _Result(rowcount=self.updated)
        if "incompatible_records" in normalized:
            return _Result(scalar=self.incompatible)
        return _Result()


def test_preview_uses_null_only_classifier_distribution() -> None:
    """Preview считает expected только среди NULL, не по всей таблице."""
    connection = _Connection(updated=0, incompatible=0)

    preview = preview_auto_update_minus_phrases(cast(Connection, connection))

    assert preview.total_records == 5
    assert preview.null_records == 2
    assert preview.expected_enabled_records == 1
    assert preview.expected_disabled_records == 1


def test_backfill_updates_only_null_rows_and_forbids_broad_true_update() -> None:
    """NULL-only UPDATE: UI-тогглы / non-NULL не переписываются."""
    connection = _Connection(updated=2, incompatible=0)

    result = apply_auto_update_minus_phrases_backfill(cast(Connection, connection))

    assert result.updated_records == 2
    assert result.incompatible_records == 0
    update_sql = next(sql for sql in connection.sql if sql.lstrip().startswith("UPDATE"))
    normalized = " ".join(update_sql.split()).lower()
    assert "bot_active is true" in normalized
    assert "where auto_update_minus_phrases is null" in normalized
    assert "is distinct from" not in normalized
    assert "set auto_update_minus_phrases = true" not in normalized
    assert any("set default false" in " ".join(s.split()).lower() for s in connection.sql)
    assert any("set not null" in " ".join(s.split()).lower() for s in connection.sql)


def test_incompatible_residue_is_reported_for_job_gate() -> None:
    """Job gate видит оставшиеся NULL после backfill."""
    connection = _Connection(updated=2, incompatible=1)

    result = apply_auto_update_minus_phrases_backfill(cast(Connection, connection))

    assert result.incompatible_records == 1


def test_retry_after_interrupted_constraint_transition_is_idempotent() -> None:
    """Retry после partial transition безопасен (NULL уже заполнены → 0 updates)."""
    connection = _Connection(
        updated=2,
        incompatible=0,
        fail_on_constraint=True,
    )

    with pytest.raises(RuntimeError, match="interrupted"):
        apply_auto_update_minus_phrases_backfill(cast(Connection, connection))

    connection.fail_on_constraint = False
    connection.updated = 0
    result = apply_auto_update_minus_phrases_backfill(cast(Connection, connection))

    assert result.updated_records == 0
    assert result.incompatible_records == 0
