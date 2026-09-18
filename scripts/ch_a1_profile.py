"""Profiling-first ClickHouse evidence collector for the ООО «А1» case.

Модуль выполняет только bounded metadata/aggregate/sample SELECT-запросы.
Полные физические строки ClickHouse не выгружаются: для больших таблиц
сохраняются schema, агрегированные профили, распределения, sample rows и
воспроизводимые SQL. PostgreSQL профилируется по уже собранным безопасным
CSV-строкам, Redis остаётся вне critical path как cache/current state.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts import ch_a1_evidence as evidence


PROFILE_FAMILIES = (
    "orders_sales",
    "advertising",
    "campaign_state",
    "funnel",
    "normquery_search",
    "product_state",
)


def _as_int(value: Any) -> int:
    """Преобразовать значение ClickHouse metadata в int без исключения."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _actual_columns(columns: list[dict[str, Any]]) -> dict[str, str]:
    """Вернуть mapping lowercase column name -> фактическое имя."""
    return {
        str(row.get("name", "")).lower(): str(row.get("name", ""))
        for row in columns
        if row.get("name")
    }


def _qualified(database: str, table: str) -> str:
    """Собрать безопасное имя ClickHouse table."""
    return f"{evidence.quote_ch(database)}.{evidence.quote_ch(table)}"


def _quote_ch_string(value: str) -> str:
    """Экранировать строковый литерал ClickHouse."""
    return "'" + value.replace("'", "''") + "'"


def _profile_query(
    root: Path,
    sequence: int,
    name: str,
    query: str,
    *,
    timeout_seconds: int = 1800,
) -> tuple[list[dict[str, Any]], dict[str, Any], Path, Path]:
    """Выполнить bounded SELECT и сохранить его JSONL/SQL."""
    stem = f"{sequence:04d}_{evidence.safe_filename(name)}"
    output = root / "query_results" / f"{stem}.jsonl"
    sql_path = root / "sql" / f"{stem}.sql"
    status = evidence.run_ch_query(
        query,
        output,
        sql_path,
        timeout_seconds=timeout_seconds,
    )
    return evidence.read_jsonl(output), status, output, sql_path


def _parse_sorting_key(value: str, available: set[str]) -> list[str]:
    """Извлечь простые column names из ORDER BY для logical-key probe."""
    result: list[str] = []
    for raw_part in value.strip("() ").split(","):
        part = raw_part.strip().strip("`")
        if part and part.lower() in available:
            result.append(part)
    return result


def _compact_columns(columns: list[str], family: str) -> list[str]:
    """Выбрать минимальную projection для ожидаемого analytical export."""
    wanted_by_family = {
        "orders_sales": (
            "shop_id", "nmid", "nm_id", "date", "event_date", "event_time",
            "timestamp", "order_id", "sale_id", "srid", "orders", "sales",
            "buyouts", "buy_outs", "returns", "cancel", "price", "discount",
            "spp", "warehouse", "logistics",
        ),
        "advertising": (
            "adv_id", "advert_id", "campaign_id", "complex_adv_id", "nmid", "nm_id", "date",
            "event_date", "views", "impressions", "clicks", "ctr", "cpc",
            "cpm", "spend", "sum", "orders", "added_to_cart", "carts",
        ),
        "campaign_state": (
            "adv_id", "campaign_id", "nmid", "nm_id", "date", "event_date",
            "ts", "timestamp", "src_ts", "version", "ver", "sign", "bid",
            "bid_minor", "cpo", "budget", "mode", "strategy", "status",
        ),
        "funnel": (
            "shop_id", "nmid", "nm_id", "date", "event_date", "open_card",
            "views", "add_to_cart", "carts", "orders", "orders_sum",
            "buy_outs", "buyouts_sum_rub",
        ),
        "normquery_search": (
            "adv_id", "campaign_id", "nmid", "nm_id", "date", "event_date",
            "norm_query", "query", "keyword", "text", "position", "rank",
            "views", "impressions", "clicks", "carts", "orders", "spend",
            "bid",
        ),
        "product_state": (
            "shop_id", "nmid", "nm_id", "date", "event_date", "timestamp",
            "price", "discount", "spp", "stock", "warehouse", "rating",
            "reviews", "review_count", "category", "subject",
        ),
    }
    lower = {column.lower(): column for column in columns}
    wanted = wanted_by_family.get(family, ())
    selected = [
        lower[name]
        for name in wanted
        if name in lower
    ]
    return selected or columns[: min(8, len(columns))]


