"""Компактная READ_ONLY analytical evidence-выгрузка для ООО «А1».

Источники ClickHouse выбираются по доказанным campaign IDs кабинета, а не по
небезопасному объединению ``adv_id OR nmid``. Для источников без campaign ID
(например, funnel и auto-shelf) используются только nmID, встречающиеся в
парах из безопасного PostgreSQL ``advsetting.csv``. Большие физические таблицы
не выгружаются: advertising daily читается из ``mv_clusters_daily_agg``.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

from scripts import ch_a1_evidence as evidence


def _sql_int_list(values: Iterable[int]) -> str:
    """Собрать непустой SQL-список целых идентификаторов."""
    normalized = sorted({int(value) for value in values})
    if not normalized:
        raise ValueError("A1 mapping produced an empty identifier list")
    return "(" + ", ".join(str(value) for value in normalized) + ")"


def _sha256(path: Path) -> str:
    """Посчитать SHA-256 потоково, не загружая dataset в память."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonl_stats(path: Path) -> tuple[int, str | None, str | None]:
    """Посчитать строки и min/max по известным date-like полям JSONL."""
    count = 0
    minimum: str | None = None
    maximum: str | None = None
    temporal_names = {
        "date",
        "event_date",
        "timestamp",
        "src_ts",
        "decision_time",
        "bucket_start",
        "inserted_at",
    }
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            count += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            values = [
                str(value)
                for key, value in row.items()
                if key.lower() in temporal_names and value not in (None, "")
            ]
            if values:
                row_min, row_max = min(values), max(values)
                minimum = row_min if minimum is None else min(minimum, row_min)
                maximum = row_max if maximum is None else max(maximum, row_max)
    return count, minimum, maximum


def _run_query(
    root: Path,
    name: str,
    query: str,
    *,
    sequence: int,
    timeout_seconds: int = 1800,
) -> tuple[Path, dict[str, Any]]:
    """Выполнить один SELECT и сохранить SQL/result в export directory."""
    stem = f"{sequence:03d}_{evidence.safe_filename(name)}"
    output = root / "query_results" / f"{stem}.jsonl"
    sql_path = root / "sql" / f"{stem}.sql"
    status = evidence.run_ch_query(
        query,
        output,
        sql_path,
        timeout_seconds=timeout_seconds,
    )
    if not status["success"]:
        raise RuntimeError(f"ClickHouse query failed: {name}: {status['stderr']}")
    return output, status


def _bid_decision_query(campaigns: str) -> str:
    """Построить bounded latest-version query для части campaign IDs."""
    return f"""
SELECT
    adv_id, nmid, norm_query, wb_category, pos_final, pos_final_bucket,
    views_curr, spend_curr, cpm_curr, pos_curr, views_prev, spend_prev,
    cpm_prev, pos_prev, final_bid, decision_source, stats_max_timestamp,
    decision_time, version
FROM default_db.bid_decision_log
WHERE adv_id IN {campaigns}
ORDER BY adv_id, nmid, norm_query, pos_final_bucket, version DESC
LIMIT 1 BY adv_id, nmid, norm_query, pos_final_bucket
""".strip()


