"""READ_ONLY raw collector for WB v3 associated-conversion evidence.

Модуль использует существующий DI/auth/client path приложения, но намеренно не
вызывает ``FullAdvStat`` mapper: его ``DayStats`` теряет ``apps[].nms[]``.
Сначала сохраняется raw response v3 и конфигурация v2, затем локально строятся
nm-level attribution, decomposition и точное reconciliation с day totals.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import shutil
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import dotenv

dotenv.load_dotenv()

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
BEGIN_DATE = date(2026, 7, 1)
END_DATE = date(2026, 8, 22)
EVIDENCE_ROOT = Path(".tmp/clickhouse_a1_evidence_run9")


def _jsonable(value: Any) -> Any:
    """Рекурсивно привести attrs/model payload к JSON-совместимому виду."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date,)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if hasattr(value, "value"):
        return _jsonable(value.value)
    return str(value)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Записать JSONL в стабильном UTF-8 формате."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_jsonable(row), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def _read_int(row: dict[str, Any], *names: str) -> int:
    """Взять первое числовое поле из вариантов API naming."""
    for name in names:
        value = row.get(name)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return 0


def _read_float(row: dict[str, Any], *names: str) -> float:
    """Взять первое числовое поле с плавающей точкой."""
    for name in names:
        value = row.get(name)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return 0.0


def _date_value(row: dict[str, Any]) -> str:
    """Нормализовать дату API до ISO date без потери исходного day значения."""
    value = row.get("date", "")
    return str(value)[:10]