def _expected_grain(family: str) -> str:
    """Вернуть целевой grain компактной выгрузки без выполнения трансформации."""
    return {
        "orders_sales": "event-level",
        "advertising": "date × campaign × nmID",
        "campaign_state": "change event",
        "funnel": "date × nmID",
        "normquery_search": "date × campaign × nmID × query",
        "product_state": "change-only or daily snapshot",
    }.get(family, "source row")


def _profile_family(table: str, columns: list[str]) -> str:
    """Снизить семантическую уверенность для внутренних aggregate tables."""
    family = evidence.choose_family(table, columns)
    if (
        table.startswith(".inner_id.")
        and any(column.lower().endswith("_state") for column in columns)
        and not any(
            column.lower() in {"adv_id", "campaign_id", "complex_adv_id"}
            for column in columns
        )
    ):
        return "unknown"
    return family


def _profile_clickhouse_table(
    root: Path,
    database: str,
    table: str,
    columns: list[dict[str, Any]],
    table_meta: dict[str, Any],
    parts: dict[str, Any],
    filter_sql: str,
    mapping: str,
    sequence: int,
) -> dict[str, Any]:
    """Профилировать одну A1-mapped ClickHouse table без raw dump."""
    names = [str(row.get("name", "")) for row in columns]
    actual = _actual_columns(columns)
    temporal = evidence.temporal_column(columns)
    qualified = _qualified(database, table)
    summary_fields = ["count() AS source_row_count"]
    if temporal:
        quoted_temporal = evidence.quote_ch(temporal)
        summary_fields.extend(
            [
                f"toString(min({quoted_temporal})) AS min_date",
                f"toString(max({quoted_temporal})) AS max_date",
            ]
        )
    id_columns = [
        actual[key]
        for key in (
            "shop_id",
            "cabinet_id",
            "wb_cabinet_id",
            "seller_id",
            "adv_id",
            "advert_id",
            "campaign_id",
            "complex_adv_id",
            "nmid",
            "nm_id",
        )
        if key in actual
    ]
    for column in dict.fromkeys(id_columns):
        alias = evidence.safe_filename(column.lower())
        summary_fields.append(
            f"uniqExact(toString({evidence.quote_ch(column)})) AS unique_{alias}"
        )
    summary_query = (
        f"SELECT {', '.join(summary_fields)} FROM {qualified} "
        f"WHERE {filter_sql}"
    )
    summary_rows, summary_status, _, summary_sql = _profile_query(
        root,
        sequence,
        f"{database}_{table}_summary",
        summary_query,
    )
    summary = summary_rows[0] if summary_rows else {}
    source_rows = _as_int(summary.get("source_row_count"))
    if not summary_status["success"]:
        source_rows = _as_int(parts.get("rows"))

    distribution: list[dict[str, Any]] = []
    distribution_status: dict[str, Any] = {"success": True}
    distribution_sql: Path | None = None
    if temporal:
        distribution_grain = "day" if source_rows > 5_000_000 else "month"
        period_expression = (
            f"toDate({evidence.quote_ch(temporal)})"
            if distribution_grain == "day"
            else f"toStartOfMonth(toDate({evidence.quote_ch(temporal)}))"
        )
        distribution_query = (
            f"SELECT toString({period_expression}) AS period, count() AS rows "
            f"FROM {qualified} WHERE {filter_sql} GROUP BY period ORDER BY period"
        )
        distribution, distribution_status, _, distribution_sql = _profile_query(
            root,
            sequence + 1,
            f"{database}_{table}_rows_by_{distribution_grain}",
            distribution_query,
        )
    sample_query = f"SELECT * FROM {qualified} WHERE {filter_sql} LIMIT 50"
    samples, sample_status, sample_path, sample_sql = _profile_query(
        root,
        sequence + 2,
        f"{database}_{table}_sample",
        sample_query,
    )

    logical_profile: dict[str, Any] = {}
    logical_status: dict[str, Any] = {"success": True}
    write_frequency: list[dict[str, Any]] = []
    write_frequency_status: dict[str, Any] = {"success": True, "available": False}
    write_frequency_sql: Path | None = None
    lower_names = set(actual)
    if table == "clusters_adv_stats" and {"adv_id", "nmid", "date"} <= lower_names:
        cluster_query = (
            f"SELECT count() AS physical_rows, "
            f"uniqExact(tuple({evidence.quote_ch('adv_id')}, {evidence.quote_ch('nmid')}, "
            f"{evidence.quote_ch('date')})) AS campaign_nmid_day_keys, "
            f"uniqCombined64(tuple({evidence.quote_ch('adv_id')}, {evidence.quote_ch('nmid')}, "
            f"{evidence.quote_ch('wb_category')}, {evidence.quote_ch('norm_query')}, "
            f"{evidence.quote_ch('date')})) AS campaign_nmid_query_day_keys, "
            f"uniqExact(tuple({evidence.quote_ch('adv_id')}, {evidence.quote_ch('nmid')}, "
            f"{evidence.quote_ch('date')}, {evidence.quote_ch('timestamp')})) "
            f"AS timestamp_keys FROM {qualified} WHERE {filter_sql}"
        )
        logical_rows, logical_status, _, logical_sql = _profile_query(
            root,
            sequence + 3,
            f"{database}_{table}_logical_keys",
            cluster_query,
        )
        logical_profile = logical_rows[0] if logical_rows else {}
        if "timestamp" in actual:
            write_query = (
                "SELECT toString(toStartOfHour(event_time)) AS write_hour, "
                "count() AS new_parts, sum(rows) AS rows "
                "FROM system.part_log "
                "WHERE database = "
                f"{_quote_ch_string(database)} AND table = {_quote_ch_string(table)} "
                "AND event_type = 'NewPart' "
                "GROUP BY write_hour ORDER BY write_hour"
            )
            (
                write_frequency,
                write_frequency_status,
                _,
                write_frequency_sql,
            ) = _profile_query(
                root,
                sequence + 4,
                f"{database}_{table}_write_frequency",
                write_query,
            )
            write_frequency_status["available"] = write_frequency_status["success"]
    elif "replacingmergetree" in str(table_meta.get("engine", "")).lower():
        sorting_key = _parse_sorting_key(
            str(table_meta.get("sorting_key", "")),
            set(actual),
        )
        if sorting_key and len(sorting_key) <= 5 and source_rows <= 5_000_000:
            order_projection = ", ".join(evidence.quote_ch(column) for column in sorting_key)
            logical_query = (
                f"SELECT count() AS physical_rows, "
                f"uniqExact(tuple({order_projection})) AS logical_rows "
                f"FROM {qualified} WHERE {filter_sql}"
            )
            logical_rows, logical_status, _, logical_sql = _profile_query(
                root,
                sequence + 3,
                f"{database}_{table}_logical_keys",
                logical_query,
            )
            logical_profile = logical_rows[0] if logical_rows else {}
        else:
            logical_sql = None
    else:
        logical_sql = None

    family = _profile_family(table, names)
    semantic_type = (
        "UNKNOWN"
        if family == "unknown"
        else evidence.choose_semantic(table, names)
    )
    compact_columns = _compact_columns(names, family)
    average_row_bytes = 0
    if samples:
        encoded = [
            len(
                json.dumps(
                    {column: row.get(column) for column in compact_columns},
                    ensure_ascii=False,
                    default=str,
                ).encode("utf-8")
            )
            for row in samples
        ]
        average_row_bytes = sum(encoded) // len(encoded)
    expected_rows = source_rows if family != "unknown" else 0
    if table == "clusters_adv_stats":
        expected_rows = _as_int(logical_profile.get("campaign_nmid_day_keys")) or source_rows
    elif family != "unknown" and logical_profile.get("logical_rows") is not None:
        expected_rows = _as_int(logical_profile.get("logical_rows"))
    write_frequency_summary = {
        "available": write_frequency_status.get("available", False),
        "hourly_buckets": len(write_frequency),
        "new_parts": sum(_as_int(row.get("new_parts")) for row in write_frequency),
        "rows": sum(_as_int(row.get("rows")) for row in write_frequency),
        "peak_rows_per_hour": max(
            (_as_int(row.get("rows")) for row in write_frequency),
            default=0,
        ),
    }
    parts_profile = {
        "active_rows": _as_int(parts.get("rows")),
        "bytes_on_disk": _as_int(parts.get("bytes_on_disk")),
        "data_compressed_bytes": _as_int(parts.get("data_compressed_bytes")),
        "data_uncompressed_bytes": _as_int(parts.get("data_uncompressed_bytes")),
        "partitions": sorted(parts.get("partitions", [])),
    }
    logical_key = (
        "analytical candidates: (adv_id, nmid, date) and "
        "(adv_id, nmid, wb_category, norm_query, date); "
        f"storage ORDER BY: {table_meta.get('sorting_key') or 'UNKNOWN'}"
        if table == "clusters_adv_stats"
        else (
            f"storage ORDER BY: {table_meta.get('sorting_key') or 'UNKNOWN'}; "
            "logical grain not proven"
        )
    )
    return {
        "source_system": "clickhouse",
        "database": database,
        "table": table,
        "family": family,
        "semantic_type": semantic_type,
        "schema": None,
        "schema_profile": {
            "columns": names,
            "column_definitions": [
                {
                    key: row.get(key)
                    for key in (
                        "name",
                        "type",
                        "default_kind",
                        "default_expression",
                        "comment",
                    )
                }
                for row in columns
            ],
            "engine": table_meta.get("engine"),
            "partition_key": table_meta.get("partition_key"),
            "sorting_key": table_meta.get("sorting_key"),
            "primary_key": table_meta.get("primary_key"),
            "ttl": table_meta.get("ttl_table"),
            "version_columns": [
                column
                for column in names
                if column.lower() in {"version", "ver", "sign"}
            ],
        },
        "source_row_count": source_rows,
        "profile_rows": source_rows,
        "min_date": summary.get("min_date") if source_rows else None,
        "max_date": summary.get("max_date") if source_rows else None,
        "rows_by_period": distribution,
        "rows_by_period_grain": (
            "day" if source_rows > 5_000_000 else "month"
        ) if temporal else None,
        "unique_identifiers": {
            column: _as_int(summary.get(f"unique_{column.lower()}"))
            for column in dict.fromkeys(id_columns)
        },
        "sample_rows": len(samples),
        "sample_file": str(sample_path.relative_to(root)),
        "schema_files": [
            "schema/databases.jsonl",
            "schema/tables.jsonl",
            "schema/columns.jsonl",
            "schema/parts.jsonl",
        ],
        "query_files": [
            str(summary_sql.relative_to(root)),
            str(sample_sql.relative_to(root)),
            *([str(distribution_sql.relative_to(root))] if distribution_sql else []),
            *([str(logical_sql.relative_to(root))] if logical_sql is not None else []),
            *(
                [str(write_frequency_sql.relative_to(root))]
                if write_frequency_sql is not None
                else []
            ),
        ],
        "filter": filter_sql,
        "mapping": mapping,
        "natural_key": logical_key,
        "logical_key_profile": logical_profile,
        "logical_key_query_status": logical_status,
        "write_frequency": write_frequency,
        "write_frequency_status": write_frequency_status,
        "write_frequency_summary": write_frequency_summary,
        "parts_profile": parts_profile,
        "provenance": (
            "ClickHouse system.tables/system.columns/system.parts + A1 mapping "
            "from existing safe PostgreSQL evidence; family/semantic classification "
            "is heuristic and UNKNOWN is retained where not proven."
        ),
        "target_export_grain": _expected_grain(family),
        "target_projection": compact_columns,
        "expected_compact_export_rows": expected_rows,
        "sample_compact_row_bytes": average_row_bytes,
        "expected_compact_export_bytes": expected_rows * average_row_bytes,
        "output_row_count": 0,
        "records_selected": 0,
        "records_written": 0,
        "output_status": "NOT_STARTED_PROFILE_ONLY",
        "transformation": (
            "Profiling only: no source rows transformed or exported; "
            "compact row estimate uses target grain and sample projection."
        ),
        "status": {
            "summary": summary_status,
            "distribution": distribution_status,
            "sample": sample_status,
        },
    }