def _export_bid_decisions_chunked(
    root: Path,
    campaign_ids: list[int],
    *,
    sequence: int,
) -> dict[str, Any]:
    """Выгрузить bid decisions чанками, чтобы не перегружать HTTP query."""
    output = root / "datasets" / "bot_bid_decision_history.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"")
    source_rows = 0
    sql_files: list[str] = []
    for part_number in range(0, len(campaign_ids), 25):
        part_ids = campaign_ids[part_number : part_number + 25]
        part = f"{part_number // 25 + 1:03d}"
        campaign_sql = _sql_int_list(part_ids)
        chunk_sequence = sequence + (part_number // 25) * 2
        count_path, _ = _run_query(
            root,
            f"bot_bid_decision_history_{part}_source_count",
            f"SELECT count() AS source_rows FROM default_db.bid_decision_log WHERE adv_id IN {campaign_sql}",
            sequence=chunk_sequence,
        )
        count_rows, _, _ = _jsonl_stats(count_path)
        if count_rows:
            source_rows += int(
                json.loads(count_path.read_text(encoding="utf-8").splitlines()[0])["source_rows"]
            )
        data_path, _ = _run_query(
            root,
            f"bot_bid_decision_history_{part}",
            _bid_decision_query(campaign_sql),
            sequence=chunk_sequence + 1,
        )
        with data_path.open("rb") as handle, output.open("ab") as combined:
            shutil.copyfileobj(handle, combined)
        sql_files.extend(
            [
                str(
                    (
                        root
                        / "sql"
                        / f"{chunk_sequence:03d}_bot_bid_decision_history_{part}_source_count.sql"
                    ).relative_to(root)
                ),
                str(
                    (
                        root
                        / "sql"
                        / f"{chunk_sequence + 1:03d}_bot_bid_decision_history_{part}.sql"
                    ).relative_to(root)
                ),
            ]
        )
    output_rows, minimum, maximum = _jsonl_stats(output)
    return {
        "dataset": "bot_bid_decision_history",
        "source": "default_db.bid_decision_log",
        "family": "campaign_state",
        "semantic_type": "APPLICATION_EVENT",
        "exact_grain": "adv_id × nmid × norm_query × pos_final_bucket logical event",
        "source_rows": source_rows,
        "output_rows": output_rows,
        "min_date": minimum,
        "max_date": maximum,
        "dimensions": ["adv_id", "nmid", "norm_query", "pos_final_bucket", "decision_time"],
        "metrics": ["pos_final", "views_curr", "spend_curr", "cpm_curr", "final_bid"],
        "mapping": "Primary ownership filter: adv_id IN A1 campaign IDs.",
        "transformation": "Chunked ORDER BY version DESC + LIMIT 1 BY ReplacingMergeTree key.",
        "dedup_version_rule": "ReplacingMergeTree(version); latest physical row per logical key selected deterministically.",
        "confidence": "HIGH",
        "sql_files": sql_files,
        "output_file": str(output.relative_to(root)),
        "sha256": _sha256(output),
        "status": "EXPORTED",
    }


def _export_clickhouse_dataset(
    root: Path,
    *,
    sequence: int,
    name: str,
    source: str,
    query: str,
    source_count_query: str,
    family: str,
    semantic_type: str,
    grain: str,
    dimensions: list[str],
    metrics: list[str],
    mapping: str,
    transformation: str,
    dedup_rule: str,
    confidence: str,
) -> dict[str, Any]:
    """Выгрузить один bounded compact dataset и записать его receipt."""
    count_path, _ = _run_query(
        root,
        f"{name}_source_count",
        source_count_query,
        sequence=sequence,
    )
    count_rows, _, _ = _jsonl_stats(count_path)
    data_path, _ = _run_query(root, name, query, sequence=sequence + 1)
    output_rows, minimum, maximum = _jsonl_stats(data_path)
    return {
        "dataset": name,
        "source": source,
        "family": family,
        "semantic_type": semantic_type,
        "exact_grain": grain,
        "source_rows": (
            int(json.loads(count_path.read_text(encoding="utf-8").splitlines()[0]).get("source_rows", 0))
            if count_rows
            else 0
        ),
        "output_rows": output_rows,
        "min_date": minimum,
        "max_date": maximum,
        "dimensions": dimensions,
        "metrics": metrics,
        "mapping": mapping,
        "transformation": transformation,
        "dedup_version_rule": dedup_rule,
        "confidence": confidence,
        "sql_files": [
            str((root / "sql" / f"{sequence:03d}_{evidence.safe_filename(name)}_source_count.sql").relative_to(root)),
            str((root / "sql" / f"{sequence + 1:03d}_{evidence.safe_filename(name)}.sql").relative_to(root)),
        ],
        "output_file": str(data_path.relative_to(root)),
        "sha256": _sha256(data_path),
        "status": "EXPORTED",
    }


def _safe_pg_rows(root: Path, evidence_root: Path, table_name: str) -> dict[str, Any] | None:
    """Скопировать уже собранный A1-safe CSV PostgreSQL без новых DB-запросов."""
    source = evidence_root / "postgres" / f"adv_updater_public_{table_name}.csv"
    if not source.exists():
        return None
    output = root / "postgres" / f"{table_name}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)
    with source.open(encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))
    query_files: list[str] = []
    coverage_path = evidence_root / "postgres" / "a1_coverage.json"
    if coverage_path.exists():
        for item in json.loads(coverage_path.read_text(encoding="utf-8")):
            if item.get("table") != table_name or not item.get("query_file"):
                continue
            source_sql = evidence_root / str(item["query_file"]).replace("\\", "/")
            if source_sql.exists():
                target_sql = root / "sql" / f"pg_{table_name}.sql"
                target_sql.write_text(
                    source_sql.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                query_files.append(str(target_sql.relative_to(root)))
            break
    columns = list(rows[0]) if rows else []
    temporal = [
        str(row[column])
        for row in rows
        for column in columns
        if column.lower() in {"date", "last_update", "created_at", "updated_at"}
        and row.get(column)
    ]
    family = evidence.choose_family(table_name, columns)
    return {
        "dataset": f"postgres_{table_name}",
        "source": f"adv_updater.public.{table_name}",
        "family": family,
        "semantic_type": evidence.choose_semantic(table_name, columns),
        "exact_grain": "source row (safe A1 PostgreSQL table)",
        "source_rows": len(rows),
        "output_rows": len(rows),
        "min_date": min(temporal) if temporal else None,
        "max_date": max(temporal) if temporal else None,
        "dimensions": columns,
        "metrics": [],
        "mapping": "Existing CSV was already selected by A1 shop/cabinet mapping.",
        "transformation": "Copy of existing safe A1-filtered CSV; no new DB query.",
        "dedup_version_rule": "No additional deduplication; preserve PostgreSQL source rows.",
        "confidence": "HIGH" if table_name == "advsetting" else "MEDIUM",
        "sql_files": query_files,
        "output_file": str(output.relative_to(root)),
        "sha256": _sha256(output),
        "status": "EXPORTED",
    }


def _load_a1_pair_mapping(evidence_root: Path) -> tuple[set[int], set[int], set[int]]:
    """Загрузить campaign IDs, cabinet IDs и подтверждённые nmID из advsetting."""
    mapping_path = evidence_root / "postgres" / "a1_mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    cabinet_ids = {int(value) for value in mapping.get("cabinet_ids", [])}
    source = evidence_root / "postgres" / "adv_updater_public_advsetting.csv"
    campaign_ids: set[int] = set()
    paired_nmids: set[int] = set()
    with source.open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row.get("wb_cabinet_id") or 0) not in cabinet_ids:
                continue
            if row.get("adv_id"):
                campaign_ids.add(int(row["adv_id"]))
            try:
                values = ast.literal_eval(row.get("nmids") or "[]")
            except (ValueError, SyntaxError):
                values = []
            paired_nmids.update(int(value) for value in values)
    if not campaign_ids:
        campaign_ids = {int(value) for value in mapping.get("campaign_ids", [])}
    if not paired_nmids:
        paired_nmids = {int(value) for value in mapping.get("nmids", [])}
    return cabinet_ids, campaign_ids, paired_nmids