def _nm_rows(raw_items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Развернуть только days/apps/nms и одновременно собрать day reconciliation."""
    nm_rows: list[dict[str, Any]] = []
    day_rows: list[dict[str, Any]] = []
    for item in raw_items:
        advert_id = _read_int(item, "advertId", "advert_id")
        days = item.get("days") if isinstance(item.get("days"), list) else []
        for day in days:
            if not isinstance(day, dict):
                continue
            day_date = _date_value(day)
            day_rows.append(
                {
                    "advert_id": advert_id,
                    "date": day_date,
                    "day_orders": _read_int(day, "orders"),
                    "day_sum_price": _read_float(day, "sum_price"),
                    "day_views": _read_int(day, "views"),
                    "day_clicks": _read_int(day, "clicks"),
                    "day_spend": _read_float(day, "sum", "spend"),
                }
            )
            apps = day.get("apps") if isinstance(day.get("apps"), list) else []
            for app in apps:
                if not isinstance(app, dict):
                    continue
                app_type = app.get("appType", app.get("app_type", ""))
                nms = app.get("nms") if isinstance(app.get("nms"), list) else []
                for nm in nms:
                    if not isinstance(nm, dict):
                        continue
                    nm_rows.append(
                        {
                            "advert_id": advert_id,
                            "date": day_date,
                            "app_type": app_type,
                            "ordered_nm_id": _read_int(nm, "nmId", "nmID", "nm_id", "id"),
                            "name": nm.get("name", ""),
                            "views": _read_int(nm, "views"),
                            "clicks": _read_int(nm, "clicks"),
                            "spend": _read_float(nm, "sum", "spend"),
                            "atbs": _read_int(nm, "atbs", "carts"),
                            "orders": _read_int(nm, "orders"),
                            "canceled": _read_int(nm, "canceled", "cancelled"),
                            "shks": _read_int(nm, "shks"),
                            "sum_price": _read_float(nm, "sum_price"),
                        }
                    )
    return nm_rows, day_rows


def _config_rows(configs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[int, set[int]]]:
    """Сохранить config v2 и построить promoted nmID mapping без эвристики."""
    rows: list[dict[str, Any]] = []
    promoted: dict[int, set[int]] = {}
    for raw in configs:
        advert_id = _read_int(raw, "id", "advertId", "advert_id")
        settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
        nm_settings = raw.get("nm_settings")
        if not isinstance(nm_settings, list):
            nm_settings = []
        nm_ids = {
            _read_int(item, "nm_id", "nmId", "nmID")
            for item in nm_settings
            if isinstance(item, dict)
        }
        nm_ids.discard(0)
        promoted[advert_id] = nm_ids
        rows.append(
            {
                "advert_id": advert_id,
                "campaign_name": settings.get("name", ""),
                "payment_type": settings.get("payment_type"),
                "placements": settings.get("placements"),
                "promoted_nm_ids": sorted(nm_ids),
                "raw_config": raw,
            }
        )
    return rows, promoted


def _derive(
    nm_rows: list[dict[str, Any]],
    day_rows: list[dict[str, Any]],
    promoted: dict[int, set[int]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Построить attribution, decomposition, diagnostic и reconciliation."""
    grouped: dict[tuple[str, int, int], dict[str, Any]] = {}
    for row in nm_rows:
        key = (row["date"], row["advert_id"], row["ordered_nm_id"])
        target = grouped.setdefault(
            key,
            {
                "date": row["date"],
                "advert_id": row["advert_id"],
                "ordered_nm_id": row["ordered_nm_id"],
                "views": 0,
                "clicks": 0,
                "spend": 0.0,
                "atbs": 0,
                "orders": 0,
                "canceled": 0,
                "shks": 0,
                "sum_price": 0.0,
            },
        )
        for field in ("views", "clicks", "spend", "atbs", "orders", "canceled", "shks", "sum_price"):
            target[field] += row[field]

    attribution = list(grouped.values())
    day_lookup: dict[tuple[int, str], dict[str, Any]] = {}
    for row in day_rows:
        day_lookup[(row["advert_id"], row["date"])] = row

    decomposition: list[dict[str, Any]] = []
    diagnostic: list[dict[str, Any]] = []
    by_day: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in attribution:
        by_day[(row["advert_id"], row["date"])].append(row)
    for key, rows in sorted(by_day.items()):
        advert_id, day_date = key
        promoted_ids = promoted.get(advert_id, set())
        direct_orders = sum(r["orders"] for r in rows if r["ordered_nm_id"] in promoted_ids)
        direct_sum = sum(r["sum_price"] for r in rows if r["ordered_nm_id"] in promoted_ids)
        non_orders = sum(r["orders"] for r in rows if r["ordered_nm_id"] not in promoted_ids)
        non_sum = sum(r["sum_price"] for r in rows if r["ordered_nm_id"] not in promoted_ids)
        total_orders = direct_orders + non_orders
        total_sum = direct_sum + non_sum
        spend = day_lookup.get(key, {}).get("day_spend")
        if spend is None:
            spend = sum(r["spend"] for r in rows)
        decomposition.append(
            {
                "advert_id": advert_id,
                "date": day_date,
                "spend": float(spend),
                "direct_orders": direct_orders,
                "direct_order_sum": direct_sum,
                "non_promoted_attributed_orders": non_orders,
                "non_promoted_attributed_order_sum": non_sum,
                "total_attributed_orders": total_orders,
                "total_attributed_order_sum": total_sum,
                "direct_cpo": float(spend) / direct_orders if direct_orders else None,
                "total_attributed_cpo": float(spend) / total_orders if total_orders else None,
                "non_promoted_order_share": non_orders / total_orders if total_orders else None,
                "non_promoted_gmv_share": non_sum / total_sum if total_sum else None,
            }
        )
        for row in rows:
            if row["ordered_nm_id"] not in promoted_ids:
                diagnostic.append(
                    {
                        "advert_id": advert_id,
                        "date": day_date,
                        "ordered_nm_id": row["ordered_nm_id"],
                        "views": row["views"],
                        "clicks": row["clicks"],
                        "spend": row["spend"],
                        "orders": row["orders"],
                    }
                )

    reconciliation: list[dict[str, Any]] = []
    nm_by_day: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in nm_rows:
        nm_by_day[(row["advert_id"], row["date"])].append(row)
    for key, day in sorted(day_lookup.items()):
        nm = nm_by_day.get(key, [])
        nm_orders = sum(row["orders"] for row in nm)
        nm_sum = sum(row["sum_price"] for row in nm)
        orders_match = nm_orders == day["day_orders"]
        sum_match = abs(nm_sum - day["day_sum_price"]) < 1e-6
        reconciliation.append(
            {
                "advert_id": key[0],
                "date": key[1],
                "day_orders": day["day_orders"],
                "nm_orders": nm_orders,
                "orders_match": orders_match,
                "day_sum_price": day["day_sum_price"],
                "nm_sum_price": nm_sum,
                "sum_price_match": sum_match,
                "pass": orders_match and sum_match,
            }
        )
    return attribution, decomposition, diagnostic, {
        "checks": reconciliation,
        "pass": all(row["pass"] for row in reconciliation),
        "checked_days": len(reconciliation),
        "failed_days": sum(not row["pass"] for row in reconciliation),
    }


def _sha256(path: Path) -> str:
    """Посчитать SHA256 файла потоково."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files_manifest(root: Path) -> list[dict[str, Any]]:
    """Собрать размеры и SHA256 всех artifact files."""
    return [
        {
            "path": str(path.relative_to(root)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in {"manifest.json"}
    ]


async def _collect_api(output_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[int], list[int]]:
    """Получить all-campaign IDs, configs и raw v3 items через существующий auth."""
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.chunked import (
        run_chunked_single_range,
    )

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(SHOP_ID)
        client = hub.wb_data_manager.promotion_manager._client
        all_configs = await client.campaigns_info_v2_adapter.get_all_campaigns()
        api_ids = sorted({_read_int(item.to_dict(), "id") for item in all_configs})
        if not api_ids:
            api_ids = sorted(await client.promotion_count_adapter.get_cabinet_adv_ids())
            all_configs = await client.campaigns_info_v2_adapter.get_campaigns_info(api_ids)
        config_rows, _ = _config_rows([_jsonable(item.to_dict()) for item in all_configs])
        current_ids = _current_complex_adv_ids()
        raw_rows: list[dict[str, Any]] = []
        window_begin = BEGIN_DATE
        adapter = client.fullstats_adapter
        while window_begin <= END_DATE:
            window_end = min(window_begin + timedelta(days=30), END_DATE)

            async def fetcher(chunk: list[int], begin: date, end: date) -> list[Any]:
                return await adapter._request_chunk(chunk, begin, end)

            items = await run_chunked_single_range(api_ids, window_begin, window_end, fetcher)
            for item in items:
                raw = _jsonable(item.to_dict())
                raw["_evidence_request_begin"] = window_begin.isoformat()
                raw["_evidence_request_end"] = window_end.isoformat()
                raw_rows.append(raw)
            window_begin = window_end + timedelta(days=1)
            if window_begin <= END_DATE:
                await asyncio.sleep(20)
        return raw_rows, config_rows, api_ids, current_ids


def _current_complex_adv_ids() -> list[int]:
    """Прочитать current ComplexAdv coverage из уже безопасного A1 CSV."""
    source = EVIDENCE_ROOT / "postgres/adv_updater_public_advsetting.csv"
    if not source.exists():
        return []
    import csv

    result: list[int] = []
    with source.open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("bot_active", "").lower() == "true" and row.get("active_status") != "done":
                if row.get("adv_id"):
                    result.append(int(row["adv_id"]))
    return sorted(set(result))


def _load_envelopes(
    envelope_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[int], list[int]]:
    """Разделить захваченный из pod stdout на raw v3 и campaign config."""
    raw_items: list[dict[str, Any]] = []
    config_payloads: list[dict[str, Any]] = []
    with envelope_path.open(encoding="utf-8-sig", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            envelope = json.loads(line)
            if envelope.get("kind") == "campaign":
                payload = envelope.get("data")
                if isinstance(payload, dict):
                    config_payloads.append(payload)
            elif envelope.get("kind") == "fullstats":
                payload = envelope.get("data")
                if isinstance(payload, dict):
                    payload["_evidence_request_begin"] = envelope.get("request_begin")
                    payload["_evidence_request_end"] = envelope.get("request_end")
                    raw_items.append(payload)
    config_rows, _ = _config_rows(config_payloads)
    api_ids = sorted({row["advert_id"] for row in config_rows})
    return raw_items, config_rows, api_ids, _current_complex_adv_ids()


def run_export(output_dir: Path, envelope_path: Path | None = None) -> int:
    """Выполнить raw API collect, derived export, reconciliation и ZIP."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "raw").mkdir(parents=True)
    (output_dir / "derived").mkdir(parents=True)
    if envelope_path is None:
        raw_items, config_rows, api_ids, current_ids = asyncio.run(_collect_api(output_dir))
    else:
        raw_items, config_rows, api_ids, current_ids = _load_envelopes(envelope_path)
    _write_jsonl(output_dir / "raw/fullstats_v3_raw.jsonl", raw_items)
    _write_jsonl(output_dir / "raw/campaigns.jsonl", config_rows)
    nm_rows, day_rows = _nm_rows(raw_items)
    attribution, decomposition, diagnostic, reconciliation = _derive(
        nm_rows,
        day_rows,
        {
            row["advert_id"]: set(row["promoted_nm_ids"])
            for row in config_rows
        },
    )
    _write_jsonl(output_dir / "derived/campaign_nmid_day_attribution.jsonl", attribution)
    _write_jsonl(output_dir / "derived/campaign_day_attribution_decomposition.jsonl", decomposition)
    _write_jsonl(output_dir / "derived/non_promoted_diagnostic.jsonl", diagnostic)
    observed_dates = sorted(
        {
            row["date"]
            for row in day_rows
            if row.get("date")
        }
    )
    date_range = [observed_dates[0], observed_dates[-1]] if observed_dates else []
    secret_markers: list[str] = []
    for path in output_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in ("Authorization:", "Bearer ", "password=", "token="):
            if re.search(re.escape(marker), text, flags=re.IGNORECASE):
                secret_markers.append(f"{path.relative_to(output_dir)}:{marker}")
    if secret_markers:
        raise RuntimeError("Secret marker detected; artifact was not packaged.")
    (output_dir / "report.json").write_text(
        json.dumps(
            {
                "records_raw_fullstats_items": len(raw_items),
                "records_raw_nm_level": len(nm_rows),
                "records_derived_campaign_nmid_day": len(attribution),
                "records_derived_decomposition": len(decomposition),
                "records_non_promoted_diagnostic": len(diagnostic),
                "campaign_count": len(api_ids),
                "raw_date_range_requested": [BEGIN_DATE.isoformat(), END_DATE.isoformat()],
                "observed_date_range": date_range,
                "current_complex_adv_campaign_ids": current_ids,
                "reconciliation": reconciliation,
                "coverage_gaps": {
                    "current_complex_adv_missing_from_api_campaigns": sorted(set(current_ids) - set(api_ids)),
                    "api_campaigns_without_config": sorted(set(api_ids) - {row["advert_id"] for row in config_rows}),
                },
                "classification_note": "NON_PROMOTED_ATTRIBUTED is not asserted to be pure associative conversion; combined-card reconciliation remains required.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    manifest = {
        "artifact": "associated_conversions_a1",
        "scope": {"shop_id": SHOP_ID, "client": "ООО «А1»"},
        "source": {
            "raw_fullstats": "GET /adv/v3/fullstats via existing FullstatsAdapter auth/client; raw mapper bypassed",
            "campaign_config": "GET /api/advert/v2/adverts via existing CampaignsInfoV2Adapter",
            "period": [BEGIN_DATE.isoformat(), END_DATE.isoformat()],
        },
        "read_only": True,
        "wb_mutations": False,
        "campaign_count": len(api_ids),
        "current_complex_adv_campaign_ids": current_ids,
        "observed_date_range": date_range,
        "reconciliation": reconciliation,
        "secret_scan": "PASS",
        "files": _files_manifest(output_dir),
        "status": "COMPLETE",
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    archive = output_dir.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                handle.write(path, path.relative_to(output_dir))
    digest = _sha256(archive)
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "artifact_dir": str(output_dir.resolve()),
                "archive": str(archive.resolve()),
                "sha256": digest,
                "reconciliation_pass": reconciliation["pass"],
                "campaign_count": len(api_ids),
                "records_raw_nm_level": len(nm_rows),
                "records_derived": len(attribution),
                "LOCAL_ARTIFACT_HANDOFF": "PASS",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать non-interactive параметры collector."""
    parser = argparse.ArgumentParser(description="READ_ONLY A1 associated conversions evidence.")
    parser.add_argument("--output-dir", default=".tmp/associated_conversions_a1")
    parser.add_argument("--envelope", help="Use stdout captured from an authenticated application pod.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить READ_ONLY raw/derived export."""
    args = parse_args(argv)
    envelope = Path(args.envelope).resolve() if args.envelope else None
    return run_export(Path(args.output_dir).resolve(), envelope)


if __name__ == "__main__":
    raise SystemExit(main())