def _profile_postgres(profile_root: Path, evidence_root: Path) -> list[dict[str, Any]]:
    """Построить компактный профиль уже выгруженных safe PostgreSQL CSV."""
    coverage_path = evidence_root / "postgres" / "a1_coverage.json"
    if not coverage_path.exists():
        return []
    source_items = json.loads(coverage_path.read_text(encoding="utf-8"))
    result: list[dict[str, Any]] = []
    for index, item in enumerate(source_items, start=1):
        output = Path(str(item.get("query_status", {}).get("output", "")))
        if not output.exists():
            continue
        columns = [str(column) for column in item.get("columns", [])]
        sample_path = profile_root / "postgres_samples" / f"{index:03d}_{output.stem}.jsonl"
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        samples: list[dict[str, Any]] = []
        import csv

        with output.open(encoding="utf-8", errors="replace", newline="") as handle:
            for row_number, row in enumerate(csv.DictReader(handle)):
                if row_number >= 50:
                    break
                samples.append(dict(row))
        sample_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in samples),
            encoding="utf-8",
        )
        query_file = item.get("query_file")
        if query_file:
            source_sql = evidence_root / str(query_file).replace("\\", "/")
            target_sql = profile_root / "sql" / f"pg_{index:03d}_{source_sql.name}"
            if source_sql.exists():
                target_sql.parent.mkdir(parents=True, exist_ok=True)
                target_sql.write_text(source_sql.read_text(encoding="utf-8"), encoding="utf-8")
                query_file = str(target_sql.relative_to(profile_root))
        expected_rows = (
            _as_int(item.get("rows"))
            if item.get("family") != "unknown"
            else 0
        )
        result.append(
            {
                **item,
                "source_system": "postgresql",
                "source_row_count": _as_int(item.get("rows")),
                "profile_rows": _as_int(item.get("rows")),
                "sample_rows": len(samples),
                "sample_file": str(sample_path.relative_to(profile_root)),
                "query_files": [query_file] if query_file else [],
                "expected_compact_export_rows": expected_rows,
                "expected_compact_export_bytes": int(
                    (
                        sum(
                            len(json.dumps(row, ensure_ascii=False).encode("utf-8"))
                            for row in samples
                        )
                        / max(len(samples), 1)
                    )
                    * expected_rows
                ),
                "output_row_count": 0,
                "records_selected": 0,
                "records_written": 0,
                "output_status": "NOT_STARTED_PROFILE_ONLY",
                "transformation": "Profile of already collected safe CSV; no new DB query.",
            }
        )
    return result


