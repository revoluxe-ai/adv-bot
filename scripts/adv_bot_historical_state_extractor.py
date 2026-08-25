"""Reusable STRICT READ_ONLY extractor INTERNAL adv-bot historical state.

Собирает forensic-пакет для сопоставления control input → ad delivery без
повторного сбора ER-020 external WB/store outcome. Только SELECT/read:
plan_fact_stats, clusters_adv_stats, bid_decision_log, PG CURRENT_SNAPSHOT,
prod revision timeline (committed deployment-event ledger → effective intervals).
ADV_BOT_INTERNAL_HISTORY_<case>_<period>.zip + SHA256 sidecar.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv
import jwt

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence

EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
REVISION_LEDGER_PATH = EVIDENCE_DIR / "prod_revision_timeline.jsonl"
SUPPLIER_CLAIM_KEYS = ("uid", "oid", "supplierId", "supplier_id")


class ShopResolutionError(RuntimeError):
    """Fail-closed shop resolution (0 or >1 matches)."""


@dataclass(frozen=True)
class ShopResolution:
    """Результат READ_ONLY резолва shop_id."""

    requested_supplier_id: str | None
    requested_shop_id: str | None
    resolved_shop_id: str
    shop_resolution_source: str
    shop_resolution_status: str
    diagnostic: str | None = None

    def manifest_fields(self) -> dict[str, Any]:
        """Поля provenance для manifest.json."""
        return {
            "requested_supplier_id": self.requested_supplier_id,
            "requested_shop_id": self.requested_shop_id,
            "resolved_shop_id": self.resolved_shop_id,
            "shop_resolution_source": self.shop_resolution_source,
            "shop_resolution_status": self.shop_resolution_status,
        }

WRITE_SQL_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|ALTER|CREATE|DROP|TRUNCATE|OPTIMIZE|SYSTEM)\b",
    re.IGNORECASE,
)

SETTING_FIELDS = [
    "id",
    "adv_id",
    "_search_adv_id",
    "type",
    "name",
    "nmids",
    "active_status",
    "bot_active",
    "last_update",
    "plan_for_sales_for_day",
    "target_price_for_order",
    "max_price_for_order",
    "substitute_fact_cpo_for_max",
    "orders_source_for_auto_mode",
    "strategy",
    "auto_update_strategy",
    "aggressiveness",
    "cpm",
    "max_cpm",
    "max_cpc",
    "bidder_active",
    "bidder_for_auto",
    "bidder_mode",
    "wb_bid_type",
    "bidder_step",
    "exponent_predict_ctr",
    "auto_update_exponent",
    "wb_placement_search",
    "wb_placement_recommendations",
    "rec_system_mode",
    "auto_shelf_bid_control_enabled",
    "auto_shelf_bid_control_strategy",
    "auto_budget_watchdog_enabled",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "use_common_budget",
    "common_budget_daily_limit",
    "auto_common_budget",
    "max_balance_adding_for_day",
    "black_phrases",
    "relevant_phrases",
    "pass_days",
    "boost",
    "auto_update_white_list",
    "white_list_mode",
    "auto_add_only_relevant_phrase",
    "target_position_mode",
    "min_target_position",
    "hard_min_ctr",
    "hide_small_query_keywords",
    "hide_zero_views_keywords",
    "automatic_version",
    "wb_cabinet_id",
]

PLAN_FACT_COLUMNS = [
    "timestamp",
    "adv_id",
    "shop_id",
    "date",
    "plan_orders",
    "plan_target_pay_for_order",
    "plan_max_pay_for_order",
    "fact_predict_orders",
    "fact_original_orders",
    "fact_pay_for_order",
    "fact_method",
    "version",
]

KEYWORD_INTRADAY_COLUMNS = [
    "adv_id",
    "nmid",
    "norm_query",
    "date",
    "timestamp",
    "views",
    "clicks",
    "carts",
    "orders",
    "spend",
    "cpm",
    "position",
    "ctr",
    "cpc",
    "wb_category",
]

KEYWORD_DAILY_COLUMNS = [
    "adv_id",
    "nmid",
    "norm_query",
    "date",
    "views",
    "clicks",
    "carts",
    "orders",
    "spend",
    "cpm",
    "position",
]

BID_DECISION_COLUMNS = [
    "adv_id",
    "nmid",
    "norm_query",
    "wb_category",
    "pos_final",
    "pos_final_bucket",
    "views_curr",
    "spend_curr",
    "cpm_curr",
    "pos_curr",
    "views_prev",
    "spend_prev",
    "cpm_prev",
    "pos_prev",
    "final_bid",
    "decision_source",
    "stats_max_timestamp",
    "decision_time",
    "version",
]


def _pg_database() -> str:
    """Имя PostgreSQL database из env кластера."""
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap_pg_credentials_from_env() -> bool:
    """Подставить PG credentials из env, если Secret недоступен локально."""
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    if not user or not password:
        return False
    evidence._PG_CREDENTIALS = user, password
    return True


def bootstrap_cluster_infra() -> None:
    """Переключить PG/CH endpoints на in-cluster env из Job secrets."""
    _bootstrap_pg_credentials_from_env()
    pg_host = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get(
        "POSTGRES_REPLICA_HOST"
    )
    pg_port = os.environ.get("POSTGRES_PORT")
    if pg_host:
        evidence.PG_EXTERNAL_HOST = pg_host
    if pg_port:
        evidence.PG_EXTERNAL_PORT = int(pg_port)
    ch_host = os.environ.get("CLICK_HOUSE_HOST")
    ch_port = os.environ.get("CLICKHOUSE_PORT", "8123")
    if ch_host:
        evidence.CH_HTTP_URL = f"http://{ch_host}:{ch_port}/"


def esc_sql_str(value: str) -> str:
    """Экранировать строковый литерал для SQL."""
    return value.replace("\\", "\\\\").replace("'", "''")


def int_csv(values: set[int]) -> str:
    """Сформировать безопасный список целых для SQL IN."""
    if not values:
        return ""
    return ", ".join(str(int(v)) for v in sorted(values))


def assert_read_only_query(query: str) -> None:
    """Fail-closed guard: запрет mutating SQL."""
    if WRITE_SQL_FORBIDDEN.search(query):
        raise RuntimeError(f"Mutating SQL forbidden: {query[:120]}...")


def period_bounds(
    from_day: date, to_day: date, timezone: str
) -> tuple[str, str, str, str]:
    """Вернуть date strings и DateTime bounds в указанной TZ."""
    tz = ZoneInfo(timezone)
    start_dt = datetime.combine(from_day, time.min, tzinfo=tz)
    end_dt = datetime.combine(to_day, time(23, 59, 59), tzinfo=tz)
    return (
        from_day.isoformat(),
        to_day.isoformat(),
        start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        end_dt.strftime("%Y-%m-%d %H:%M:%S"),
    )


def period_slug(from_day: date, to_day: date) -> str:
    """Короткий slug периода для имени ZIP."""
    return f"{from_day.isoformat()}_{to_day.isoformat()}"


def primary_zip_name(case_slug: str, from_day: date, to_day: date) -> str:
    """Имя primary ZIP без директории."""
    safe_case = re.sub(r"[^A-Za-z0-9_.-]+", "_", case_slug.strip()) or "case"
    return f"ADV_BOT_INTERNAL_HISTORY_{safe_case}_{period_slug(from_day, to_day)}.zip"


def serialize(value: Any) -> str:
    """CSV-safe сериализация значения."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    """Записать CSV с фиксированными колонками."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: serialize(row.get(col)) for col in columns})