def run_export(output_dir: Path, evidence_dir: Path) -> int:
    """Выполнить compact export, secret scan, ZIP и SHA-256 receipt."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    for directory in ("sql", "query_results", "metadata", "postgres", "raw"):
        (output_dir / directory).mkdir(parents=True, exist_ok=True)
    _, campaign_ids, paired_nmids = _load_a1_pair_mapping(evidence_dir)
    campaigns = _sql_int_list(campaign_ids)
    nmids = _sql_int_list(paired_nmids)
    shop_literal = _quote_string(evidence.SHOP_ID)
    datasets: list[dict[str, Any]] = []
    sequence = 10

    spend_check_path, _ = _run_query(
        output_dir,
        "mv_clusters_daily_agg_schema",
        "DESCRIBE TABLE default_db.mv_clusters_daily_agg",
        sequence=1,
    )
    (output_dir / "metadata" / "mv_clusters_daily_agg_schema.jsonl").write_text(
        spend_check_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    evidence.write_json(
        output_dir / "metadata" / "query_level_spend_check.json",
        {
            "source": "default_db.mv_clusters_daily_agg",
            "spend_state_present": False,
            "status": "UNAVAILABLE_NOT_DERIVED",
            "note": "MV exposes argMax states for views/clicks/carts/orders/cpm/cpc/ctr/avr_pos only. Query-level spend was not reconstructed from CPC/CPM.",
        },
    )

    mv_query = f"""