def _write_profile_report(
    root: Path,
    profiles: list[dict[str, Any]],
    databases: list[str],
    evidence_root: Path,
) -> None:
    """Сохранить profiling manifest и технический report."""
    evidence_dir = str(evidence_root)
    manifest = {
        "artifact": "clickhouse_a1_profile",
        "scope": {"client": "ООО «А1»", "shop_id": evidence.SHOP_ID},
        "mode": "profiling_first",
        "raw_dump_performed": False,
        "raw_dump_target": "clusters_adv_stats 74M physical rows / 7+ GB was not re-exported",
        "clickhouse_databases": databases,
        "source_evidence_dir": evidence_dir,
        "profiles": profiles,
        "redis": {
            "critical_path": False,
            "note": "Cache/legacy metadata is documented only; payload was not read.",
        },
        "wb_api_collect_run": False,
        "files": sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.is_file() and path.name != "manifest.json"
        ),
    }
    evidence.write_json(root / "manifest.json", manifest)
    lines = [
        "# Profiling report: ООО «А1»",
        "",
        f"- `shop_id`: `{evidence.SHOP_ID}`",
        "- Mode: profiling-first, READ_ONLY; no WB API and no full raw dump.",
        "- `clusters_adv_stats` 74M physical rows / 7+ GB was retained only as a ClickHouse source.",
        f"- ClickHouse databases: `{databases}`.",
        "- A1 scope uses a direct `shop_id` filter when present; otherwise it uses the "
        "union of mapped cabinet/campaign/nmID identifiers. Pairwise campaign↔nmID "
        "ownership is not assumed unless a source table provides it.",
        "",
        "## Expected compact analytical export sizes",
        "",
        "| source | table | family | source rows | expected rows | expected bytes | target grain |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for item in profiles:
        qualified = ".".join(
            str(value)
            for value in (item.get("database"), item.get("schema"), item.get("table"))
            if value
        )
        lines.append(
            f"| {item.get('source_system')} | `{qualified}` | {item.get('family', 'unknown')} | "
            f"{item.get('source_row_count', 0)} | "
            f"{item.get('expected_compact_export_rows', 0)} | "
            f"{item.get('expected_compact_export_bytes', 0)} | "
            f"{item.get('target_export_grain', 'unknown')} |"
        )
    lines.extend(
        [
            "",
            "## A1 dataset profiles",
            "",
        ]
    )
    for item in profiles:
        qualified = ".".join(
            str(value)
            for value in (item.get("database"), item.get("schema"), item.get("table"))
            if value
        )
        logical = item.get("logical_key_profile", {})
        lines.extend(
            [
                f"### `{qualified}`",
                "",
                f"- Family/semantic: `{item.get('family')}` / `{item.get('semantic_type')}`.",
                f"- Source rows: `{item.get('source_row_count', 0)}`; "
                f"range: `{item.get('min_date') or 'UNKNOWN'}` .. "
                f"`{item.get('max_date') or 'UNKNOWN'}`.",
                f"- Grain target: `{item.get('target_export_grain')}`; "
                f"natural key: `{item.get('natural_key')}`.",
                f"- Schema: `{item.get('schema_profile', item.get('schema'))}`; "
                f"schema files: `{item.get('schema_files', [])}`.",
                f"- Unique identifiers: `{item.get('unique_identifiers', {})}`.",
                f"- Rows by `{item.get('rows_by_period_grain') or 'none'}`: "
                f"{len(item.get('rows_by_period', []))} periods; distribution is in profile JSON.",
                f"- Sample: `{item.get('sample_rows', 0)}` rows at `{item.get('sample_file')}`.",
                f"- Logical-key profile: `{logical}`.",
                f"- SQL: `{item.get('query_files', [])}`.",
                f"- Provenance: {item.get('provenance')}.",
                f"- Transformation: {item.get('transformation')}.",
                "",
            ]
        )
    cluster_profiles = [item for item in profiles if item.get("table") == "clusters_adv_stats"]
    lines.extend(["## clusters_adv_stats assessment", ""])
    if cluster_profiles:
        cluster = cluster_profiles[0]
        logical = cluster.get("logical_key_profile", {})
        lines.extend(
            [
                "- Engine/ORDER BY, version columns and partition metadata are recorded in the profile manifest.",
                "- The table is a physical MergeTree source, not a ReplacingMergeTree; rows are not automatically deduplicated.",
                f"- Physical source rows: `{cluster.get('source_row_count', 0)}`.",
                f"- `campaign_nmid_day_keys`: `{logical.get('campaign_nmid_day_keys', 'UNKNOWN')}`.",
                f"- `campaign_nmid_query_day_keys`: `{logical.get('campaign_nmid_query_day_keys', 'UNKNOWN')}`.",
                f"- `timestamp_keys`: `{logical.get('timestamp_keys', 'UNKNOWN')}`.",
                f"- NewPart write-frequency probe (retention-limited `system.part_log`): "
                f"`{cluster.get('write_frequency_summary', {})}`; "
                f"availability: `{cluster.get('write_frequency_status', {})}`. "
                "This is not a complete historical write-rate series.",
                "- Classification: append-only timestamped metric samples; MergeTree has no "
                "ReplacingMergeTree/version semantics, so snapshot-versus-revision meaning is not "
                "encoded by the table engine.",
                f"- Expected compact analytical grain: `{cluster.get('target_export_grain')}`; "
                f"expected rows: `{cluster.get('expected_compact_export_rows', 0)}`.",
                "- For campaign × date × nmID history the required fields are "
                "`adv_id,nmid,date,views,clicks,ctr,cpm,add_to_cart,orders,cpc,spend`; "
                "`wb_category,norm_query,timestamp` remain available for query-level reconciliation.",
                "- Required compact fields are listed in `target_projection`; no transformation has been executed yet.",
            ]
        )
    else:
        lines.append("- `clusters_adv_stats` profile query did not produce a mapped A1 item.")
    lines.extend(
        [
            "",
            "## Export gate",
            "",
            "- Analytical export is intentionally not started. Next step requires Owner approval after reviewing this profiling report.",
            "- Redis is outside the critical path because only cache/legacy state was observed; no payload was read.",
            "- Semantic reconciliation with WB API remains pending; WB API was not called.",
        ]
    )
    evidence.write_text(root / "report.md", "\n".join(lines) + "\n")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"] = sorted(
        set(manifest.get("files", [])) | {"report.md"}
    )
    evidence.write_json(root / "manifest.json", manifest)