def pg_query(
    database: str, query: str, out: Path, sql_dir: Path, name: str
) -> dict[str, Any]:
    """READ_ONLY PostgreSQL SELECT с сохранением SQL."""
    assert_read_only_query(query)
    return evidence.run_pg_query(
        database, query, out, sql_dir / f"pg_{name}.sql", csv_output=True
    )


def ch_query(query: str, out: Path, sql_dir: Path, name: str) -> dict[str, Any]:
    """READ_ONLY ClickHouse SELECT с сохранением SQL."""
    assert_read_only_query(query)
    return evidence.run_ch_query(query, out, sql_dir / f"ch_{name}.sql")


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    """Прочитать CSV в список dict."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _pg_query_ephemeral(
    database: str,
    query: str,
    sql_dir: Path,
    name: str,
) -> list[dict[str, Any]]:
    """READ_ONLY PG SELECT во временный CSV; файл удаляется сразу после чтения."""
    staging = sql_dir.parent / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    path = staging / f"{name}_ephemeral.csv"
    st = pg_query(database, query, path, sql_dir, name)
    if not st["success"]:
        path.unlink(missing_ok=True)
        raise RuntimeError(f"PG query {name} failed: {st['stderr']}")
    rows = read_csv_rows(path)
    path.unlink(missing_ok=True)
    return rows


def supplier_claims_from_api_key(api_key: str) -> set[str]:
    """Извлечь supplier-related claims из JWT без записи токена на диск."""
    try:
        payload = jwt.decode(api_key, options={"verify_signature": False})
    except Exception:
        return set()
    if not isinstance(payload, dict):
        return set()
    claims: set[str] = set()
    for key in SUPPLIER_CLAIM_KEYS:
        value = payload.get(key)
        if value is not None:
            claims.add(str(value))
    return claims


def resolve_shop_from_supplier_id(
    supplier_id: str,
    sql_dir: Path,
) -> ShopResolution:
    """READ_ONLY резолв shop_id по WB supplier_id через PG internal mapping."""
    supplier_norm = supplier_id.strip()
    if not supplier_norm:
        raise ShopResolutionError("supplier_id is empty")

    matches: dict[str, set[str]] = {}

    if supplier_norm.isdigit():
        cabinet_rows = _pg_query_ephemeral(
            _pg_database(),
            (
                "SELECT shop_id FROM public.wbcabinet "
                f"WHERE id = {int(supplier_norm)}"
            ),
            sql_dir,
            "supplier_wbcabinet_id",
        )
        for row in cabinet_rows:
            sid = str(row.get("shop_id") or "").strip()
            if sid:
                matches.setdefault(sid, set()).add("wbcabinet.id")

    token_rows = _pg_query_ephemeral(
        _pg_database(),
        (
            "SELECT t.shop_id, t.api_key "
            "FROM public.wbtoken t "
            "INNER JOIN public.wbcabinet c ON c.shop_id = t.shop_id "
            "WHERE t.shop_id IS NOT NULL AND COALESCE(t.active, true) = true"
        ),
        sql_dir,
        "supplier_wbtoken_claims",
    )
    for row in token_rows:
        api_key = str(row.get("api_key") or "")
        shop_id = str(row.get("shop_id") or "").strip()
        if not api_key or not shop_id:
            continue
        if supplier_norm in supplier_claims_from_api_key(api_key):
            matches.setdefault(shop_id, set()).add("wbtoken.jwt_claim")

    if not matches:
        raise ShopResolutionError(
            f"No shop_id for supplier_id={supplier_norm} "
            "(checked wbcabinet.id and wbtoken JWT claims)"
        )
    if len(matches) > 1:
        raise ShopResolutionError(
            "Ambiguous supplier_id mapping: "
            + ", ".join(sorted(matches.keys()))
        )
    resolved = next(iter(matches))
    sources = sorted(matches[resolved])
    return ShopResolution(
        requested_supplier_id=supplier_norm,
        requested_shop_id=None,
        resolved_shop_id=resolved,
        shop_resolution_source="+".join(sources),
        shop_resolution_status="RESOLVED",
    )


def resolve_shop_identity(
    *,
    supplier_id: str | None,
    shop_id: str | None,
    sql_dir: Path,
) -> ShopResolution:
    """Резолвить canonical shop_id из --shop-id и/или --supplier-id."""
    supplier_norm = supplier_id.strip() if supplier_id else None
    shop_norm = shop_id.strip() if shop_id else None

    if shop_norm and supplier_norm:
        from_supplier = resolve_shop_from_supplier_id(supplier_norm, sql_dir)
        if from_supplier.resolved_shop_id != shop_norm:
            raise ShopResolutionError(
                "supplier_id and shop_id disagree: "
                f"supplier->{from_supplier.resolved_shop_id} "
                f"shop_id->{shop_norm}"
            )
        return ShopResolution(
            requested_supplier_id=supplier_norm,
            requested_shop_id=shop_norm,
            resolved_shop_id=shop_norm,
            shop_resolution_source=(
                f"explicit_shop_id+{from_supplier.shop_resolution_source}"
            ),
            shop_resolution_status="RESOLVED",
        )

    if shop_norm:
        verify_rows = _pg_query_ephemeral(
            _pg_database(),
            (
                "SELECT shop_id FROM public.wbcabinet "
                f"WHERE shop_id = '{esc_sql_str(shop_norm)}'"
            ),
            sql_dir,
            "explicit_shop_verify",
        )
        if not verify_rows:
            raise ShopResolutionError(f"No wbcabinet row for shop_id={shop_norm}")
        return ShopResolution(
            requested_supplier_id=None,
            requested_shop_id=shop_norm,
            resolved_shop_id=shop_norm,
            shop_resolution_source="explicit_shop_id",
            shop_resolution_status="RESOLVED",
        )

    if supplier_norm:
        return resolve_shop_from_supplier_id(supplier_norm, sql_dir)

    raise ShopResolutionError("Either --shop-id or --supplier-id is required")


def _parse_iso_datetime(value: str, timezone: str) -> datetime | None:
    """Разобрать ISO timestamp с fallback в указанную TZ."""
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo(timezone))
    return parsed


DEPLOYMENT_LEDGER_FIELDS = (
    "deployed_at",
    "commit_sha",
    "image_ref",
    "image_digest",
    "workflow_run_id",
    "evidence_source",
    "evidence_ref",
    "evidence_kind",
    "confidence",
    "notes",
)

REVISION_INTERVAL_COLUMNS = (
    "effective_from",
    "effective_to",
    "commit_sha",
    "image_ref",
    "image_digest",
    "deployment_timestamp",
    "evidence_source",
    "evidence_kind",
    "confidence",
    "notes",
)


def _format_interval_timestamp(value: datetime, timezone: str) -> str:
    """Сериализовать границу интервала в запрошенной таймзоне."""
    return value.astimezone(ZoneInfo(timezone)).isoformat()


def load_deployment_events(ledger_path: Path | None = None) -> list[dict[str, Any]]:
    """READ_ONLY committed deployment-event ledger (cluster-safe; no git)."""
    path = ledger_path or REVISION_LEDGER_PATH
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        deployed_at = str(item.get("deployed_at") or "").strip()
        commit_sha = str(item.get("commit_sha") or "").strip()
        if not deployed_at or not commit_sha:
            continue
        events.append(
            {
                "deployed_at": deployed_at,
                "commit_sha": commit_sha,
                "image_ref": str(item.get("image_ref") or ""),
                "image_digest": str(item.get("image_digest") or ""),
                "workflow_run_id": item.get("workflow_run_id"),
                "evidence_source": str(item.get("evidence_source") or ""),
                "evidence_ref": str(item.get("evidence_ref") or ""),
                "evidence_kind": str(
                    item.get("evidence_kind") or "DIRECT_DEPLOYMENT_RECEIPT"
                ),
                "confidence": str(item.get("confidence") or ""),
                "notes": str(item.get("notes") or ""),
            }
        )
    return events


def _deployment_event_dt(deployed_at: str) -> datetime | None:
    """Распарсить deployed_at; ledger хранит UTC/offset ISO."""
    parsed = _parse_iso_datetime(deployed_at, "UTC")
    if parsed is not None:
        return parsed
    return _parse_iso_datetime(deployed_at, "Europe/Moscow")


def derive_effective_intervals(
    events: list[dict[str, Any]],
    from_day: date,
    to_day: date,
    timezone: str,
) -> list[dict[str, Any]]:
    """Построить effective intervals для периода из deployment events."""
    tz = ZoneInfo(timezone)
    period_start = datetime.combine(from_day, time.min, tzinfo=tz)
    period_end = datetime.combine(to_day, time(23, 59, 59), tzinfo=tz)

    parsed_events: list[tuple[datetime, dict[str, Any]]] = []
    for event in events:
        deployed_dt = _deployment_event_dt(event["deployed_at"])
        if deployed_dt is None:
            continue
        parsed_events.append((deployed_dt, event))
    if not parsed_events:
        return []

    parsed_events.sort(key=lambda item: item[0])
    before_start = [item for item in parsed_events if item[0] <= period_start]
    in_period = [
        item for item in parsed_events if period_start < item[0] <= period_end
    ]
    after_period = [item for item in parsed_events if item[0] > period_end]

    if not before_start and not in_period:
        return []

    intervals: list[dict[str, Any]] = []

    def _interval_row(
        *,
        effective_from: datetime,
        effective_to: datetime,
        event: dict[str, Any],
        evidence_kind: str,
    ) -> dict[str, Any]:
        return {
            "effective_from": _format_interval_timestamp(effective_from, timezone),
            "effective_to": _format_interval_timestamp(effective_to, timezone),
            "commit_sha": event["commit_sha"],
            "image_ref": event["image_ref"],
            "image_digest": event["image_digest"],
            "deployment_timestamp": event["deployed_at"],
            "evidence_source": event["evidence_source"],
            "evidence_kind": evidence_kind,
            "confidence": event["confidence"],
            "notes": event["notes"],
        }

    if before_start:
        active_event = before_start[-1][1]
        if not in_period and not after_period:
            return []
        first_boundary = in_period[0][0] if in_period else period_end
        intervals.append(
            _interval_row(
                effective_from=period_start,
                effective_to=first_boundary,
                event=active_event,
                evidence_kind="INFERRED_CONTINUITY",
            )
        )
        for index, (deployed_dt, event) in enumerate(in_period):
            next_boundary = (
                in_period[index + 1][0]
                if index + 1 < len(in_period)
                else period_end
            )
            intervals.append(
                _interval_row(
                    effective_from=deployed_dt,
                    effective_to=next_boundary,
                    event=event,
                    evidence_kind="DIRECT_DEPLOYMENT_RECEIPT",
                )
            )
        return intervals

    for index, (deployed_dt, event) in enumerate(in_period):
        effective_from = deployed_dt if index == 0 else deployed_dt
        next_boundary = (
            in_period[index + 1][0] if index + 1 < len(in_period) else period_end
        )
        intervals.append(
            _interval_row(
                effective_from=effective_from,
                effective_to=next_boundary,
                event=event,
                evidence_kind="DIRECT_DEPLOYMENT_RECEIPT",
            )
        )
    return intervals


def try_git_revision_timeline(
    from_day: date,
    to_day: date,
    timezone: str,
    repo_root: Path | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Опциональный local git log (dev worktree only; not cluster-primary)."""
    if shutil.which("git") is None:
        return [], ["git binary not available"]
    root = repo_root or Path(__file__).resolve().parents[1]
    if not (root / ".git").exists():
        return [], [f".git not found under {root}"]
    tz = ZoneInfo(timezone)
    since = datetime.combine(from_day, time.min, tzinfo=tz).isoformat()
    until = datetime.combine(
        to_day + timedelta(days=1), time.min, tzinfo=tz
    ).isoformat()
    branches = ["origin/stage", "origin/master", "origin/scripts"]
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for branch in branches:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "log",
                branch,
                f"--since={since}",
                f"--until={until}",
                "--format=%H|%cI|%an|%s",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            errors.append(f"{branch}: {proc.stderr.strip()[:200]}")
            continue
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue
            sha, committed_at, author, subject = parts
            rows.append(
                {
                    "branch": branch,
                    "commit_sha": sha,
                    "committed_at": committed_at,
                    "author": author,
                    "subject": subject,
                    "source": "local_git_read_only",
                }
            )
    return rows, errors