SELECT
    adv_id, nmid, norm_query, date,
    argMaxMerge(views_state) AS views,
    argMaxMerge(clicks_state) AS clicks,
    argMaxMerge(carts_state) AS carts,
    argMaxMerge(orders_state) AS orders,
    argMaxMerge(cpm_state) AS cpm,
    argMaxMerge(cpc_state) AS cpc,
    argMaxMerge(ctr_state) AS ctr,
    argMaxMerge(avr_pos_state) AS avr_pos
FROM default_db.mv_clusters_daily_agg
WHERE adv_id IN {campaigns}
GROUP BY adv_id, nmid, norm_query, date
ORDER BY date, adv_id, nmid, norm_query
""".strip()
    datasets.append(_export_clickhouse_dataset(
        output_dir, sequence=sequence, name="advertising_daily_mv",
        source="default_db.mv_clusters_daily_agg",
        query=mv_query,
        source_count_query=f"SELECT count() AS source_rows FROM default_db.mv_clusters_daily_agg WHERE adv_id IN {campaigns}",
        family="advertising", semantic_type="DERIVED_METRIC",
        grain="date × adv_id × nmid × norm_query",
        dimensions=["date", "adv_id", "nmid", "norm_query"],
        metrics=["views", "clicks", "carts", "orders", "cpm", "cpc", "ctr", "avr_pos"],
        mapping="Primary ownership filter: adv_id IN A1 campaign IDs; nmID is retained as a dimension.",
        transformation="argMaxMerge over installed AggregateFunction states; no clusters_adv_stats scan.",
        dedup_rule="AggregatingMergeTree state merge; no FINAL; one grouped logical row.",
        confidence="HIGH",
    ))
    sequence += 2

    full_adv_query = f"""
SELECT
    adv_id, date,
    argMax(views, version) AS views,
    argMax(clicks, version) AS clicks,
    argMax(spend, version) AS spend,
    argMax(added_to_cart, version) AS added_to_cart,
    argMax(orders, version) AS orders,
    argMax(sum_price_orders, version) AS sum_price_orders
FROM default_db.full_adv_wb_stat
WHERE adv_id IN {campaigns}
GROUP BY adv_id, date
ORDER BY date, adv_id
""".strip()
    datasets.append(_export_clickhouse_dataset(
        output_dir, sequence=sequence, name="ad_campaign_daily",
        source="default_db.full_adv_wb_stat",
        query=full_adv_query,
        source_count_query=f"SELECT count() AS source_rows FROM default_db.full_adv_wb_stat WHERE adv_id IN {campaigns}",
        family="advertising", semantic_type="SNAPSHOT",
        grain="date × adv_id",
        dimensions=["date", "adv_id"],
        metrics=["views", "clicks", "spend", "added_to_cart", "orders", "sum_price_orders"],
        mapping="Primary ownership filter: adv_id IN A1 campaign IDs; nmID is deliberately not claimed.",
        transformation="Projection with argMax(metric, version), grouped by adv_id/date.",
        dedup_rule="ReplacingMergeTree logical resolution by version; no FINAL.",
        confidence="HIGH",
    ))
    sequence += 2

    funnel_query = f"""