def run_profile(output_dir: Path, evidence_dir: Path) -> int:
    """Выполнить profiling-only сбор и остановиться до analytical export."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "schema").mkdir(parents=True, exist_ok=True)
    (output_dir / "parts").mkdir(parents=True, exist_ok=True)
    mapping_path = evidence_dir / "postgres" / "a1_mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.exists() else {}
    cabinet_ids = {int(value) for value in mapping.get("cabinet_ids", [])}
    campaign_ids = {int(value) for value in mapping.get("campaign_ids", [])}
    nmids = {int(value) for value in mapping.get("nmids", [])}

    schema_queries = (
        ("databases", "SELECT * FROM system.databases ORDER BY name"),
        (
            "tables",
            "SELECT * FROM system.tables WHERE database NOT IN "
            "('system', 'INFORMATION_SCHEMA', 'information_schema') "
            "ORDER BY database, name",
        ),
        (
            "columns",
            "SELECT * FROM system.columns WHERE database NOT IN "
            "('system', 'INFORMATION_SCHEMA', 'information_schema') "
            "ORDER BY database, table, position",
        ),
        (
            "parts",
            "SELECT database, table, partition, active, rows, bytes_on_disk, "
            "data_compressed_bytes, data_uncompressed_bytes "
            "FROM system.parts WHERE active AND database NOT IN "
            "('system', 'INFORMATION_SCHEMA', 'information_schema') "
            "ORDER BY database, table, partition",
        ),
    )
    inventory: dict[str, list[dict[str, Any]]] = {}
    for sequence, (name, query) in enumerate(schema_queries, start=1):
        rows, _, output, _ = _profile_query(
            output_dir,
            sequence,
            f"system_{name}",
            query,
        )
        inventory[name] = rows
        target = output.parent.parent / "schema" / f"{name}.jsonl"
        target.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
    databases = sorted(
        str(row.get("name"))
        for row in inventory["databases"]
        if row.get("name")
        and str(row.get("name")).lower() not in {"system", "information_schema"}
    )
    table_rows = inventory["tables"]
    column_rows = inventory["columns"]
    columns_by_table: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in column_rows:
        columns_by_table[(str(row.get("database")), str(row.get("table")))].append(row)
    parts_by_table: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "rows": 0,
            "bytes_on_disk": 0,
            "data_compressed_bytes": 0,
            "data_uncompressed_bytes": 0,
            "partitions": [],
        }
    )
    for row in inventory["parts"]:
        key = (str(row.get("database")), str(row.get("table")))
        target = parts_by_table[key]
        for metric in (
            "rows",
            "bytes_on_disk",
            "data_compressed_bytes",
            "data_uncompressed_bytes",
        ):
            target[metric] += _as_int(row.get(metric))
        if row.get("partition") is not None:
            target["partitions"].append(str(row["partition"]))
    table_meta = {
        (str(row.get("database")), str(row.get("name"))): row for row in table_rows
    }
    profiles: list[dict[str, Any]] = []
    sequence = 100
    for (database, table), columns in sorted(columns_by_table.items()):
        if database not in {"default", "default_db"}:
            continue
        names = [str(row.get("name", "")) for row in columns]
        haystack = f"{table} {' '.join(names)}".lower()
        if not any(
            term in haystack
            for _, terms in evidence.SEMANTIC_TERMS
            for term in terms
        ):
            continue
        meta = table_meta.get((database, table), {})
        if "view" in str(meta.get("engine", "")).lower():
            continue
        filter_sql, mapping_text = evidence.filter_for_clickhouse(
            columns,
            cabinet_ids,
            campaign_ids,
            nmids,
        )
        if filter_sql is None:
            continue
        profiles.append(
            _profile_clickhouse_table(
                output_dir,
                database,
                table,
                columns,
                meta,
                parts_by_table[(database, table)],
                filter_sql,
                mapping_text,
                sequence,
            )
        )
        sequence += 10
    profiles.extend(_profile_postgres(output_dir, evidence_dir))
    evidence.write_json(output_dir / "profiles.json", profiles)
    _write_profile_report(output_dir, profiles, databases, evidence_dir)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir.resolve()),
                "profile_items": len(profiles),
                "clickhouse_databases": databases,
                "raw_dump_performed": False,
                "analytical_export_started": False,
                "LOCAL_ARTIFACT_HANDOFF": "PROFILE_ONLY",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать параметры profiling-only запуска."""
    parser = argparse.ArgumentParser(
        description="Profiling-first read-only A1 ClickHouse evidence collector."
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp/clickhouse_a1_profile",
        help="profile output directory; no ZIP is created",
    )
    parser.add_argument(
        "--evidence-dir",
        default=".tmp/clickhouse_a1_evidence_run9",
        help="existing local evidence directory with A1 mappings",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить profiling report и не переходить к analytical export."""
    args = parse_args(argv)
    return run_profile(Path(args.output_dir).resolve(), Path(args.evidence_dir).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
