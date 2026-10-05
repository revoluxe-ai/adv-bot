"""SQL-контракт DDL shop-wide inventory и availability.

Spec: ``connected-shop-campaign-ad-data-collection`` (design §D.1, §F.2).
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Задача 2.1 доказывает текст миграции: квалификация ``default_db.``,
колонки inventory, ``route_version`` как колонка epoch (не аргумент
``ReplacingMergeTree``), append-only availability. Миграция на живую БД
не выполняется — proof это issued SQL, не mock writer'а.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "clickhouse_migrations"
    / "007_create_shop_campaign_inventory_and_availability.sql"
)

_INVENTORY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("shop_id", "String"),
    ("adv_id", "Int64"),
    ("nm_ids", "Array(UInt64)"),
    ("wb_status", "String"),
    ("wb_lifecycle", "String"),
    ("route", "String"),
    ("discovered_at", "DateTime"),
    ("last_seen_at", "DateTime"),
    ("route_version", "UInt64"),
    ("version", "UInt64"),
)

_AVAILABILITY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("shop_id", "String"),
    ("adv_id", "Int64"),
    ("collector_id", "String"),
    ("reason_code", "String"),
    ("route_version", "UInt64"),
)

_PRESERVED_FACT_TABLES: tuple[str, ...] = (
    "full_adv_wb_stat",
    "wb_common_stat",
    "clusters_adv_stats",
)


def _ddl_text() -> str:
    """Читает файл миграции 2.1 с диска.

    Spec ``connected-shop-campaign-ad-data-collection`` требует явный SQL
    ``default_db.<object>``. Тест смотрит файл, а не сессию клиента.
    """
    return _MIGRATION.read_text(encoding="utf-8")


def _strip_line_comments(ddl: str) -> str:
    """Убирает ``--`` комментарии, чтобы контракт не проходил по тексту шапки.

    Иначе упоминание колонки в комментарии закрыло бы отсутствующую колонку
    в ``CREATE TABLE``.
    """
    return "\n".join(
        line.split("--", maxsplit=1)[0] for line in ddl.splitlines()
    )


def _create_statements(ddl: str) -> dict[str, str]:
    """Возвращает тело каждого ``CREATE TABLE`` по квалифицированному имени.

    Spec требует две таблицы и запрещает неквалифицированный ``CREATE``.
    Скобки ``Array(...)`` не обрывают список колонок.
    """
    body = _strip_line_comments(ddl)
    header = re.compile(r"CREATE TABLE IF NOT EXISTS (default_db\.\w+)\s*\(")
    found: dict[str, str] = {}
    for match in header.finditer(body):
        name = match.group(1)
        depth = 1
        idx = match.end()
        while idx < len(body) and depth:
            if body[idx] == "(":
                depth += 1
            elif body[idx] == ")":
                depth -= 1
            idx += 1
        if depth != 0:
            raise AssertionError(f"unbalanced columns in {name}")
        engine = re.match(
            r"\s*ENGINE = ([^\n]+)\nORDER BY \(([^)]+)\)",
            body[idx:],
        )
        if engine is None:
            raise AssertionError(f"missing ENGINE/ORDER BY for {name}")
        found[name] = body[match.start() : idx + engine.end()]
    return found


def _columns(statement: str) -> tuple[tuple[str, str], ...]:
    """Разбирает список колонок внутри первых скобок ``CREATE TABLE``."""
    open_at = statement.index("(")
    depth = 0
    end: int | None = None
    for idx, char in enumerate(statement[open_at:], start=open_at):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                end = idx
                break
    if end is None:
        raise AssertionError("column list is not closed")
    inner = statement[open_at + 1 : end]
    columns: list[tuple[str, str]] = []
    buffer: list[str] = []
    depth = 0
    for char in inner:
        if char == "(":
            depth += 1
            buffer.append(char)
        elif char == ")":
            depth -= 1
            buffer.append(char)
        elif char == "," and depth == 0:
            _append_column(columns, "".join(buffer))
            buffer = []
        else:
            buffer.append(char)
    _append_column(columns, "".join(buffer))
    return tuple(columns)


def _append_column(columns: list[tuple[str, str]], raw_piece: str) -> None:
    """Добавляет одну колонку ``name type``, пропуская пустые куски."""
    piece = raw_piece.strip()
    if not piece:
        return
    name, type_name = piece.split(maxsplit=1)
    columns.append((name, type_name.strip()))


def test_migration_qualifies_both_shop_campaign_tables() -> None:
    """Оба CREATE квалифицированы ``default_db.`` и других CREATE нет.

    Decision ``clickhouse-sql-database-qualification``: рабочий CH SQL
    обязан нести имя БД в тексте, а не только в session database.
    """
    ddl = _ddl_text()
    statements = _create_statements(ddl)
    assert set(statements) == {
        "default_db.shop_campaign_inventory",
        "default_db.shop_campaign_collection_availability",
    }
    unqualified = re.search(
        r"CREATE TABLE IF NOT EXISTS (?!default_db\.)",
        _strip_line_comments(ddl),
    )
    assert unqualified is None


def test_inventory_columns_match_design_d1_and_existing_types() -> None:
    """Inventory содержит ровно колонки design §D.1 и типы существующих фактов.

    ``shop_id String``, ``adv_id Int64``, ``nm_ids Array(UInt64)`` взяты из
    shop-runner / PG BIGINT / CH ``nmid``, без новых product-полей.
    """
    statement = _create_statements(_ddl_text())[
        "default_db.shop_campaign_inventory"
    ]
    assert _columns(statement) == _INVENTORY_COLUMNS


def test_inventory_route_version_is_column_not_replacing_version() -> None:
    """``route_version`` — колонка epoch, а ``version`` — аргумент replace.

    Spec handoff: единственный durable route epoch —
    ``shop_campaign_inventory.route_version``. Optimistic ``version`` не
    подменяет epoch и не живёт в Redis.
    """
    statement = _create_statements(_ddl_text())[
        "default_db.shop_campaign_inventory"
    ]
    assert "ENGINE = ReplacingMergeTree(version)" in statement
    assert "ReplacingMergeTree(route_version)" not in statement
    assert "ORDER BY (shop_id, adv_id)" in statement
    names = [name for name, _type_name in _columns(statement)]
    assert "route_version" in names
    assert names.index("route_version") != names.index("version")


def test_availability_is_append_only_diagnostic_plane() -> None:
    """Availability — MergeTree с reason_code, collector_id и route_version.

    Задача 6.3 / design §F.3: диагностика append-only. ``route_version``
    строки — сверенный epoch inventory, не второй источник истины.
    """
    statement = _create_statements(_ddl_text())[
        "default_db.shop_campaign_collection_availability"
    ]
    assert _columns(statement) == _AVAILABILITY_COLUMNS
    assert "ENGINE = MergeTree()" in statement
    assert "ReplacingMergeTree" not in statement
    assert (
        "ORDER BY (shop_id, adv_id, collector_id, route_version, reason_code)"
        in statement
    )


def test_migration_does_not_create_redis_epoch_or_alter_fact_tables() -> None:
    """Миграция не заводит Redis epoch и не меняет существующие fact-таблицы.

    Design §C: Redis MAY быть lock, но не SoT. Fact grains
    ``full_adv_wb_stat`` / ``wb_common_stat`` / ``clusters_adv_stats``
    остаются как есть.
    """
    body = _strip_line_comments(_ddl_text()).lower()
    assert "redis" not in body
    for table in _PRESERVED_FACT_TABLES:
        assert f"alter table default_db.{table}" not in body
        assert f"create table if not exists default_db.{table}" not in body
    raw = _ddl_text().lower()
    assert "route_version" in raw
    assert "redis" in raw