SELECT
    date, nmid,
    argMax(open_card, version) AS open_card,
    argMax(add_to_cart, version) AS add_to_cart,
    argMax(orders, version) AS orders,
    argMax(orders_sum, version) AS orders_sum,
    argMax(buy_outs, version) AS buy_outs,
    argMax(buyouts_sum_rub, version) AS buyouts_sum_rub
FROM default_db.wb_common_stat
WHERE nmid IN {nmids}
GROUP BY date, nmid
ORDER BY date, nmid
""".strip()
    datasets.append(_export_clickhouse_dataset(
        output_dir, sequence=sequence, name="funnel_daily",
        source="default_db.wb_common_stat",
        query=funnel_query,
        source_count_query=f"SELECT count() AS source_rows FROM default_db.wb_common_stat WHERE nmid IN {nmids}",
        family="funnel", semantic_type="RAW_SOURCE",
        grain="date × nmid",
        dimensions=["date", "nmid"],
        metrics=["open_card", "add_to_cart", "orders", "orders_sum", "buy_outs", "buyouts_sum_rub"],
        mapping="No campaign column exists; nmIDs are restricted to A1 advsetting campaign↔nmID pairs.",
        transformation="argMax(metric, version) grouped by nmid/date; wb_common_stat_delta excluded.",
        dedup_rule="ReplacingMergeTree(version), key (nmid,date); no FINAL.",
        confidence="MEDIUM",
    ))
    sequence += 2

    fact_fields = (
        "event_date, event_id, bucket_start, shop_id, complex_adv_id, "
        "views_adv_sum, clicks_adv_sum, carts_adv_sum, orders_adv_sum, "
        "spend_adv_sum_rub, orders_sum_adv_rub, open_card_sum, carts_card_sum, "
        "orders_card_sum, orders_sum_card_rub, buy_outs_sum, src_ts, version, inserted_at"
    )
    for table, name in (
        ("fact_stat_states", "intraday_fact_state"),
        ("fact_stat_states_prev", "intraday_fact_state_prev"),
    ):
        query = (
            f"SELECT {fact_fields if table == 'fact_stat_states' else fact_fields.replace('event_date, event_id, ', '')} "
            f"FROM default_db.{table} WHERE shop_id = {shop_literal} ORDER BY src_ts, bucket_start"
        )
        datasets.append(_export_clickhouse_dataset(
            output_dir, sequence=sequence, name=name,
            source=f"default_db.{table}",
            query=query,
            source_count_query=f"SELECT count() AS source_rows FROM default_db.{table} WHERE shop_id = {shop_literal}",
            family="advertising", semantic_type="RAW_SOURCE",
            grain="source bucket/event grain",
            dimensions=["shop_id", "complex_adv_id", "bucket_start", "src_ts", "version"],
            metrics=["views_adv_sum", "clicks_adv_sum", "carts_adv_sum", "orders_adv_sum",
                     "spend_adv_sum_rub", "orders_sum_adv_rub", "open_card_sum",
                     "carts_card_sum", "orders_card_sum", "orders_sum_card_rub", "buy_outs_sum"],
            mapping="Direct shop_id=A1; repository proves complex_adv_id is ComplexAdv/AdvSetting ID, but WB adv_id equivalence is UNKNOWN_MAPPING.",
            transformation="A1 shop filter only; preserve original bucket rows.",
            dedup_rule="No cross-row deduplication; preserve version/event history.",
            confidence="MEDIUM",
        ))
        sequence += 2

    datasets.append(
        _export_bid_decisions_chunked(
            output_dir,
            sorted(campaign_ids),
            sequence=sequence,
        )
    )
    sequence += ((len(campaign_ids) + 24) // 25) * 2

    interval_query = f"""
