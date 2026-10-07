"""Загрузка SQL из ``keyword_performance/sql/``."""

from __future__ import annotations

from pathlib import Path

_SQL_ROOT = Path(__file__).resolve().parent.parent / "sql"


def load_keyword_sql(name: str) -> str:
    """Читает ``{name}.sql`` из keyword_performance/sql."""
    return (_SQL_ROOT / f"{name}.sql").read_text(encoding="utf-8")