def export_prod_revision_timeline(
    from_day: date,
    to_day: date,
    timezone: str,
    *,
    ledger_path: Path | None = None,
    repo_root: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Effective prod revision intervals из committed deployment-event ledger."""
    del repo_root  # local git reconstruction — dev tooling only, not export path
    events = load_deployment_events(ledger_path=ledger_path)
    rows = derive_effective_intervals(events, from_day, to_day, timezone)
    status = "EXPORTED" if rows else "NOT_AVAILABLE"
    return rows, {
        "status": status,
        "rows": len(rows),
        "primary_source": "deployment_event_ledger" if events else "none",
        "deployment_events_loaded": len(events),
        "ledger_path": str(ledger_path or REVISION_LEDGER_PATH),
        "cluster_safe": bool(events),
    }


def ch_rows_to_csv(path: Path, columns: list[str]) -> list[dict[str, Any]]:
    """Прочитать JSONEachRow CH export и нормализовать колонки."""
    raw = evidence.read_jsonl(path)
    rows: list[dict[str, Any]] = []
    for item in raw:
        row = {col: item.get(col) for col in columns}
        if "carts" in columns and row.get("carts") in (None, ""):
            row["carts"] = item.get("add_to_cart")
        if "position" in columns:
            row["position"] = item.get("position") or item.get("avr_pos")
        rows.append(row)
    return rows


def resolve_shop_scope(
    shop_id: str,
    adv_ids: set[int],
    nmids: set[int],
    root: Path,
    sql_dir: Path,
) -> tuple[set[int], set[int], list[dict[str, Any]], list[str]]:
    """Разрешить adv_id/nmid и загрузить advsetting rows для shop."""
    gaps: list[str] = []
    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    cabinet_path = staging / "wbcabinet.csv"
    sid = esc_sql_str(shop_id)
    st = pg_query(
        _pg_database(),
        (
            "SELECT id, shop_id FROM public.wbcabinet "
            f"WHERE shop_id = '{sid}'"
        ),
        cabinet_path,
        sql_dir,
        "wbcabinet",
    )
    if not st["success"]:
        raise RuntimeError(f"wbcabinet query failed: {st['stderr']}")
    cabinets = read_csv_rows(cabinet_path)
    cabinet_ids = {int(c["id"]) for c in cabinets if c.get("id")}
    if not cabinet_ids:
        raise RuntimeError(f"No wbcabinet row for shop_id={shop_id}")
    ids_sql = int_csv(cabinet_ids)
    setting_path = staging / "advsetting.csv"
    st2 = pg_query(
        _pg_database(),
        f"SELECT * FROM public.advsetting WHERE wb_cabinet_id IN ({ids_sql})",
        setting_path,
        sql_dir,
        "advsetting",
    )
    if not st2["success"]:
        raise RuntimeError(f"advsetting query failed: {st2['stderr']}")
    settings = read_csv_rows(setting_path)
    resolved_adv: set[int] = set(adv_ids)
    resolved_nm: set[int] = set(nmids)
    for row in settings:
        if row.get("adv_id") and str(row["adv_id"]).isdigit():
            aid = int(row["adv_id"])
            if not adv_ids or aid in adv_ids:
                resolved_adv.add(aid)
        if row.get("_search_adv_id") and str(row["_search_adv_id"]).isdigit():
            sid_adv = int(row["_search_adv_id"])
            if not adv_ids or sid_adv in adv_ids:
                resolved_adv.add(sid_adv)
        try:
            parsed = ast.literal_eval(row.get("nmids") or "[]")
        except (ValueError, SyntaxError):
            parsed = []
        if isinstance(parsed, list):
            for v in parsed:
                if str(v).isdigit():
                    n = int(v)
                    if not nmids or n in nmids:
                        resolved_nm.add(n)
    if adv_ids and not resolved_adv:
        gaps.append("ADV_ID_FILTER: no matching advsetting rows for supplied adv_id")
    if nmids and not resolved_nm:
        gaps.append("NMID_FILTER: no matching nmids in advsetting for supplied nmid")
    if not resolved_adv:
        gaps.append("SCOPE: empty adv_id set after resolution")
    return resolved_adv, resolved_nm, settings, gaps


def load_keywords(
    settings: list[dict[str, Any]], root: Path, sql_dir: Path
) -> list[dict[str, Any]]:
    """CURRENT keywordsetting rows для adv_setting_id из snapshot."""
    setting_ids = {
        int(s["id"]) for s in settings if s.get("id") and str(s["id"]).isdigit()
    }
    if not setting_ids:
        return []
    ids_sql = int_csv(setting_ids)
    path = root / "staging" / "keywordsetting.csv"
    st = pg_query(
        _pg_database(),
        f"SELECT * FROM public.keywordsetting WHERE adv_setting_id IN ({ids_sql})",
        path,
        sql_dir,
        "keywordsetting",
    )
    if not st["success"]:
        return []
    return read_csv_rows(path)


def build_current_settings_snapshot(
    settings: list[dict[str, Any]], keywords: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Плоский CURRENT_SNAPSHOT; не выдавать за historical state."""
    observed = datetime.now().isoformat()
    rows: list[dict[str, Any]] = []
    for s in settings:
        for field in SETTING_FIELDS:
            if field in s and s[field] not in (None, ""):
                rows.append(
                    {
                        "snapshot_kind": "CURRENT_SNAPSHOT",
                        "observed_at": observed,
                        "object_type": "adv_setting",
                        "object_id": s.get("id"),
                        "adv_id": s.get("adv_id"),
                        "field": field,
                        "value": s.get(field),
                        "source": "postgresql.advsetting",
                        "historical": "NO",
                    }
                )
    adv_map = {
        int(s["id"]): s for s in settings if s.get("id") and str(s["id"]).isdigit()
    }
    for k in keywords:
        adv_s = adv_map.get(int(k.get("adv_setting_id") or 0), {})
        rows.append(
            {
                "snapshot_kind": "CURRENT_SNAPSHOT",
                "observed_at": observed,
                "object_type": "keyword_setting",
                "object_id": k.get("id"),
                "adv_id": adv_s.get("adv_id"),
                "field": "keyword_row",
                "value": json.dumps(
                    {
                        "text": k.get("text"),
                        "hard_status": k.get("hard_status"),
                        "strategy_mode": k.get("strategy_mode"),
                        "target_place": k.get("target_place"),
                    },
                    ensure_ascii=False,
                ),
                "source": "postgresql.keywordsetting",
                "historical": "NO",
            }
        )
    return rows


def export_plan_fact_stats(
    shop_id: str,
    adv_ids: set[int],
    from_day: date,
    to_day: date,
    timezone: str,
    root: Path,
    sql_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Выгрузка plan_fact_stats за период."""
    _, _, from_ts, to_ts = period_bounds(from_day, to_day, timezone)
    sid = esc_sql_str(shop_id)
    campaigns = int_csv(adv_ids)
    cov_path = root / "staging" / "plan_fact_coverage.jsonl"
    tz = esc_sql_str(timezone)
    cov_q = (
        "SELECT count() AS rows, toString(min(timestamp)) AS min_ts, "
        "toString(max(timestamp)) AS max_ts "
        "FROM default_db.plan_fact_stats "
        f"WHERE shop_id = '{sid}' "
        f"AND adv_id IN ({campaigns}) "
        f"AND timestamp >= toDateTime('{from_ts}', '{tz}') "
        f"AND timestamp <= toDateTime('{to_ts}', '{tz}')"
    )
    ch_query(cov_q, cov_path, sql_dir, "plan_fact_coverage")
    cov = evidence.read_jsonl(cov_path)
    out_path = root / "staging" / "plan_fact_stats.jsonl"
    query = (
        "SELECT timestamp, adv_id, plan_orders, plan_target_pay_for_order, "
        "plan_max_pay_for_order, fact_predict_orders, fact_original_orders, "
        "fact_pay_for_order, fact_method, shop_id, date, version "
        "FROM default_db.plan_fact_stats "
        f"WHERE shop_id = '{sid}' "
        f"AND adv_id IN ({campaigns}) "
        f"AND timestamp >= toDateTime('{from_ts}', '{tz}') "
        f"AND timestamp <= toDateTime('{to_ts}', '{tz}') "
        "ORDER BY timestamp, adv_id"
    )
    st = ch_query(query, out_path, sql_dir, "plan_fact_stats")
    rows = ch_rows_to_csv(out_path, PLAN_FACT_COLUMNS) if st["success"] else []
    return rows, {
        "status": "EXPORTED" if st["success"] else "FAILED",
        "rows": len(rows),
        "coverage": cov[0] if cov else {},
        "stderr": st.get("stderr", "")[:500],
    }


def export_keyword_intraday(
    adv_ids: set[int],
    nmids: set[int],
    from_day: date,
    to_day: date,
    root: Path,
    sql_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Raw clusters_adv_stats rows (intraday snapshots)."""
    campaigns = int_csv(adv_ids)
    nm_sql = int_csv(nmids) if nmids else ""
    nm_filter = f"AND nmid IN ({nm_sql}) " if nm_sql else ""
    cov_path = root / "staging" / "keyword_intraday_coverage.jsonl"
    cov_q = (
        "SELECT count() AS rows, toString(min(timestamp)) AS min_ts, "
        "toString(max(timestamp)) AS max_ts "
        "FROM default_db.clusters_adv_stats "
        f"WHERE adv_id IN ({campaigns}) {nm_filter}"
        f"AND date >= toDate('{from_day.isoformat()}') "
        f"AND date <= toDate('{to_day.isoformat()}')"
    )
    ch_query(cov_q, cov_path, sql_dir, "keyword_intraday_coverage")
    cov = evidence.read_jsonl(cov_path)
    out_path = root / "staging" / "keyword_intraday.jsonl"
    query = (
        "SELECT adv_id, nmid, norm_query, date, timestamp, views, clicks, "
        "add_to_cart AS carts, orders, spend, cpm, avr_pos AS position, ctr, cpc, wb_category "
        "FROM default_db.clusters_adv_stats "
        f"WHERE adv_id IN ({campaigns}) {nm_filter}"
        f"AND date >= toDate('{from_day.isoformat()}') "
        f"AND date <= toDate('{to_day.isoformat()}') "
        "ORDER BY timestamp, adv_id, nmid, norm_query"
    )
    st = ch_query(query, out_path, sql_dir, "keyword_intraday")
    rows = ch_rows_to_csv(out_path, KEYWORD_INTRADAY_COLUMNS) if st["success"] else []
    return rows, {
        "status": "EXPORTED" if st["success"] else "FAILED",
        "rows": len(rows),
        "coverage": cov[0] if cov else {},
        "stderr": st.get("stderr", "")[:500],
    }


def export_keyword_daily(
    adv_ids: set[int],
    nmids: set[int],
    from_day: date,
    to_day: date,
    root: Path,
    sql_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Daily rollup: last snapshot per (adv_id, nmid, norm_query, date)."""
    campaigns = int_csv(adv_ids)
    nm_sql = int_csv(nmids) if nmids else ""
    nm_filter = f"AND nmid IN ({nm_sql}) " if nm_sql else ""
    out_path = root / "staging" / "keyword_daily.jsonl"
    query = (
        "SELECT adv_id, nmid, norm_query, date, "
        "argMax(views, timestamp) AS views, "
        "argMax(clicks, timestamp) AS clicks, "
        "argMax(add_to_cart, timestamp) AS carts, "
        "argMax(orders, timestamp) AS orders, "
        "argMax(spend, timestamp) AS spend, "
        "argMax(cpm, timestamp) AS cpm, "
        "argMax(avr_pos, timestamp) AS position "
        "FROM default_db.clusters_adv_stats "
        f"WHERE adv_id IN ({campaigns}) {nm_filter}"
        f"AND date >= toDate('{from_day.isoformat()}') "
        f"AND date <= toDate('{to_day.isoformat()}') "
        "GROUP BY adv_id, nmid, norm_query, date "
        "ORDER BY date, adv_id, nmid, norm_query"
    )
    st = ch_query(query, out_path, sql_dir, "keyword_daily")
    rows = ch_rows_to_csv(out_path, KEYWORD_DAILY_COLUMNS) if st["success"] else []
    return rows, {
        "status": "EXPORTED" if st["success"] else "FAILED",
        "rows": len(rows),
        "stderr": st.get("stderr", "")[:500],
    }


def export_bid_decision_log(
    adv_ids: set[int],
    from_day: date,
    to_day: date,
    timezone: str,
    root: Path,
    sql_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """READ_ONLY bid_decision_log; без fill/backfill."""
    if not adv_ids:
        return [], {"status": "EMPTY", "rows": 0}
    _, _, from_ts, to_ts = period_bounds(from_day, to_day, timezone)
    campaigns = int_csv(adv_ids)
    tz = esc_sql_str(timezone)
    cov_path = root / "staging" / "bid_decision_coverage.jsonl"
    cov_q = (
        "SELECT count() AS rows, toString(min(decision_time)) AS min_ts, "
        "toString(max(decision_time)) AS max_ts "
        "FROM default_db.bid_decision_log "
        f"WHERE adv_id IN ({campaigns}) "
        f"AND decision_time >= toDateTime('{from_ts}', '{tz}') "
        f"AND decision_time <= toDateTime('{to_ts}', '{tz}')"
    )
    ch_query(cov_q, cov_path, sql_dir, "bid_decision_coverage")
    cov = evidence.read_jsonl(cov_path)
    out_path = root / "staging" / "bid_decision_log.jsonl"
    query = (
        "SELECT adv_id, nmid, norm_query, wb_category, pos_final, pos_final_bucket, "
        "views_curr, spend_curr, cpm_curr, pos_curr, views_prev, spend_prev, cpm_prev, "
        "pos_prev, final_bid, decision_source, stats_max_timestamp, decision_time, version "
        "FROM default_db.bid_decision_log "
        f"WHERE adv_id IN ({campaigns}) "
        f"AND decision_time >= toDateTime('{from_ts}', '{tz}') "
        f"AND decision_time <= toDateTime('{to_ts}', '{tz}') "
        "ORDER BY decision_time, adv_id, nmid, norm_query, version"
    )
    st = ch_query(query, out_path, sql_dir, "bid_decision_log")
    rows: list[dict[str, Any]] = evidence.read_jsonl(out_path) if st["success"] else []
    return rows, {
        "status": "EXPORTED" if st["success"] else "FAILED",
        "rows": len(rows),
        "coverage": cov[0] if cov else {},
        "stderr": st.get("stderr", "")[:500],
    }


def archive_directory(source_dir: Path, archive_path: Path) -> str:
    """Создать ZIP primary artifact и вернуть sha256."""
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(source_dir).as_posix())
    digest = hashlib.sha256()
    with archive_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_collect(
    *,
    shop_resolution: ShopResolution,
    from_day: date,
    to_day: date,
    adv_ids: set[int],
    nmids: set[int],
    timezone: str,
    output_dir: Path,
    case_slug: str,
) -> dict[str, Any]:
    """Выполнить полный READ_ONLY collect и создать primary ZIP."""
    shop_id = shop_resolution.resolved_shop_id
    if output_dir.exists():
        shutil.rmtree(output_dir)
    sql_dir = output_dir / "sql"
    sql_dir.mkdir(parents=True)
    bootstrap_cluster_infra()
    gaps: list[str] = []

    resolved_adv, resolved_nm, settings, scope_gaps = resolve_shop_scope(
        shop_id, adv_ids, nmids, output_dir, sql_dir
    )
    gaps.extend(scope_gaps)
    keywords = load_keywords(settings, output_dir, sql_dir)

    plan_rows, plan_meta = export_plan_fact_stats(
        shop_id, resolved_adv, from_day, to_day, timezone, output_dir, sql_dir
    )
    kw_intra, kw_intra_meta = export_keyword_intraday(
        resolved_adv, resolved_nm, from_day, to_day, output_dir, sql_dir
    )
    kw_daily, kw_daily_meta = export_keyword_daily(
        resolved_adv, resolved_nm, from_day, to_day, output_dir, sql_dir
    )
    bid_rows, bid_meta = export_bid_decision_log(
        resolved_adv, from_day, to_day, timezone, output_dir, sql_dir
    )
    rev_rows, rev_meta = export_prod_revision_timeline(from_day, to_day, timezone)
    snapshot_rows = build_current_settings_snapshot(settings, keywords)

    write_csv(output_dir / "plan_fact_intraday_raw.csv", plan_rows, PLAN_FACT_COLUMNS)
    write_csv(
        output_dir / "keyword_intraday_raw.csv", kw_intra, KEYWORD_INTRADAY_COLUMNS
    )
    write_csv(output_dir / "keyword_daily_raw.csv", kw_daily, KEYWORD_DAILY_COLUMNS)
    write_csv(output_dir / "bid_decision_raw.csv", bid_rows, BID_DECISION_COLUMNS)
    write_csv(
        output_dir / "current_settings_snapshot.csv",
        snapshot_rows,
        [
            "snapshot_kind",
            "observed_at",
            "object_type",
            "object_id",
            "adv_id",
            "field",
            "value",
            "source",
            "historical",
        ],
    )
    write_csv(
        output_dir / "prod_revision_timeline.csv",
        rev_rows,
        list(REVISION_INTERVAL_COLUMNS),
    )

    if plan_meta.get("status") != "EXPORTED" or plan_meta.get("rows", 0) == 0:
        gaps.append(f"plan_fact_stats: {plan_meta}")
    if kw_intra_meta.get("rows", 0) == 0:
        gaps.append(f"keyword_intraday: {kw_intra_meta}")
    if bid_meta.get("rows", 0) == 0:
        gaps.append(
            "bid_decision_log: empty or missing "
            "(may be expected if no decisions logged in period)"
        )
    if rev_meta.get("rows", 0) == 0 or rev_meta.get("status") == "NOT_AVAILABLE":
        gaps.append(f"prod_revision_timeline: {rev_meta}")

    coverage = {
        "shop_id": shop_id,
        "shop_resolution": shop_resolution.manifest_fields(),
        "period": {"from": from_day.isoformat(), "to": to_day.isoformat()},
        "timezone": timezone,
        "adv_ids": sorted(resolved_adv),
        "nmids": sorted(resolved_nm),
        "plan_fact_stats": plan_meta,
        "keyword_intraday": kw_intra_meta,
        "keyword_daily": kw_daily_meta,
        "bid_decision_log": bid_meta,
        "prod_revision_timeline": rev_meta,
        "current_settings_snapshot_rows": len(snapshot_rows),
        "gaps": gaps,
    }
    evidence.write_json(output_dir / "coverage.json", coverage)

    readme = [
        "# Adv-bot INTERNAL history pack",
        "",
        f"Case: `{case_slug}`",
        f"Shop: `{shop_id}`",
        f"Period: {from_day.isoformat()} .. {to_day.isoformat()} ({timezone})",
        "",
        "This pack is **INTERNAL adv-bot history** for forensic analysis.",
        "It does **not** replace ER-020 external WB/store outcome.",
        "",
        "`current_settings_snapshot.csv` is **CURRENT_SNAPSHOT only** — not historical state.",
        "",
        "Primary artifact contract: ADV_BOT_INTERNAL_HISTORY_<case>_<period>.zip + SHA256.",
    ]
    evidence.write_text(output_dir / "README.md", "\n".join(readme) + "\n")

    gap_lines = ["# DATA_GAPS", ""] + [f"- {g}" for g in gaps]
    evidence.write_text(output_dir / "DATA_GAPS.md", "\n".join(gap_lines) + "\n")

    zip_name = primary_zip_name(case_slug, from_day, to_day)
    manifest = {
        "artifact": "adv_bot_internal_history",
        "created_at": evidence.now_iso(),
        "case": case_slug,
        **shop_resolution.manifest_fields(),
        "timezone": timezone,
        "period": {"from": from_day.isoformat(), "to": to_day.isoformat()},
        "selectors": {
            "adv_id_filter": sorted(adv_ids),
            "nmid_filter": sorted(nmids),
            "resolved_adv_ids": sorted(resolved_adv),
            "resolved_nmids": sorted(resolved_nm),
        },
        "primary_zip": zip_name,
        "datasets": {
            "plan_fact_intraday_raw.csv": len(plan_rows),
            "keyword_intraday_raw.csv": len(kw_intra),
            "keyword_daily_raw.csv": len(kw_daily),
            "bid_decision_raw.csv": len(bid_rows),
            "current_settings_snapshot.csv": len(snapshot_rows),
            "prod_revision_timeline.csv": len(rev_rows),
        },
        "read_only": True,
        "er020_outcome_included": False,
    }
    evidence.write_json(output_dir / "manifest.json", manifest)

    findings = evidence.secret_scan(output_dir)
    if findings:
        raise SystemError(f"Secret scan failed: {findings[:5]}")

    archive_path = output_dir.parent / zip_name
    digest = archive_directory(output_dir, archive_path)
    sidecar = archive_path.with_suffix(archive_path.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")

    return {
        "EXECUTION_STATUS": "COMPLETE",
        "SHOP_ID": shop_id,
        "SHOP_RESOLUTION": shop_resolution.manifest_fields(),
        "CASE": case_slug,
        "PERIOD": period_slug(from_day, to_day),
        "PRIMARY_ZIP": str(archive_path.resolve()),
        "PRIMARY_SHA256": digest,
        "ZIP_ABSOLUTE_PATH": str(archive_path.resolve()),
        "ZIP_SHA256": digest,
        "LOCAL_ARTIFACT_HANDOFF": "PASS",
        "COVERAGE": coverage,
        "GAPS": gaps,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI для reusable INTERNAL history extractor."""
    parser = argparse.ArgumentParser(
        description="READ_ONLY adv-bot INTERNAL historical state extractor."
    )
    shop_group = parser.add_mutually_exclusive_group(required=True)
    shop_group.add_argument("--shop-id", help="WB shop UUID (explicit)")
    shop_group.add_argument(
        "--supplier-id",
        help="WB supplier_id; resolves canonical shop_id READ_ONLY from PG",
    )
    parser.add_argument("--from", dest="from_date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--adv-id",
        dest="adv_ids",
        action="append",
        type=int,
        default=[],
        help="Repeatable campaign adv_id filter",
    )
    parser.add_argument(
        "--nmid",
        dest="nmids",
        action="append",
        type=int,
        default=[],
        help="Repeatable nmid filter",
    )
    parser.add_argument("--timezone", default="Europe/Moscow")
    parser.add_argument(
        "--output-dir",
        default=".tmp/adv_bot_internal_history",
        help="Working directory before ZIP",
    )
    parser.add_argument(
        "--case",
        default="case",
        help="Case slug for ADV_BOT_INTERNAL_HISTORY_<case>_<period>.zip",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entrypoint."""
    args = parse_args(argv)
    from_day = date.fromisoformat(args.from_date)
    to_day = date.fromisoformat(args.to_date)
    if to_day < from_day:
        raise SystemExit("--to must be >= --from")
    out = Path(args.output_dir).resolve()
    sql_dir = out / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    try:
        shop_resolution = resolve_shop_identity(
            supplier_id=getattr(args, "supplier_id", None),
            shop_id=getattr(args, "shop_id", None),
            sql_dir=sql_dir,
        )
    except ShopResolutionError as exc:
        raise SystemExit(str(exc)) from exc
    result = run_collect(
        shop_resolution=shop_resolution,
        from_day=from_day,
        to_day=to_day,
        adv_ids=set(args.adv_ids),
        nmids=set(args.nmids),
        timezone=args.timezone,
        output_dir=out,
        case_slug=args.case,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