WITH ordered AS (
    SELECT
        event_date, event_id, src_ts, bucket_start, version, nmid, mode,
        bid_minor, currency, price_minor, price_currency,
        delta_impressions, delta_clicks, delta_carts, delta_orders, delta_spend,
        row_number() OVER w AS seq,
        lagInFrame(mode) OVER w AS prev_mode,
        lagInFrame(bid_minor) OVER w AS prev_bid_minor,
        lagInFrame(price_minor) OVER w AS prev_price_minor
    FROM default_db.auto_shelf_bid_intervals
    WHERE nmid IN {nmids}
    WINDOW w AS (
        PARTITION BY nmid ORDER BY src_ts, event_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )
)
SELECT
    event_date, event_id, src_ts, bucket_start, version, nmid, mode,
    bid_minor, currency, price_minor, price_currency,
    delta_impressions, delta_clicks, delta_carts, delta_orders, delta_spend
FROM ordered
WHERE seq = 1 OR mode != prev_mode OR bid_minor != prev_bid_minor OR price_minor != prev_price_minor
ORDER BY src_ts, event_id
""".strip()
    datasets.append(_export_clickhouse_dataset(
        output_dir, sequence=sequence, name="bot_auto_shelf_change_points",
        source="default_db.auto_shelf_bid_intervals",
        query=interval_query,
        source_count_query=f"SELECT count() AS source_rows FROM default_db.auto_shelf_bid_intervals WHERE nmid IN {nmids}",
        family="campaign_state", semantic_type="APPLICATION_EVENT",
        grain="nmid × change event",
        dimensions=["event_date", "event_id", "src_ts", "bucket_start", "nmid", "mode", "bid_minor", "price_minor"],
        metrics=["delta_impressions", "delta_clicks", "delta_carts", "delta_orders", "delta_spend"],
        mapping="No campaign column; nmIDs restricted to A1 advsetting campaign↔nmID pairs.",
        transformation="Deterministic LAG change-point extraction on mode/bid/price; preserves original timestamps and fields.",
        dedup_rule="MergeTree append-only event rows; no deduplication.",
        confidence="MEDIUM",
    ))
    sequence += 2

    keyword_new_query = f"""
SELECT
    adv_id, text, date,
    argMaxMerge(clicks_state) AS clicks,
    argMaxMerge(views_state) AS views,
    argMaxMerge(spend_state) AS spend
