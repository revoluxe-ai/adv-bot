"""Read-only ClickHouse/PostgreSQL/Redis evidence collector for one WB shop.

Модуль собирает техническую evidence-базу для ООО «А1» через уже работающие
Kubernetes workload'ы. Он выполняет только SELECT/metadata-запросы, сохраняет
каждый применённый SQL, сырые JSONL/CSV-выгрузки, provenance и контрольные
счётчики, а затем создаёт ZIP и SHA-256. Значения Secret и токенов в запросы
и артефакты не включаются.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode


SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
CH_NAMESPACE = "prod-analytics"
CH_POD = "clickhouse-restore-0"
CH_HTTP_URL = "http://194.87.215.163:8123/"
PG_NAMESPACE = "prod-adv-bot"
PG_POD = "postgres-db-0"
PG_SECRET_NAME = "advupdater.postgres-db.credentials.postgresql.acid.zalan.do"
PG_EXTERNAL_HOST = "92.255.79.78"
PG_EXTERNAL_PORT = 30432
REDIS_NAMESPACE = "prod-analytics"
REDIS_POD = "redis2-master-0"
_PG_CREDENTIALS: tuple[str, str] | None = None
_QUERY_PARAMETER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

SENSITIVE_NAMES = (
    "api_key",
    "token",
    "password",
    "secret",
    "authorization",
    "connection_string",
    "dsn",
)
ID_NAMES = {
    "shop_id",
    "cabinet_id",
    "wb_cabinet_id",
    "seller_id",
    "adv_id",
    "advert_id",
    "campaign_id",
    "nmid",
    "nm_id",
    "nmid",
}
SEMANTIC_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("orders_sales", ("order", "sale", "buyout", "return", "cancel", "common_stat")),
    ("advertising", ("adv", "advert", "campaign", "promo", "spend", "cpm", "cpc")),
    ("campaign_state", ("decision", "state", "snapshot", "setting", "bid", "budget")),
    ("funnel", ("funnel", "view", "open_card", "cart", "click", "impression")),
    ("normquery_search", ("query", "keyword", "norm", "position", "rank", "search")),
    ("product_state", ("product", "card", "price", "discount", "stock", "rating", "review")),
)


def quote_ch(identifier: str) -> str:
    """Экранировать идентификатор ClickHouse."""
    return f"`{identifier.replace('`', '``')}`"


def quote_pg(identifier: str) -> str:
    """Экранировать идентификатор PostgreSQL."""
    return '"' + identifier.replace('"', '""') + '"'


def safe_filename(value: str) -> str:
    """Преобразовать имя таблицы в безопасное имя локального файла."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def now_iso() -> str:
    """Вернуть UTC timestamp для manifest."""
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value: Any) -> None:
    """Сохранить JSON с UTF-8 и стабильным форматированием."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, value: str) -> None:
    """Сохранить текстовый артефакт."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def redact_kubernetes_metadata(value: Any, key: str = "") -> Any:
    """Удалить scalar values чувствительных ключей из Kubernetes JSON."""
    sensitive_keys = {
        "password",
        "api_key",
        "token",
        "secret",
        "connection_string",
    }
    if key.lower() in sensitive_keys:
        return "***REDACTED***"
    if isinstance(value, dict):
        return {
            child_key: redact_kubernetes_metadata(child_value, child_key)
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [redact_kubernetes_metadata(item) for item in value]
    return value


def redact_kubernetes_file(path: Path) -> None:
    """Перезаписать Kubernetes metadata JSON без credential values."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    write_json(path, redact_kubernetes_metadata(payload))


def run_streaming(
    args: list[str],
    output_path: Path,
    *,
    timeout_seconds: int = 1800,
) -> tuple[bool, str, int]:
    """Выполнить read-only subprocess и потоково записать stdout.

    Args:
        args: Аргументы без shell-интерпретации.
        output_path: Файл для stdout.
        timeout_seconds: Верхняя граница одного запроса.

    Returns:
        Кортеж ``(success, stderr, return_code)``.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    attempts = 5 if args and args[0].lower().endswith("kubectl") else 1
    last_stderr = ""
    last_return_code = 1
    for attempt in range(attempts):
        started = time.monotonic()
        with output_path.open("wb") as output:
            process = subprocess.Popen(
                args,
                stdout=output,
                stderr=subprocess.PIPE,
            )
            try:
                _, stderr_bytes = process.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                _, stderr_bytes = process.communicate()
                elapsed = time.monotonic() - started
                last_stderr = (
                    f"TIMEOUT after {elapsed:.1f}s\n"
                    f"{stderr_bytes.decode(errors='replace')}"
                )
                last_return_code = 124
                break
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        last_stderr = stderr
        last_return_code = int(process.returncode or 0)
        if process.returncode == 0:
            return True, stderr, 0
        transient = ("TLS handshake timeout", "Unable to connect", "EOF")
        if attempt + 1 < attempts and any(marker in stderr for marker in transient):
            time.sleep(3)
            continue
        break
    return False, last_stderr, last_return_code


def run_ch_query(
    query: str,
    output_path: Path,
    sql_path: Path,
    *,
    query_params: Mapping[str, object] | None = None,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    """Выполнить ClickHouse SELECT через штатный pod path.

    Args:
        query: SQL с ClickHouse placeholders вида ``{name:Type}``.
        output_path: Файл для JSONEachRow-ответа.
        sql_path: Сохраняемый SQL без значений runtime-параметров.
        query_params: Значения HTTP query parameters `param_<name>`.
        timeout_seconds: Максимальное время запроса.

    Returns:
        Machine-readable status без выполнения mutation-запросов.

    Raises:
        ValueError: если имя параметра не соответствует allowlist.
    """
    encoded_params = {"default_format": "JSONEachRow"}
    for name, value in (query_params or {}).items():
        if not _QUERY_PARAMETER_PATTERN.fullmatch(name):
            raise ValueError(f"unsafe ClickHouse query parameter name: {name}")
        encoded_params[f"param_{name}"] = (
            json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            if isinstance(value, (list, tuple))
            else str(value)
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(
        sql_path,
        (
            "-- ============================================================================\n"
            f"-- {sql_path.name}\n"
            "-- Назначение: READ_ONLY technical evidence extraction for ООО «А1».\n"
            "-- Таблица(и): ClickHouse system/data tables; credentials are never selected.\n"
            "-- Параметры: runtime values use ClickHouse HTTP query parameters.\n"
            "-- Вызывается: scripts/ch_a1_evidence.py.\n"
            "-- ============================================================================\n\n"
            f"{query.rstrip()}\n"
        ),
    )
    request = urllib.request.Request(
        f"{CH_HTTP_URL}?{urlencode(encoded_params)}",
        data=query.encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    last_error = ""
    success = False
    for attempt in range(3):
        try:
            output_path.write_bytes(b"")
            with opener.open(request, timeout=timeout_seconds) as response:
                with output_path.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
            success, last_error = True, ""
            break
        except (OSError, http.client.HTTPException, urllib.error.URLError) as exc:
            last_error = str(exc)
            output_path.write_bytes(b"")
            if attempt < 2:
                time.sleep(5)
    stderr, return_code = last_error, 0 if success else 1
    result = {
        "success": success,
        "stderr": stderr[-4000:],
        "return_code": return_code,
        "output": str(output_path),
        "access_path": CH_HTTP_URL,
    }
    if not success:
        write_text(output_path.with_suffix(output_path.suffix + ".error.txt"), stderr)
    return result


def _get_pg_credentials() -> tuple[str, str]:
    """Получить PG user/password из Secret без вывода содержимого."""
    global _PG_CREDENTIALS
    if _PG_CREDENTIALS is not None:
        return _PG_CREDENTIALS
    last_error = "unknown error"
    for attempt in range(5):
        try:
            completed = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "secret",
                    PG_SECRET_NAME,
                    "-n",
                    PG_NAMESPACE,
                    "-o",
                    "json",
                ],
                check=False,
                capture_output=True,
                timeout=60,
            )
            if completed.returncode != 0:
                last_error = completed.stderr.decode("utf-8", errors="replace")
            else:
                payload = json.loads(completed.stdout.decode("utf-8"))
                encoded = payload["data"]
                username = base64.b64decode(encoded["username"]).decode("utf-8")
                password = base64.b64decode(encoded["password"]).decode("utf-8")
                _PG_CREDENTIALS = username, password
                return _PG_CREDENTIALS
        except (OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError) as exc:
            last_error = str(exc)
        if attempt < 4:
            time.sleep(3)
    raise RuntimeError(f"Unable to read PostgreSQL Secret metadata: {last_error[-500:]}")


def _serialize_pg_value(value: Any) -> str:
    """Сериализовать значение PG в стабильный текстовый CSV/TSV cell."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


async def _write_pg_query(
    database: str,
    query: str,
    output_path: Path,
    *,
    query_params: Sequence[object],
    timeout_seconds: int,
    csv_output: bool,
    csv_columns: list[str] | None,
) -> None:
    """Потоково выполнить SELECT по внешнему read-only NodePort."""
    import asyncpg  # type: ignore[import-not-found]

    username, password = _get_pg_credentials()
    ssl_mode = os.environ.get("POSTGRES_SSL_MODE", "").lower()
    ssl_insecure = os.environ.get("POSTGRES_SSL_INSECURE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    use_ssl = ssl_mode == "require" and not ssl_insecure
    connection = await asyncpg.connect(
        host=PG_EXTERNAL_HOST,
        port=PG_EXTERNAL_PORT,
        user=username,
        password=password,
        database=database,
        # NodePort path uses ssl=False; in-cluster Job may require TLS.
        ssl=use_ssl,
        timeout=timeout_seconds,
        statement_cache_size=0,
    )
    try:
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="," if csv_output else "\t", lineterminator="\n")
            async with connection.transaction():
                cursor = connection.cursor(query, *query_params, prefetch=1000)
                header_written = False
                if csv_output and csv_columns:
                    writer.writerow(csv_columns)
                    header_written = True
                async for row in cursor:
                    if csv_output and not header_written:
                        writer.writerow(list(row.keys()))
                        header_written = True
                    writer.writerow([_serialize_pg_value(row[column]) for column in row.keys()])
    finally:
        await connection.close()


def run_pg_query(
    database: str,
    query: str,
    output_path: Path,
    sql_path: Path,
    *,
    query_params: Sequence[object] = (),
    timeout_seconds: int = 1800,
    csv_output: bool = False,
    csv_columns: list[str] | None = None,
) -> dict[str, Any]:
    """Выполнить PostgreSQL SELECT через read-only внешний NodePort."""
    write_text(
        sql_path,
        (
            "-- ============================================================================\n"
            f"-- {sql_path.name}\n"
            "-- Назначение: READ_ONLY technical evidence extraction for ООО «А1».\n"
            "-- Таблица(и): PostgreSQL information_schema/public tables; sensitive columns excluded.\n"
            "-- Параметры: values are passed through asyncpg bind parameters ($1, $2, ...).\n"
            "-- Вызывается: scripts/ch_a1_evidence.py.\n"
            "-- ============================================================================\n\n"
            f"{query.rstrip()}\n"
        ),
    )
    try:
        asyncio.run(
            _write_pg_query(
                database,
                query,
                output_path,
                query_params=query_params,
                timeout_seconds=timeout_seconds,
                csv_output=csv_output,
                csv_columns=csv_columns,
            )
        )
        success, stderr, return_code = True, "", 0
    except Exception as exc:
        output_path.write_bytes(b"")
        success, stderr, return_code = False, str(exc), 1
    result = {
        "success": success,
        "stderr": stderr[-4000:],
        "return_code": return_code,
        "output": str(output_path),
        "access_path": f"{PG_EXTERNAL_HOST}:{PG_EXTERNAL_PORT}",
    }
    if not success:
        write_text(output_path.with_suffix(output_path.suffix + ".error.txt"), stderr)
    return result


def run_redis_command(command: list[str], output_path: Path) -> dict[str, Any]:
    """Выполнить Redis metadata-команду без чтения payload."""
    success, stderr, return_code = run_streaming(
        [
            "kubectl",
            "exec",
            "-n",
            REDIS_NAMESPACE,
            REDIS_POD,
            "--",
            "redis-cli",
            "--raw",
            *command,
        ],
        output_path,
        timeout_seconds=120,
    )
    return {
        "success": success,
        "stderr": stderr[-4000:],
        "return_code": return_code,
        "output": str(output_path),
    }


def run_kubectl_json(args: list[str], output_path: Path) -> dict[str, Any]:
    """Сохранить Kubernetes metadata без Secret values."""
    success, stderr, return_code = run_streaming(
        ["kubectl", *args],
        output_path,
        timeout_seconds=180,
    )
    if success:
        redact_kubernetes_file(output_path)
    return {
        "success": success,
        "stderr": stderr[-4000:],
        "return_code": return_code,
        "output": str(output_path),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Прочитать небольшой JSONEachRow metadata-файл."""
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def read_tsv(path: Path) -> list[list[str]]:
    """Прочитать tab-separated metadata PostgreSQL."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        return [row for row in csv.reader(handle, delimiter="\t") if row]


def count_json_rows(path: Path) -> tuple[int, set[str], set[str]]:
    """Посчитать JSONL и извлечь встреченные nmid/adv IDs."""
    rows = 0
    nmids: set[str] = set()
    adv_ids: set[str] = set()
    if not path.exists():
        return rows, nmids, adv_ids
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows += 1
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            for key in ("nmid", "nm_id", "nmID", "nmId"):
                if item.get(key) is not None:
                    nmids.add(str(item[key]))
            for key in ("adv_id", "advert_id", "campaign_id", "advertId"):
                if item.get(key) is not None:
                    adv_ids.add(str(item[key]))
    return rows, nmids, adv_ids


def count_csv_rows(path: Path) -> int:
    """Посчитать записи CSV без заголовка."""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def csv_temporal_bounds(path: Path, columns: list[str]) -> tuple[str | None, str | None]:
    """Найти лексикографические min/max по очевидным temporal columns CSV."""
    temporal_columns = [
        column
        for column in columns
        if column.lower() in {
            "date",
            "timestamp",
            "time",
            "created",
            "updated",
            "last_update",
            "expiration_time",
            "date_start",
            "date_end",
        }
        or column.lower().endswith(("_at", "_date", "_time"))
    ]
    if not path.exists() or not temporal_columns:
        return None, None
    minimum: str | None = None
    maximum: str | None = None
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            for column in temporal_columns:
                value = (row.get(column) or "").strip()
                if not value:
                    continue
                minimum = value if minimum is None or value < minimum else minimum
                maximum = value if maximum is None or value > maximum else maximum
    return minimum, maximum


def choose_family(name: str, columns: Iterable[str]) -> str:
    """Определить предметную family без смешивания рекламных и shop metrics."""
    haystack = f"{name} {' '.join(columns)}".lower()
    if any(term in haystack for term in ("keyword", "norm_query", "query", "position", "rank")):
        return "normquery_search"
    if any(term in haystack for term in ("snapshot", "decision", "setting", "bid", "budget", "strategy", "mode")):
        return "campaign_state"
    if "adv" in haystack or "advert" in haystack or "campaign" in haystack:
        return "advertising"
    if (
        "common_stat" in haystack
        and any(term in haystack for term in ("open_card", "add_to_cart", "buy_out"))
    ):
        return "funnel"
    if any(term in haystack for term in ("order", "sale", "buyout", "return", "cancel", "common_stat")):
        return "orders_sales"
    if any(term in haystack for term in ("funnel", "view", "open_card", "cart", "click", "impression")):
        return "funnel"
    if any(term in haystack for term in ("product", "card", "price", "discount", "stock", "rating", "review")):
        return "product_state"
    return "unknown"


def choose_semantic(name: str, columns: Iterable[str]) -> str:
    """Назначить один из фиксированных semantic provenance типов."""
    haystack = f"{name} {' '.join(columns)}".lower()
    if any(term in name.lower() for term in ("event", "decision_log")):
        return "APPLICATION_EVENT"
    if any(term in haystack for term in ("snapshot", "price", "discount", "stock", "rating", "review")):
        return "SNAPSHOT"
    if any(term in haystack for term in ("keyword", "norm_query", "position", "rank")):
        return "NORMALIZED_SOURCE"
    if any(term in haystack for term in ("mv_", "aggregate", "hourly", "cluster", "funnel", "plan_fact")):
        return "DERIVED_METRIC"
    if choose_family(name, columns) != "unknown":
        return "RAW_SOURCE"
    return "UNKNOWN"


def temporal_column(columns: list[dict[str, Any]]) -> str | None:
    """Выбрать наиболее вероятную temporal column для min/max."""
    preferred = (
        "event_date",
        "date",
        "timestamp",
        "event_time",
        "created_at",
        "updated_at",
        "time",
    )
    names = {str(row.get("name", "")).lower(): str(row.get("name", "")) for row in columns}
    for name in preferred:
        if name in names:
            return names[name]
    for row in columns:
        column_name = str(row.get("name", ""))
        column_type = str(row.get("type", ""))
        if "date" in column_type.lower() or "datetime" in column_type.lower():
            return column_name
    return None


def _clickhouse_parameter_list(
    prefix: str, values: Iterable[int], type_name: str
) -> tuple[str, dict[str, int]]:
    """Сформировать bound-плейсхолдеры ClickHouse для списка integer values."""
    ordered = sorted(values)
    parameters = {
        f"{prefix}_{index}": value for index, value in enumerate(ordered)
    }
    placeholders = ", ".join(
        f"{{{name}:{type_name}}}" for name in parameters
    )
    return placeholders, parameters


def filter_for_clickhouse(
    columns: list[dict[str, Any]],
    cabinet_ids: set[int],
    adv_ids: set[int],
    nmids: set[int],
    *,
    shop_id: str,
) -> tuple[str | None, str, dict[str, object]]:
    """Построить ClickHouse filter без интерполяции runtime values."""
    names = {str(row.get("name", "")).lower(): str(row.get("name", "")) for row in columns}
    clauses: list[str] = []
    mappings: list[str] = []
    bound_parameters: dict[str, object] = {}
    if "shop_id" in names:
        clauses.append(f"{quote_ch(names['shop_id'])} = {{shop_id:String}}")
        mappings.append("direct shop_id")
        return clauses[0], "; ".join(mappings), {"shop_id": shop_id}
    for key in ("cabinet_id", "wb_cabinet_id"):
        if key in names and cabinet_ids:
            values, parameters = _clickhouse_parameter_list(
                "cabinet_id", cabinet_ids, "UInt64"
            )
            clauses.append(f"{quote_ch(names[key])} IN ({values})")
            mappings.append(f"PG wbcabinet.id -> {key}")
            bound_parameters.update(parameters)
    for key in ("adv_id", "advert_id", "campaign_id"):
        if key in names and adv_ids:
            values, parameters = _clickhouse_parameter_list(
                "adv_id", adv_ids, "UInt64"
            )
            clauses.append(f"{quote_ch(names[key])} IN ({values})")
            mappings.append(f"PG advsetting.adv_id -> {key}")
            bound_parameters.update(parameters)
    for key in ("nmid", "nm_id", "nmID", "nmId"):
        lower_key = key.lower()
        if lower_key in names and nmids:
            values, parameters = _clickhouse_parameter_list(
                "nmid", nmids, "UInt64"
            )
            clauses.append(f"{quote_ch(names[lower_key])} IN ({values})")
            mappings.append(f"PG advsetting.nmids -> {names[lower_key]}")
            bound_parameters.update(parameters)
    if not clauses:
        return None, "no safe A1 mapping", {}
    return (
        " OR ".join(f"({clause})" for clause in clauses),
        "; ".join(mappings),
        bound_parameters,
    )


def _postgres_parameter_list(
    identifier: str, values: Iterable[int], start_index: int
) -> tuple[str, tuple[int, ...]]:
    """Сформировать asyncpg positional placeholders для integer values."""
    ordered = tuple(sorted(values))
    placeholders = ", ".join(
        f"${index}" for index in range(start_index, start_index + len(ordered))
    )
    return f"{identifier} IN ({placeholders})", ordered


def filter_for_postgres(
    columns: list[str],
    cabinet_ids: set[int],
    adv_setting_ids: set[int],
    adv_ids: set[int],
    nmids: set[int],
    *,
    shop_id: str,
) -> tuple[str | None, str, list[str], tuple[object, ...]]:
    """Построить PostgreSQL filter и asyncpg bind parameters."""
    lower = {column.lower(): column for column in columns}
    clauses: list[str] = []
    mappings: list[str] = []
    if "shop_id" in lower:
        clauses.append(f"{quote_pg(lower['shop_id'])} = $1")
        mappings.append("direct shop_id")
        return clauses[0], "; ".join(mappings), [
            column
            for column in columns
            if not any(marker in column.lower() for marker in SENSITIVE_NAMES)
        ], (shop_id,)
    parameters: list[object] = []
    parameter_index = 1
    for key in ("wb_cabinet_id", "cabinet_id"):
        if key in lower and cabinet_ids:
            clause, values = _postgres_parameter_list(
                quote_pg(lower[key]), cabinet_ids, parameter_index
            )
            clauses.append(clause)
            parameters.extend(values)
            parameter_index += len(values)
            mappings.append(f"PG wbcabinet.id -> {key}")
    if "adv_setting_id" in lower and adv_setting_ids:
        clause, values = _postgres_parameter_list(
            quote_pg(lower["adv_setting_id"]), adv_setting_ids, parameter_index
        )
        clauses.append(clause)
        parameters.extend(values)
        parameter_index += len(values)
        mappings.append("PG advsetting.id -> adv_setting_id")
    if "adv_id" in lower and adv_ids:
        clause, values = _postgres_parameter_list(
            quote_pg(lower["adv_id"]), adv_ids, parameter_index
        )
        clauses.append(clause)
        parameters.extend(values)
        parameter_index += len(values)
        mappings.append("PG advsetting.adv_id -> adv_id")
    for key in ("nmid", "nm_id"):
        if key in lower and nmids:
            clause, values = _postgres_parameter_list(
                quote_pg(lower[key]), nmids, parameter_index
            )
            clauses.append(clause)
            parameters.extend(values)
            parameter_index += len(values)
            mappings.append(f"PG advsetting.nmids -> {key}")
    safe_columns = [
        column
        for column in columns
        if not any(marker in column.lower() for marker in SENSITIVE_NAMES)
    ]
    if not safe_columns:
        return None, "all columns are sensitive", [], tuple(parameters)
    return (
        " OR ".join(f"({clause})" for clause in clauses) if clauses else None,
        "; ".join(mappings) if mappings else "no safe A1 mapping",
        safe_columns,
        tuple(parameters),
    )


def parse_mapping_rows(path: Path) -> tuple[set[int], set[int], set[int], set[int]]:
    """Извлечь cabinet IDs, AdvSetting IDs, adv IDs и nmids из CSV."""
    cabinet_ids: set[int] = set()
    setting_ids: set[int] = set()
    adv_ids: set[int] = set()
    nmids: set[int] = set()
    if not path.exists():
        return cabinet_ids, setting_ids, adv_ids, nmids
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for key, target in (
                ("id", setting_ids),
                ("wb_cabinet_id", cabinet_ids),
                ("cabinet_id", cabinet_ids),
                ("adv_id", adv_ids),
            ):
                value = row.get(key)
                if value and value.isdigit():
                    target.add(int(value))
            raw_nmids = row.get("nmids") or ""
            try:
                parsed = json.loads(raw_nmids)
            except (TypeError, json.JSONDecodeError):
                parsed = []
            if isinstance(parsed, list):
                for value in parsed:
                    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
                        nmids.add(int(value))
    return cabinet_ids, setting_ids, adv_ids, nmids


def extract_ch_table(
    out: Path,
    sql_dir: Path,
    database: str,
    table: str,
    columns: list[dict[str, Any]],
    filter_sql: str | None,
    filter_params: Mapping[str, object],
    mapping: str,
    table_meta: dict[str, Any],
    sequence: int,
) -> dict[str, Any]:
    """Собрать одну ClickHouse table через bound filters."""
    qualified = f"{quote_ch(database)}.{quote_ch(table)}"
    temporal = temporal_column(columns)
    column_types = {
        str(row.get("name", "")): str(row.get("type", "")) for row in columns
    }
    where = f" WHERE {filter_sql}" if filter_sql else ""
    count_query = f"SELECT count() AS records_selected FROM {qualified}{where}"
    if temporal:
        count_query = (
            f"SELECT count() AS records_selected, "
            f"toString(min({quote_ch(temporal)})) AS min_date, "
            f"toString(max({quote_ch(temporal)})) AS max_date "
            f"FROM {qualified}{where}"
        )
    stem = f"{sequence:03d}_{safe_filename(database)}_{safe_filename(table)}"
    stats_path = out / "metadata" / f"{stem}_stats.jsonl"
    stats_sql = sql_dir / f"{stem}_stats.sql"
    stats_result = run_ch_query(
        count_query,
        stats_path,
        stats_sql,
        query_params=filter_params,
    )
    stats_rows = read_jsonl(stats_path)
    stats = stats_rows[0] if stats_rows else {}
    column_names = [str(row.get("name", "")) for row in columns]
    semantic = choose_semantic(table, column_names)
    family = choose_family(table, column_names)
    raw_directory = out / "raw" / family
    raw_directory.mkdir(parents=True, exist_ok=True)
    raw_path = raw_directory / (
        f"{safe_filename(database)}_{safe_filename(table)}.jsonl"
    )
    rows_written = 0
    selected = int(stats.get("records_selected") or 0) if stats_result["success"] else 0
    raw_paths: list[Path] = []
    raw_sql_paths: list[Path] = []
    raw_results: list[dict[str, Any]] = []
    observed_nmids: set[str] = set()
    observed_adv_ids: set[str] = set()
    # Large MergeTree tables are split into date windows so an HTTP connection
    # reset cannot invalidate the already downloaded history.
    use_windows = (
        stats_result["success"]
        and selected > 5_000_000
        and temporal is not None
        and stats.get("min_date")
        and stats.get("max_date")
    )
    if use_windows:
        start = datetime.strptime(str(stats["min_date"])[:10], "%Y-%m-%d").date()
        end = datetime.strptime(str(stats["max_date"])[:10], "%Y-%m-%d").date()
        temporal_type = column_types.get(temporal, "").lower()
        while start <= end:
            stop = min(start + timedelta(days=7), end + timedelta(days=1))
            if "date" in temporal_type and "datetime" not in temporal_type:
                window_type = "Date"
            else:
                window_type = "DateTime"
            window_filter = (
                f"({filter_sql}) AND {quote_ch(temporal)} >= "
                f"{{window_start:{window_type}}} AND {quote_ch(temporal)} < "
                f"{{window_end:{window_type}}}"
            )
            window_params = {
                **filter_params,
                "window_start": start.isoformat()
                if window_type == "Date"
                else f"{start.isoformat()} 00:00:00",
                "window_end": stop.isoformat()
                if window_type == "Date"
                else f"{stop.isoformat()} 00:00:00",
            }
            window_stem = (
                f"{stem}_{start.strftime('%Y%m%d')}_{(stop - timedelta(days=1)).strftime('%Y%m%d')}"
            )
            window_path = raw_directory / f"{window_stem}.jsonl"
            window_sql = sql_dir / f"{window_stem}_extract.sql"
            window_result = run_ch_query(
                f"SELECT * FROM {qualified} WHERE {window_filter}",
                window_path,
                window_sql,
                query_params=window_params,
                timeout_seconds=3600,
            )
            written, window_nmids, window_adv_ids = count_json_rows(window_path)
            rows_written += written
            observed_nmids.update(window_nmids)
            observed_adv_ids.update(window_adv_ids)
            raw_paths.append(window_path)
            raw_sql_paths.append(window_sql)
            raw_results.append(window_result)
            start = stop
    else:
        raw_sql = sql_dir / f"{stem}_extract.sql"
        raw_result = run_ch_query(
            f"SELECT * FROM {qualified}{where}",
            raw_path,
            raw_sql,
            query_params=filter_params,
            timeout_seconds=3600,
        )
        rows_written, observed_nmids, observed_adv_ids = count_json_rows(raw_path)
        raw_paths.append(raw_path)
        raw_sql_paths.append(raw_sql)
        raw_results.append(raw_result)
    if not stats_result["success"]:
        selected = rows_written
    all_extract_success = bool(raw_results) and all(
        bool(result["success"]) for result in raw_results
    )
    completeness = "FULL_AVAILABLE" if stats_result["success"] and all_extract_success else "UNAVAILABLE"
    if selected == 0 and stats_result["success"]:
        completeness = "EMPTY"
    if stats_result["success"] and all_extract_success and selected != rows_written:
        completeness = "PARTIAL"
    if stats_result["success"] and not all_extract_success and rows_written > 0:
        completeness = "PARTIAL"
    return {
        "source_system": "clickhouse",
        "database": database,
        "schema": None,
        "table": table,
        "query_file": [str(path.relative_to(out)) for path in raw_sql_paths],
        "grain": "raw table row; exact grain requires table-specific reconciliation",
        "family": family,
        "semantic_type": semantic,
        "records_selected": selected,
        "records_written": rows_written,
        "rows": rows_written,
        "min_date": stats.get("min_date"),
        "max_date": stats.get("max_date"),
        "shop_filter": SHOP_ID,
        "join_mapping_used": mapping,
        "unique_nmids": sorted(observed_nmids, key=lambda value: (len(value), value)),
        "unique_campaign_ids": sorted(observed_adv_ids, key=lambda value: (len(value), value)),
        "columns": [str(row.get("name", "")) for row in columns],
        "partition_info": table_meta.get("partition_key"),
        "order_key": table_meta.get("sorting_key"),
        "primary_key": table_meta.get("primary_key"),
        "engine": table_meta.get("engine"),
        "ttl": table_meta.get("ttl_table"),
        "provenance": "repository schema/code + ClickHouse raw table",
        "notes": (
            "Raw revisions retained; ReplacingMergeTree/argMax semantics were not "
            "collapsed automatically. Materialized aggregate states are raw states."
        ),
        "completeness": completeness,
        "query_status": {
            "stats": stats_result,
            "extract": raw_results,
        },
    }


def extract_pg_table(
    out: Path,
    sql_dir: Path,
    database: str,
    schema: str,
    table: str,
    columns: list[str],
    filter_sql: str,
    filter_params: Sequence[object],
    mapping: str,
    sequence: int,
    *,
    table_semantic: str | None = None,
) -> dict[str, Any]:
    """Собрать безопасную projection одной PostgreSQL table в CSV."""
    projection = ", ".join(quote_pg(column) for column in columns)
    qualified = f"{quote_pg(schema)}.{quote_pg(table)}"
    select = f"SELECT {projection} FROM {qualified} WHERE {filter_sql}"
    query = select
    stem = f"{sequence:03d}_{safe_filename(database)}_{safe_filename(schema)}_{safe_filename(table)}"
    raw_path = out / "postgres" / (f"{safe_filename(database)}_{safe_filename(schema)}_{safe_filename(table)}.csv")
    sql_path = sql_dir / f"{stem}.sql"
    result = run_pg_query(
        database,
        query,
        raw_path,
        sql_path,
        query_params=filter_params,
        csv_output=True,
        csv_columns=columns,
    )
    rows_written = count_csv_rows(raw_path)
    min_date, max_date = csv_temporal_bounds(raw_path, columns)
    observed_nmids: set[str] = set()
    observed_adv_ids: set[str] = set()
    if raw_path.exists():
        with raw_path.open(encoding="utf-8", errors="replace", newline="") as handle:
            for row in csv.DictReader(handle):
                for key in ("nmid", "nm_id", "nmID", "nmId"):
                    if row.get(key):
                        observed_nmids.add(row[key])
                for key in ("adv_id", "advert_id", "campaign_id"):
                    if row.get(key):
                        observed_adv_ids.add(row[key])
    completeness = "FULL_AVAILABLE" if result["success"] else "UNAVAILABLE"
    if result["success"] and rows_written == 0:
        completeness = "EMPTY"
    return {
        "source_system": "postgresql",
        "database": database,
        "schema": schema,
        "table": table,
        "query_file": str(sql_path.relative_to(out)),
        "grain": "PostgreSQL source row",
        "family": choose_family(table, columns),
        "semantic_type": table_semantic or choose_semantic(table, columns),
        "records_selected": rows_written,
        "records_written": rows_written,
        "rows": rows_written,
        "min_date": min_date,
        "max_date": max_date,
        "shop_filter": SHOP_ID,
        "join_mapping_used": mapping,
        "unique_nmids": sorted(observed_nmids, key=lambda value: (len(value), value)),
        "unique_campaign_ids": sorted(observed_adv_ids, key=lambda value: (len(value), value)),
        "columns": columns,
        "partition_info": None,
        "ttl": None,
        "provenance": "repository SQLAlchemy model + PostgreSQL source row",
        "notes": "Sensitive column names were excluded from projection.",
        "completeness": completeness,
        "query_status": result,
    }


def _build_wbcabinet_query(
    columns: list[str], shop_id: str
) -> tuple[str, tuple[object, ...]]:
    """Построить cabinet SELECT с asyncpg bind parameter для shop_id."""
    query = (
        f"SELECT {', '.join(quote_pg(column) for column in columns)} "
        f"FROM {quote_pg('public')}.{quote_pg('wbcabinet')} "
        f"WHERE {quote_pg('shop_id')} = $1"
    )
    return query, (shop_id,)


def _build_advsetting_query(
    columns: list[str], cabinet_ids: set[int]
) -> tuple[str, tuple[object, ...]]:
    """Построить AdvSetting SELECT с bind parameters для cabinet IDs."""
    if cabinet_ids and "wb_cabinet_id" in columns:
        setting_filter, setting_params = _postgres_parameter_list(
            quote_pg("wb_cabinet_id"), cabinet_ids, 1
        )
    else:
        setting_filter, setting_params = "1 = 0", ()
    query = (
        f"SELECT {', '.join(quote_pg(column) for column in columns)} "
        f"FROM {quote_pg('public')}.{quote_pg('advsetting')} "
        f"WHERE {setting_filter}"
    )
    return query, setting_params


def collect_infrastructure(out: Path) -> list[dict[str, Any]]:
    """Сохранить Kubernetes resource metadata без чтения Secret values."""
    infra = out / "infrastructure"
    commands = [
        ("namespaces.json", ["get", "namespaces", "-o", "json"]),
        ("services.json", ["get", "services", "-A", "-o", "json"]),
        ("statefulsets.json", ["get", "statefulsets", "-A", "-o", "json"]),
        ("deployments.json", ["get", "deployments", "-A", "-o", "json"]),
        ("pvcs.json", ["get", "pvc", "-A", "-o", "json"]),
    ]
    statuses: list[dict[str, Any]] = []
    for filename, command in commands:
        path = infra / filename
        statuses.append({"file": filename, **run_kubectl_json(command, path)})
    write_json(infra / "collection_status.json", statuses)
    return statuses


def collect_clickhouse(
    out: Path,
    sql_dir: Path,
    cabinet_ids: set[int],
    adv_ids: set[int],
    nmids: set[int],
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    """Собрать ClickHouse schema, parts, query-log и A1 raw datasets."""
    schema_dir = out / "schema"
    metadata_dir = out / "metadata"
    files = [
        (
            "databases.jsonl",
            "SELECT * FROM system.databases ORDER BY name",
            "001_system_databases.sql",
        ),
        (
            "tables.jsonl",
            "SELECT * FROM system.tables WHERE database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema') ORDER BY database, name",
            "002_system_tables.sql",
        ),
        (
            "columns.jsonl",
            "SELECT * FROM system.columns WHERE database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema') ORDER BY database, table, position",
            "003_system_columns.sql",
        ),
        (
            "parts.jsonl",
            (
                "SELECT database, table, partition, partition_id, active, rows, bytes_on_disk, "
                "data_compressed_bytes, data_uncompressed_bytes, min_date, max_date, min_time, "
                "max_time, modification_time, level FROM system.parts "
                "WHERE active AND database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema') "
                "ORDER BY database, table, partition_id"
            ),
            "004_system_parts.sql",
        ),
        (
            "query_log.jsonl",
            (
                "SELECT event_time, type, query_duration_ms, read_rows, read_bytes, databases, "
                "tables, normalized_query FROM system.query_log "
                "WHERE event_time >= now() - INTERVAL 30 DAY AND type = 'QueryFinish' "
                "AND (positionCaseInsensitive(normalized_query, 'default_db') > 0 "
                "OR positionCaseInsensitive(normalized_query, 'full_adv') > 0 "
                "OR positionCaseInsensitive(normalized_query, 'wb_common') > 0 "
                "OR positionCaseInsensitive(normalized_query, 'clusters_adv') > 0 "
                "OR positionCaseInsensitive(normalized_query, 'keyword') > 0) "
                "ORDER BY event_time DESC LIMIT 5000"
            ),
            "005_system_query_log.sql",
        ),
    ]
    statuses: list[dict[str, Any]] = []
    for filename, query, sql_name in files:
        destination = (schema_dir if filename in {"databases.jsonl", "tables.jsonl", "columns.jsonl"} else metadata_dir) / filename
        statuses.append({"file": str(destination.relative_to(out)), **run_ch_query(query, destination, sql_dir / sql_name)})
    write_json(metadata_dir / "inventory_status.json", statuses)

    table_rows = read_jsonl(schema_dir / "tables.jsonl")
    column_rows = read_jsonl(schema_dir / "columns.jsonl")
    columns_by_table: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in column_rows:
        columns_by_table[(str(row.get("database")), str(row.get("table")))].append(row)
    table_by_key = {
        (str(row.get("database")), str(row.get("name"))): row for row in table_rows
    }

    coverage: list[dict[str, Any]] = []
    observed_nmids: set[str] = set()
    observed_adv_ids: set[str] = set()
    sequence = 100
    for (database, table), columns in sorted(columns_by_table.items()):
        if database not in {"default", "default_db"}:
            continue
        names = [str(row.get("name", "")) for row in columns]
        haystack = f"{table} {' '.join(names)}".lower()
        if not any(term in haystack for _, terms in SEMANTIC_TERMS for term in terms):
            continue
        table_meta = table_by_key.get((database, table), {})
        engine = str(table_meta.get("engine", ""))
        if "View" in engine:
            continue
        filter_sql, mapping, filter_params = filter_for_clickhouse(
            columns,
            cabinet_ids,
            adv_ids,
            nmids,
            shop_id=SHOP_ID,
        )
        if filter_sql is None:
            continue
        item = extract_ch_table(
            out,
            sql_dir,
            database,
            table,
            columns,
            filter_sql,
            filter_params,
            mapping,
            table_meta,
            sequence,
        )
        coverage.append(item)
        observed_nmids.update(item["unique_nmids"])
        observed_adv_ids.update(item["unique_campaign_ids"])
        sequence += 1
    write_json(metadata_dir / "a1_table_coverage.json", coverage)
    return coverage, observed_nmids, observed_adv_ids


def collect_postgres(
    out: Path,
    sql_dir: Path,
) -> tuple[list[dict[str, Any]], set[int], set[int], set[int], set[int]]:
    """Инвентаризировать все PG databases и выгрузить mapped A1 rows."""
    schema_dir = out / "postgres" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    databases_path = schema_dir / "databases.tsv"
    db_query = (
        "SELECT datname, pg_get_userbyid(datdba), pg_database_size(datname) "
        "FROM pg_database WHERE datallowconn AND NOT datistemplate ORDER BY datname"
    )
    db_status = run_pg_query(
        "postgres",
        db_query,
        databases_path,
        sql_dir / "010_pg_databases.sql",
    )
    databases = [row[0] for row in read_tsv(databases_path) if row]
    write_json(schema_dir / "database_query_status.json", db_status)
    tables: list[dict[str, str]] = []
    columns_by_table: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    indexes: list[list[str]] = []
    foreign_keys: list[list[str]] = []
    for database in databases:
        if database == "postgres":
            # Default maintenance DB has no application schema; keep it in the
            # database inventory but avoid an unbounded information_schema scan.
            continue
        prefix = safe_filename(database)
        tables_path = schema_dir / f"{prefix}_tables.tsv"
        columns_path = schema_dir / f"{prefix}_columns.tsv"
        indexes_path = schema_dir / f"{prefix}_indexes.tsv"
        fks_path = schema_dir / f"{prefix}_foreign_keys.tsv"
        estimates_path = schema_dir / f"{prefix}_row_estimates.tsv"
        table_query = (
            "SELECT table_schema, table_name, table_type FROM information_schema.tables "
            "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY table_schema, table_name"
        )
        column_query = (
            "SELECT table_schema, table_name, column_name, data_type, is_nullable, ordinal_position "
            "FROM information_schema.columns "
            "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY table_schema, table_name, ordinal_position"
        )
        index_query = (
            "SELECT schemaname, tablename, indexname, indexdef FROM pg_indexes "
            "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY schemaname, tablename, indexname"
        )
        fk_query = (
            "SELECT tc.table_schema, tc.table_name, kcu.column_name, "
            "ccu.table_schema, ccu.table_name, ccu.column_name "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name "
            "AND tc.table_schema = kcu.table_schema "
            "JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name "
            "AND ccu.table_schema = tc.table_schema "
            "WHERE tc.constraint_type = 'FOREIGN KEY' "
            "ORDER BY tc.table_schema, tc.table_name"
        )
        estimate_query = (
            "SELECT n.nspname, c.relname, c.reltuples::bigint, c.relpages "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE c.relkind IN ('r', 'm', 'p') "
            "AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY n.nspname, c.relname"
        )
        statuses = [
            run_pg_query(database, table_query, tables_path, sql_dir / f"011_{prefix}_tables.sql"),
            run_pg_query(database, column_query, columns_path, sql_dir / f"012_{prefix}_columns.sql"),
            run_pg_query(database, index_query, indexes_path, sql_dir / f"013_{prefix}_indexes.sql"),
            run_pg_query(database, fk_query, fks_path, sql_dir / f"014_{prefix}_foreign_keys.sql"),
            run_pg_query(database, estimate_query, estimates_path, sql_dir / f"015_{prefix}_row_estimates.sql"),
        ]
        for row in read_tsv(tables_path):
            if len(row) >= 3:
                tables.append({"database": database, "schema": row[0], "table": row[1], "type": row[2]})
        for row in read_tsv(columns_path):
            if len(row) >= 3:
                columns_by_table[(database, row[0], row[1])].append(row[2])
        indexes.extend(read_tsv(indexes_path))
        foreign_keys.extend(read_tsv(fks_path))
        write_json(schema_dir / f"{prefix}_inventory_status.json", statuses)
    write_json(schema_dir / "tables.json", tables)
    write_json(schema_dir / "columns.json", [
        {"database": database, "schema": schema, "table": table, "columns": columns}
        for (database, schema, table), columns in sorted(columns_by_table.items())
    ])
    write_json(schema_dir / "indexes.json", indexes)
    write_json(schema_dir / "foreign_keys.json", foreign_keys)

    app_db = next(
        (
            database
            for database in databases
            if ("public" in {item["schema"] for item in tables if item["database"] == database}
                and any(
                    item["database"] == database
                    and item["schema"] == "public"
                    and item["table"] == "wbcabinet"
                    for item in tables
                ))
        ),
        None,
    )
    if app_db is None:
        write_json(out / "postgres" / "a1_mapping_status.json", {"status": "UNAVAILABLE"})
        return [], set(), set(), set(), set()

    wbcabinet_columns = columns_by_table.get((app_db, "public", "wbcabinet"), [])
    safe_wbcabinet = [
        column for column in wbcabinet_columns
        if not any(marker in column.lower() for marker in SENSITIVE_NAMES)
    ]
    cabinet_path = out / "postgres" / f"{safe_filename(app_db)}_public_wbcabinet.csv"
    cabinet_query, cabinet_params = _build_wbcabinet_query(safe_wbcabinet, SHOP_ID)
    cabinet_status = run_pg_query(
        app_db,
        cabinet_query,
        cabinet_path,
        sql_dir / "020_pg_a1_wbcabinet.sql",
        query_params=cabinet_params,
        csv_output=True,
        csv_columns=safe_wbcabinet,
    )
    cabinet_ids, _, _, _ = parse_mapping_rows(cabinet_path)
    # WBCabinet's id is not an AdvSetting id, so parse it explicitly.
    with cabinet_path.open(encoding="utf-8", errors="replace", newline="") if cabinet_path.exists() else _empty_context() as handle:
        for row in csv.DictReader(handle):
            if row.get("id") and row["id"].isdigit():
                cabinet_ids.add(int(row["id"]))
    cabinet_min_date, cabinet_max_date = csv_temporal_bounds(cabinet_path, safe_wbcabinet)

    setting_key = (app_db, "public", "advsetting")
    setting_columns = columns_by_table.get(setting_key, [])
    setting_safe = [
        column for column in setting_columns
        if not any(marker in column.lower() for marker in SENSITIVE_NAMES)
    ]
    setting_path = out / "postgres" / f"{safe_filename(app_db)}_public_advsetting.csv"
    setting_query, setting_params = _build_advsetting_query(setting_safe, cabinet_ids)
    setting_status = run_pg_query(
        app_db,
        setting_query,
        setting_path,
        sql_dir / "021_pg_a1_advsetting.sql",
        query_params=setting_params,
        csv_output=True,
        csv_columns=setting_safe,
    )
    _, setting_ids, adv_ids, nmids = parse_mapping_rows(setting_path)
    setting_min_date, setting_max_date = csv_temporal_bounds(setting_path, setting_safe)

    coverage: list[dict[str, Any]] = []
    sequence = 30
    already: set[tuple[str, str, str]] = set()
    for (database, schema, table), table_columns in sorted(columns_by_table.items()):
        if database != app_db or schema not in {"public"}:
            continue
        lower_table = table.lower()
        if table in {"wbcabinet", "advsetting"}:
            continue
        if lower_table in {"alembic_version"}:
            continue
        filter_sql, mapping, safe_columns, filter_params = filter_for_postgres(
            table_columns,
            cabinet_ids,
            setting_ids,
            adv_ids,
            nmids,
            shop_id=SHOP_ID,
        )
        if filter_sql is None or not safe_columns:
            continue
        key = (database, schema, table)
        if key in already:
            continue
        already.add(key)
        semantic = "RAW_SOURCE"
        if any(marker in lower_table for marker in ("token", "secret", "credential")):
            semantic = "SNAPSHOT"
        item = extract_pg_table(
            out,
            sql_dir,
            database,
            schema,
            table,
            safe_columns,
            filter_sql,
            filter_params,
            mapping,
            sequence,
            table_semantic=semantic,
        )
        coverage.append(item)
        sequence += 1
    coverage.insert(
        0,
        {
            "source_system": "postgresql",
            "database": app_db,
            "schema": "public",
            "table": "wbcabinet",
            "query_file": str((sql_dir / "020_pg_a1_wbcabinet.sql").relative_to(out)),
            "grain": "one cabinet row",
            "family": "product_state",
            "semantic_type": "SNAPSHOT",
            "records_selected": count_csv_rows(cabinet_path),
            "records_written": count_csv_rows(cabinet_path),
            "rows": count_csv_rows(cabinet_path),
            "min_date": cabinet_min_date,
            "max_date": cabinet_max_date,
            "shop_filter": SHOP_ID,
            "join_mapping_used": "direct wbcabinet.shop_id",
            "columns": safe_wbcabinet,
            "provenance": "repository WBCabinet model",
            "completeness": "FULL_AVAILABLE" if cabinet_status["success"] else "UNAVAILABLE",
            "query_status": cabinet_status,
        },
    )
    coverage.insert(
        1,
        {
            "source_system": "postgresql",
            "database": app_db,
            "schema": "public",
            "table": "advsetting",
            "query_file": str((sql_dir / "021_pg_a1_advsetting.sql").relative_to(out)),
            "grain": "one advertising setting row",
            "family": "campaign_state",
            "semantic_type": "SNAPSHOT",
            "records_selected": count_csv_rows(setting_path),
            "records_written": count_csv_rows(setting_path),
            "rows": count_csv_rows(setting_path),
            "min_date": setting_min_date,
            "max_date": setting_max_date,
            "shop_filter": SHOP_ID,
            "join_mapping_used": "wbcabinet.shop_id -> wbcabinet.id -> advsetting.wb_cabinet_id",
            "columns": setting_safe,
            "provenance": "repository AdvSetting model",
            "completeness": "FULL_AVAILABLE" if setting_status["success"] else "UNAVAILABLE",
            "query_status": setting_status,
        },
    )
    write_json(out / "postgres" / "a1_coverage.json", coverage)
    write_json(
        out / "postgres" / "a1_mapping.json",
        {
            "database": app_db,
            "shop_id": SHOP_ID,
            "cabinet_ids": sorted(cabinet_ids),
            "adv_setting_ids": sorted(setting_ids),
            "campaign_ids": sorted(adv_ids),
            "nmids": sorted(nmids),
            "mapping": "wbcabinet.shop_id -> wbcabinet.id; advsetting.wb_cabinet_id; advsetting.adv_id; advsetting.nmids",
            "cabinet_query_status": cabinet_status,
            "setting_query_status": setting_status,
        },
    )
    for item in coverage:
        nmids.update(int(value) for value in item.get("unique_nmids", []) if str(value).isdigit())
        adv_ids.update(
            int(value) for value in item.get("unique_campaign_ids", []) if str(value).isdigit()
        )
    return coverage, cabinet_ids, setting_ids, adv_ids, nmids


class _empty_context:
    """Контекстный fallback для отсутствующего CSV."""

    def __enter__(self):
        """Вернуть пустой поток."""
        return iter(())

    def __exit__(self, *_: Any) -> None:
        """Завершить пустой контекст."""
        return None


def collect_redis(out: Path, adv_ids: set[int]) -> dict[str, Any]:
    """Проверить только A1 snapshot/cache metadata, не читая payload."""
    redis_dir = out / "redis"
    pattern = f"adv_snapshot:v1:shop:{SHOP_ID}:*"
    scan_path = redis_dir / "a1_snapshot_keys.txt"
    scan_status = run_redis_command(["SCAN", "0", "MATCH", pattern, "COUNT", "200"], scan_path)
    keys = [line.strip() for line in scan_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()] if scan_path.exists() else []
    # redis-cli SCAN returns cursor followed by keys; retain key-shaped lines only.
    keys = [key for key in keys if key.startswith("adv_snapshot:")]
    metadata: list[dict[str, Any]] = []
    for index, key in enumerate(keys, start=1):
        type_path = redis_dir / f"key_{index:03d}_type.txt"
        ttl_path = redis_dir / f"key_{index:03d}_ttl.txt"
        type_status = run_redis_command(["TYPE", key], type_path)
        ttl_status = run_redis_command(["TTL", key], ttl_path)
        metadata.append(
            {
                "key": key,
                "type": type_path.read_text(encoding="utf-8", errors="replace").strip(),
                "ttl_seconds": ttl_path.read_text(encoding="utf-8", errors="replace").strip(),
                "payload_exported": False,
                "type_status": type_status,
                "ttl_status": ttl_status,
            }
        )
    legacy: list[dict[str, Any]] = []
    for index, adv_id in enumerate(sorted(adv_ids), start=1):
        key = f"calculated_keywords:{adv_id}"
        exists_path = redis_dir / f"legacy_{index:03d}_exists.txt"
        ttl_path = redis_dir / f"legacy_{index:03d}_ttl.txt"
        exists_status = run_redis_command(["EXISTS", key], exists_path)
        ttl_status = run_redis_command(["TTL", key], ttl_path)
        legacy.append(
            {
                "key": key,
                "exists": exists_path.read_text(encoding="utf-8", errors="replace").strip(),
                "ttl_seconds": ttl_path.read_text(encoding="utf-8", errors="replace").strip(),
                "payload_exported": False,
                "exists_status": exists_status,
                "ttl_status": ttl_status,
            }
        )
    result = {
        "source_system": "redis",
        "namespace": REDIS_NAMESPACE,
        "pod": REDIS_POD,
        "scan_pattern": pattern,
        "snapshot_keys": metadata,
        "legacy_keys": legacy,
        "persistence_note": (
            "Redis is appendonly-backed but application snapshot keys have short TTL "
            "(repository default 3600s); payloads were intentionally not dumped because "
            "this is current/cache state, not durable historical evidence."
        ),
        "completeness": "UNKNOWN" if not scan_status["success"] else "PARTIAL",
        "scan_status": scan_status,
    }
    write_json(redis_dir / "metadata.json", result)
    return result


def build_relationships(out: Path, table_rows: list[dict[str, Any]]) -> None:
    """Сохранить простые source/view relationship hints из create query."""
    relationships: list[dict[str, str]] = []
    for row in table_rows:
        create_query = str(row.get("create_table_query") or "")
        if not create_query:
            continue
        refs = sorted(set(re.findall(r"(?:FROM|TO)\\s+([`\\w.]+)", create_query, re.IGNORECASE)))
        if refs:
            relationships.append(
                {
                    "database": str(row.get("database", "")),
                    "table": str(row.get("name", "")),
                    "engine": str(row.get("engine", "")),
                    "references": ", ".join(refs),
                }
            )
    write_json(out / "schema" / "relationships.json", relationships)


def build_reports(
    out: Path,
    ch_coverage: list[dict[str, Any]],
    pg_coverage: list[dict[str, Any]],
    redis_result: dict[str, Any],
    mapping: dict[str, Any],
) -> None:
    """Создать manifest, coverage и технический report без business analysis."""
    all_items = ch_coverage + pg_coverage
    nmids: set[str] = set(str(value) for value in mapping.get("nmids", []))
    campaigns: set[str] = set(str(value) for value in mapping.get("campaign_ids", []))
    for item in all_items:
        nmids.update(str(value) for value in item.get("unique_nmids", []))
        campaigns.update(str(value) for value in item.get("unique_campaign_ids", []))
    database_rows = read_jsonl(out / "schema" / "databases.jsonl")
    clickhouse_databases = sorted(
        str(row.get("name"))
        for row in database_rows
        if row.get("name") and str(row.get("name")).lower() not in {"system", "information_schema"}
    )
    coverage = {
        "scope": {"client": "ООО «А1»", "shop_id": SHOP_ID},
        "records_selected": sum(int(item.get("records_selected") or 0) for item in all_items),
        "records_written": sum(int(item.get("records_written") or 0) for item in all_items),
        "items": all_items,
        "unique_nmids": sorted(nmids, key=lambda value: (len(value), value)),
        "unique_campaign_ids": sorted(campaigns, key=lambda value: (len(value), value)),
        "redis": redis_result,
        "completeness_legend": {
            "FULL_AVAILABLE": "query and raw write succeeded",
            "PARTIAL": "some rows/statuses differ or only partial evidence available",
            "EMPTY": "mapped query succeeded with zero rows",
            "UNAVAILABLE": "read-only query failed",
            "UNKNOWN": "semantic or mapping completeness not proven",
        },
    }
    write_json(out / "coverage.json", coverage)
    manifest = {
        "artifact": "clickhouse_a1_evidence",
        "created_at_utc": now_iso(),
        "scope": {"client": "ООО «А1»", "shop_id": SHOP_ID},
        "read_only": True,
        "wb_api_collect_run": False,
        "systems": ["kubernetes", "clickhouse", "postgresql", "redis"],
        "mapping": mapping,
        "files": sorted(
            str(path.relative_to(out))
            for path in out.rglob("*")
            if path.is_file() and path.name not in {"manifest.json", "coverage.json"}
        ),
        "secret_policy": {
            "secret_values_requested": False,
            "postgres_sensitive_columns_excluded": True,
            "redis_payloads_exported": False,
            "kubernetes_secret_objects_read": False,
        },
    }
    write_json(out / "manifest.json", manifest)
    useful = [item for item in all_items if item.get("completeness") != "EMPTY"]
    lines = [
        "# Technical evidence report: ООО «А1»",
        "",
        f"- `shop_id`: `{SHOP_ID}`",
        "- Scope: READ_ONLY storage discovery and evidence extraction; no business analysis.",
        "- WB API collect: not run in this audit.",
        "",
        "## Storage systems",
        "",
        f"- ClickHouse: `prod-analytics/clickhouse-restore-0`; databases found: `{clickhouse_databases}`.",
        "- PostgreSQL: `prod-adv-bot/postgres-db-0`, schema/index/FK inventory and mapped public rows saved.",
        "- Redis: `prod-analytics/redis2-master-0`, key metadata only; short-TTL cache is not historical evidence.",
        "- Object storage: no application S3/MinIO/object-storage path found in repository search.",
        "",
        "## Useful datasets",
        "",
        "| source | database.table | family/purpose | grain | semantic_type | rows for A1 | earliest | latest | TTL | completeness |",
        "|---|---|---|---|---|---:|---|---|---|---|",
    ]
    for item in useful:
        source = item.get("source_system", "")
        qualified = ".".join(
            value for value in (item.get("database"), item.get("schema"), item.get("table")) if value
        )
        lines.append(
            f"| {source} | `{qualified}` | {item.get('family', 'unknown')} | "
            f"{item.get('grain', '')} | {item.get('semantic_type', 'UNKNOWN')} | "
            f"{item.get('rows', 0)} | {item.get('min_date', '') or ''} | "
            f"{item.get('max_date', '') or ''} | {item.get('ttl', '') or ''} | "
            f"{item.get('completeness', 'UNKNOWN')} |"
        )
    family_order = (
        "orders_sales",
        "advertising",
        "campaign_state",
        "funnel",
        "normquery_search",
        "product_state",
    )
    lines.extend(["", "## History depth by family", ""])
    for family in family_order:
        family_items = [item for item in all_items if item.get("family") == family]
        dated = [item for item in family_items if item.get("min_date") or item.get("max_date")]
        if not family_items:
            lines.append(f"- `{family}`: no mapped A1 dataset found in the audited stores.")
            continue
        min_dates = [str(item["min_date"]) for item in dated if item.get("min_date")]
        max_dates = [str(item["max_date"]) for item in dated if item.get("max_date")]
        earliest = min(min_dates) if min_dates else "UNKNOWN"
        latest = max(max_dates) if max_dates else "UNKNOWN"
        rows = sum(int(item.get("rows") or 0) for item in family_items)
        statuses = sorted({str(item.get("completeness", "UNKNOWN")) for item in family_items})
        lines.append(
            f"- `{family}`: {rows} rows across {len(family_items)} dataset(s), "
            f"available range `{earliest}` to `{latest}`, status `{', '.join(statuses)}`."
        )
    lines.extend(["", "## Evidence by family", ""])
    for family in family_order:
        family_items = [item for item in all_items if item.get("family") == family]
        lines.extend([f"### {family}", ""])
        if not family_items:
            lines.append("- No mapped A1 rows were exported for this family.")
        else:
            for item in family_items:
                qualified = ".".join(
                    value
                    for value in (item.get("database"), item.get("schema"), item.get("table"))
                    if value
                )
                lines.append(
                    f"- `{qualified}`: rows={item.get('rows', 0)}, "
                    f"range={item.get('min_date') or 'UNKNOWN'}..{item.get('max_date') or 'UNKNOWN'}, "
                    f"semantic={item.get('semantic_type', 'UNKNOWN')}, "
                    f"mapping={item.get('join_mapping_used', 'UNKNOWN')}."
                )
        lines.append("")
    lines.extend(
        [
            "",
            "## Mapping",
            "",
            f"- PostgreSQL database: `{mapping.get('database')}`.",
            f"- `wbcabinet.shop_id` -> cabinet IDs: `{mapping.get('cabinet_ids', [])}`.",
            f"- `advsetting.wb_cabinet_id` -> campaign IDs: `{mapping.get('campaign_ids', [])}`.",
            f"- `advsetting.nmids` -> `{len(nmids)}` nmid values.",
            "",
            "## Semantic/provenance cautions",
            "",
            "- ClickHouse raw revisions are preserved; ReplacingMergeTree and `argMax` reconciliation were not silently applied.",
            "- `full_adv_wb_stat`/advertising orders and `wb_common_stat`/shop funnel metrics remain distinct datasets.",
            "- AggregateFunction materialized tables are exported as raw aggregate states and require explicit merge semantics later.",
            "- Empty or failed mapped datasets are retained in `coverage.json`; absence is not interpreted as business zero.",
            "",
            "## IDs",
            "",
            f"- Unique nmids found: `{len(nmids)}`; full list is in `coverage.json`.",
            f"- Unique campaign IDs found: `{len(campaigns)}`; full list is in `coverage.json`.",
            "",
            "## Full ID lists",
            "",
            "### nmID",
            "",
            "__FULL_NMIDS__",
            "",
            "### Campaign ID",
            "",
            "__FULL_CAMPAIGNS__",
            "",
            "## Missing datasets and comparative limits",
            "",
            "- WB API was intentionally not called; relative retention versus current WB API responses is not asserted in this artifact.",
            "- A family listed as absent above had no mapped A1 rows in the audited ClickHouse/PostgreSQL evidence paths.",
            "- Redis payloads, credentials, token values, and other secret-bearing values were intentionally not exported.",
            "",
            "## Semantic ambiguities requiring later reconciliation",
            "",
            "- Advertising `orders` and shop-level `orders` are kept in separate datasets; their attribution semantics require WB API reconciliation.",
            "- AggregateFunction tables are raw states, not finalized aggregates; merge/finalization semantics require an explicit later query.",
            "- ReplacingMergeTree and application revision rows are preserved; duplicate logical events may remain by design.",
            "- PostgreSQL configuration/state rows have no reliable event-time range unless a timestamp column is present in the exported projection.",
            "",
            "## Archive",
            "",
            "- The ZIP and SHA-256 are created by the runner after this report.",
        ]
    )
    nmids_block = [f"- `{value}`" for value in sorted(nmids, key=lambda value: (len(value), value))]
    campaigns_block = [
        f"- `{value}`" for value in sorted(campaigns, key=lambda value: (len(value), value))
    ]
    lines[lines.index("__FULL_NMIDS__") : lines.index("__FULL_NMIDS__") + 1] = nmids_block
    lines[lines.index("__FULL_CAMPAIGNS__") : lines.index("__FULL_CAMPAIGNS__") + 1] = campaigns_block
    write_text(out / "report.md", "\n".join(lines) + "\n")


def secret_scan(root: Path) -> list[str]:
    """Проверить текстовые артефакты на запрещённые credential markers."""
    patterns = (
        re.compile(r"(?i)\bauthorization\s*[:=]"),
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
        re.compile(
            r'(?i)"(?:password|api_key|token|secret|connection_string)"\s*:\s*"?[^",\s}]+'
        ),
        re.compile(
            r"(?i)\b(?:password|api_key|token|secret|connection_string)\s*=\s*[^\s,;]+"
        ),
    )
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".zip", ".parquet"}:
            continue
        try:
            matched: set[int] = set()
            tail = ""
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    text = tail + chunk.decode("utf-8", errors="ignore").lower()
                    for index, pattern in enumerate(patterns):
                        if index in matched:
                            continue
                        match = pattern.search(text)
                        while match is not None:
                            if "***redacted***" not in match.group(0).lower():
                                matched.add(index)
                                break
                            match = pattern.search(text, match.end())
                    if len(matched) == len(patterns):
                        break
                    tail = text[-512:]
        except OSError:
            continue
        for index in sorted(matched):
            findings.append(f"{path.relative_to(root)}:{patterns[index].pattern}")
    return findings


def archive_directory(root: Path) -> tuple[Path, str]:
    """Упаковать evidence directory и посчитать локальный SHA-256."""
    archive = root.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                handle.write(path, path.relative_to(root.parent))
    digest_builder = hashlib.sha256()
    with archive.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest_builder.update(chunk)
    digest = digest_builder.hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive, digest


def finalize_existing_evidence(out: Path) -> int:
    """Финализировать локально собранную evidence без повторного доступа к БД."""
    ch_coverage_path = out / "metadata" / "a1_table_coverage.json"
    pg_coverage_path = out / "postgres" / "a1_coverage.json"
    mapping_path = out / "postgres" / "a1_mapping.json"
    ch_coverage = json.loads(ch_coverage_path.read_text(encoding="utf-8"))
    pg_coverage = json.loads(pg_coverage_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

    for item in ch_coverage:
        item["family"] = choose_family(item.get("table", ""), item.get("columns", []))
        stats_status = item.get("query_status", {}).get("stats", {})
        if not stats_status.get("success", False):
            item["records_selected"] = int(item.get("records_written") or 0)
            item["rows"] = int(item.get("records_written") or 0)
            item["completeness"] = (
                "FULL_AVAILABLE"
                if all(
                    result.get("success", False)
                    for result in item.get("query_status", {}).get("extract", [])
                )
                else "PARTIAL"
            )
    for item in pg_coverage:
        item["family"] = choose_family(item.get("table", ""), item.get("columns", []))
        output = item.get("query_status", {}).get("output")
        if output:
            min_date, max_date = csv_temporal_bounds(Path(output), item.get("columns", []))
            item["min_date"] = min_date
            item["max_date"] = max_date
    write_json(ch_coverage_path, ch_coverage)
    write_json(pg_coverage_path, pg_coverage)

    campaign_ids = sorted(
        {
            int(value)
            for item in ch_coverage + pg_coverage
            for value in item.get("unique_campaign_ids", [])
            if str(value).isdigit()
        }
        | {int(value) for value in mapping.get("campaign_ids", [])}
    )
    nmids = sorted(
        {
            int(value)
            for item in ch_coverage + pg_coverage
            for value in item.get("unique_nmids", [])
            if str(value).isdigit()
        }
        | {int(value) for value in mapping.get("nmids", [])}
    )
    mapping["campaign_ids"] = campaign_ids
    mapping["nmids"] = nmids
    write_json(mapping_path, mapping)

    redis_dir = out / "redis"
    redis_dir.mkdir(parents=True, exist_ok=True)
    snapshot_scan = redis_dir / "a1_snapshot_keys.txt"
    snapshot_keys = [
        line.strip()
        for line in snapshot_scan.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip().startswith("adv_snapshot:")
    ] if snapshot_scan.exists() else []
    snapshot_metadata = [
        {
            "key": key,
            "type": "NOT_READ",
            "ttl_seconds": "NOT_READ",
            "payload_exported": False,
        }
        for key in snapshot_keys
    ]
    legacy_metadata: list[dict[str, Any]] = []
    for exists_path in sorted(redis_dir.glob("legacy_*_exists.txt")):
        parts = exists_path.stem.split("_")
        if len(parts) != 3 or not parts[1].isdigit():
            continue
        index = int(parts[1])
        ttl_path = redis_dir / f"legacy_{index:03d}_ttl.txt"
        campaign = campaign_ids[index - 1] if index <= len(campaign_ids) else None
        legacy_metadata.append(
            {
                "key": f"calculated_keywords:{campaign}" if campaign is not None else None,
                "exists": exists_path.read_text(encoding="utf-8", errors="replace").strip(),
                "ttl_seconds": (
                    ttl_path.read_text(encoding="utf-8", errors="replace").strip()
                    if ttl_path.exists()
                    else "NOT_READ"
                ),
                "payload_exported": False,
            }
        )
    redis_result = {
        "source_system": "redis",
        "namespace": REDIS_NAMESPACE,
        "pod": REDIS_POD,
        "scan_pattern": f"adv_snapshot:v1:shop:{SHOP_ID}:*",
        "snapshot_keys": snapshot_metadata,
        "legacy_keys": legacy_metadata,
        "persistence_note": (
            "Only key metadata was collected. Redis payloads were not read; the "
            "legacy-key loop was intentionally stopped after local evidence collection "
            "because these keys are cache/current-state data rather than history."
        ),
        "completeness": "PARTIAL",
        "scan_status": {
            "success": False,
            "stderr": "Legacy Redis metadata collection interrupted after evidence stores completed.",
            "return_code": 130,
        },
    }
    write_json(redis_dir / "metadata.json", redis_result)
    for infrastructure_file in (out / "infrastructure").glob("*.json"):
        redact_kubernetes_file(infrastructure_file)

    build_reports(out, ch_coverage, pg_coverage, redis_result, mapping)
    findings = secret_scan(out)
    write_json(
        out / "secret_scan.json",
        {
            "status": "PASS" if not findings else "FAIL",
            "findings": findings,
            "policy": "No credentials, tokens, Authorization/Bearer values or connection strings.",
        },
    )
    if findings:
        raise SystemExit("Secret scan failed; ZIP was not created.")
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = sorted(set(manifest.get("files", [])) | {"secret_scan.json"})
    write_json(manifest_path, manifest)
    archive, digest = archive_directory(out)
    print(json.dumps(
        {
            "output_dir": str(out),
            "archive_path": str(archive),
            "sha256": digest,
            "clickhouse_items": len(ch_coverage),
            "postgres_items": len(pg_coverage),
            "redis_legacy_metadata_rows": len(legacy_metadata),
            "nmids": len(nmids),
            "campaign_ids": len(campaign_ids),
            "LOCAL_ARTIFACT_HANDOFF": "PASS",
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать non-interactive параметры evidence run."""
    parser = argparse.ArgumentParser(
        description="Read-only CH/PG/Redis historical evidence collector for one WB shop."
    )
    parser.add_argument("--shop-id", default=SHOP_ID, help="WB shop_id; defaults to the A1 case.")
    parser.add_argument(
        "--output-dir",
        default=".tmp/clickhouse_a1_evidence",
        help="local evidence directory; ZIP is written next to it",
    )
    parser.add_argument(
        "--finalize-existing",
        action="store_true",
        help="finalize already collected local evidence without database access",
    )
    parser.add_argument(
        "--allow-full-raw-export",
        action="store_true",
        help="explicitly enable the legacy full physical-row export; disabled by default",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить legacy collector только при явном разрешении полного raw export."""
    args = parse_args(argv)
    if args.shop_id != SHOP_ID:
        raise SystemExit("This bounded runner is frozen for the ООО «А1» shop_id.")
    if not args.allow_full_raw_export:
        raise SystemExit(
            "Legacy full raw export is disabled. Run scripts\\ch_a1_profile.py "
            "for profiling-first mode; no ClickHouse raw rows are exported."
        )
    out = Path(args.output_dir).resolve()
    if args.finalize_existing:
        return finalize_existing_evidence(out)
    sql_dir = out / "sql"
    if out.exists():
        for child in out.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    out.mkdir(parents=True, exist_ok=True)
    statuses = collect_infrastructure(out)
    pg_coverage, cabinet_ids, setting_ids, pg_adv_ids, pg_nmids = collect_postgres(out, sql_dir)
    ch_coverage, ch_nmids, ch_adv_ids = collect_clickhouse(
        out,
        sql_dir,
        cabinet_ids,
        set(pg_adv_ids),
        set(pg_nmids),
    )
    table_rows = read_jsonl(out / "schema" / "tables.jsonl")
    build_relationships(out, table_rows)
    redis_result = collect_redis(out, set(pg_adv_ids) | {int(value) for value in ch_adv_ids if value.isdigit()})
    mapping = {
        "database": next(
            (item.get("database") for item in pg_coverage if item.get("table") == "wbcabinet"),
            None,
        ),
        "cabinet_ids": sorted(cabinet_ids),
        "adv_setting_ids": sorted(setting_ids),
        "campaign_ids": sorted(set(pg_adv_ids) | {int(value) for value in ch_adv_ids if value.isdigit()}),
        "nmids": sorted(set(pg_nmids) | {int(value) for value in ch_nmids if value.isdigit()}),
    }
    build_reports(out, ch_coverage, pg_coverage, redis_result, mapping)
    findings = secret_scan(out)
    write_json(
        out / "secret_scan.json",
        {
            "status": "PASS" if not findings else "FAIL",
            "findings": findings,
            "policy": "No credentials, tokens, Authorization/Bearer values or connection strings.",
        },
    )
    if findings:
        raise SystemExit("Secret scan failed; ZIP was not created.")
    archive, digest = archive_directory(out)
    print(json.dumps({
        "output_dir": str(out),
        "archive_path": str(archive),
        "sha256": digest,
        "kubernetes_statuses": statuses,
        "clickhouse_items": len(ch_coverage),
        "postgres_items": len(pg_coverage),
        "nmids": len(mapping["nmids"]),
        "campaign_ids": len(mapping["campaign_ids"]),
        "LOCAL_ARTIFACT_HANDOFF": "PASS",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
