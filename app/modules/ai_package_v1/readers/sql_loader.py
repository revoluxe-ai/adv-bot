"""Загрузка SQL-шаблонов из ``app/modules/ai_package_v1/sql/``."""

from __future__ import annotations

from pathlib import Path

_SQL_ROOT = Path(__file__).resolve().parent.parent / "sql"


def load_sql(name: str) -> str:
    """
    Читает файл ``{name}.sql`` из каталога sql пакета.

    Args:
        name: Базовое имя без расширения.

    Returns:
        Текст запроса UTF-8.
    """
    path = _SQL_ROOT / f"{name}.sql"
    return path.read_text(encoding="utf-8")