FROM default_db.advkeyword_new
WHERE adv_id IN {campaigns}
GROUP BY adv_id, text, date
ORDER BY date, adv_id, text
""".strip()
    datasets.append(_export_clickhouse_dataset(
        output_dir, sequence=sequence, name="historical_advkeyword_daily",
        source="default_db.advkeyword_new",
        query=keyword_new_query,
        source_count_query=f"SELECT count() AS source_rows FROM default_db.advkeyword_new WHERE adv_id IN {campaigns}",
        family="normquery_search", semantic_type="NORMALIZED_SOURCE",
        grain="date × adv_id × text",
        dimensions=["date", "adv_id", "text"],
        metrics=["views", "clicks", "spend"],
        mapping="Primary ownership filter: adv_id IN A1 campaign IDs.",
        transformation="argMaxMerge over AggregateFunction states grouped by adv_id/text/date.",
        dedup_rule="AggregatingMergeTree state merge; one logical row per group.",
        confidence="HIGH",
    ))
    sequence += 2

    for table, name, metric_fields, key_fields in (
        (
            "keyword_position_from_api",
            "historical_keyword_position",
            "argMax(avr_position, version) AS avr_position, argMax(total_views, version) AS total_views, argMax(orders, version) AS orders",
            "nmid, text, date",
        ),
        (
            "wbitemposition",
            "historical_item_position",
            "argMax(promo_position, version) AS promo_position, argMax(base_position, version) AS base_position, argMax(cpm, version) AS cpm, argMax(adv_type, version) AS adv_type",
            "nmid, text, timestamp",
        ),
    ):
        query = (
            f"SELECT {key_fields}, {metric_fields} FROM default_db.{table} "
            f"WHERE nmid IN {nmids} GROUP BY {key_fields} ORDER BY {key_fields}"
        )
        datasets.append(_export_clickhouse_dataset(
            output_dir, sequence=sequence, name=name,
            source=f"default_db.{table}",
            query=query,
            source_count_query=f"SELECT count() AS source_rows FROM default_db.{table} WHERE nmid IN {nmids}",
            family="normquery_search", semantic_type="NORMALIZED_SOURCE",
            grain="nmid × text × date" if table == "keyword_position_from_api" else "nmid × text × timestamp",
            dimensions=key_fields.split(", "),
            metrics=["avr_position", "total_views", "orders"] if table == "keyword_position_from_api" else ["promo_position", "base_position", "cpm", "adv_type"],
            mapping="No campaign column; nmIDs restricted to A1 advsetting campaign↔nmID pairs.",
            transformation="argMax(metric, version) grouped by source logical key.",
            dedup_rule="ReplacingMergeTree(version); latest version per logical key.",
            confidence="MEDIUM",
        ))
        sequence += 2

    for table_name in (
        "advsetting",
        "advkeyword",
        "keywordsetting",
        "auto_shelf_bid_control_settings",
        "auto_shelf_bid_control_state",
        "wbautobudgettopup",
        "advpayment",
    ):
        item = _safe_pg_rows(output_dir, evidence_dir, table_name)
        if item:
            datasets.append(item)

    manifest = {
        "artifact": "clickhouse_a1_compact_evidence",
        "scope": {"client": "ООО «А1»", "shop_id": evidence.SHOP_ID},
        "read_only": True,
        "wb_api_collect_run": False,
        "full_raw_dump": False,
        "excluded": [
            "default_db.clusters_adv_stats",
            "default_db..inner_id.*",
            "default_db.wb_common_stat_delta",
            "default_db.plan_fact_stats",
            "Redis payloads",
        ],
        "datasets": datasets,
        "mapping": {
            "campaign_filter": "adv_id IN confirmed A1 campaign IDs from advsetting/wbcabinet",
            "nmid_filter": "only A1 campaign↔nmID pairs from advsetting for tables without campaign field",
            "fact_stat_states": "shop_id direct; complex_adv_id -> WB adv_id remains UNKNOWN_MAPPING",
        },
        "query_level_spend": {
            "source": "default_db.mv_clusters_daily_agg",
            "status": "UNAVAILABLE_NOT_DERIVED",
        },
        "redis": {"critical_path": False, "payload_exported": False},
        "status": "EXPORT_COMPLETE_PENDING_SECRET_SCAN",
    }
    evidence.write_json(output_dir / "manifest.json", manifest)
    findings = evidence.secret_scan(output_dir)
    evidence.write_json(
        output_dir / "secret_scan.json",
        {"status": "PASS" if not findings else "FAIL", "findings": findings},
    )
    if findings:
        raise SystemExit("Secret scan failed; ZIP was not created.")
    manifest["status"] = "EXPORT_COMPLETE"
    manifest["secret_scan"] = "PASS"
    manifest["files"] = sorted(
        str(path.relative_to(output_dir))
        for path in output_dir.rglob("*")
        if path.is_file() and path.name not in {"manifest.json"}
    )
    evidence.write_json(output_dir / "manifest.json", manifest)
    archive, digest = evidence.archive_directory(output_dir)
    print(json.dumps({
        "output_dir": str(output_dir.resolve()),
        "archive_path": str(archive.resolve()),
        "sha256": digest,
        "datasets": len(datasets),
        "full_raw_dump": False,
        "LOCAL_ARTIFACT_HANDOFF": "PASS",
    }, ensure_ascii=False, indent=2))
    return 0


def _quote_string(value: str) -> str:
    """Экранировать строковый литерал для ClickHouse."""
    return "'" + value.replace("'", "''") + "'"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать параметры compact export."""
    parser = argparse.ArgumentParser(description="Compact READ_ONLY A1 evidence export.")
    parser.add_argument("--output-dir", default=".tmp/clickhouse_a1_compact_evidence")
    parser.add_argument("--evidence-dir", default=".tmp/clickhouse_a1_evidence_run9")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить compact export и создать ZIP/SHA-256 receipt."""
    args = parse_args(argv)
    return run_export(Path(args.output_dir).resolve(), Path(args.evidence_dir).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
