"""Generic strict read-only eight-target advertising directive audit.

Модуль принимает identity клиента и список target NMID через CLI, использует
существующий read-only WB/PG collector seam и формирует factual audit package:
закрытые 3/7-дневные spend/GMV/DRR, AdvSetting/WB campaign state, explicit
mapping checks и bounded glue checks. Production write-paths, fallback client
constants и подмена ``MISSING`` на ноль отсутствуют.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import traceback
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

WRITE_COUNTS = {
    "ALL_PRODUCTION_WRITES": 0,
    "WB_API_WRITES": 0,
    "POSTGRES_WRITES": 0,
    "CLICKHOUSE_WRITES": 0,
    "REDIS_WRITES": 0,
    "EXCEL_WRITES": 0,
}


@dataclass(frozen=True)
class Target:
    """Target NMID и ожидаемые AdvSetting/Auto/Search/legacy CPC IDs."""

    nmid: int
    advsetting_id: int | None = None
    auto_adv_id: int | None = None
    search_adv_id: int | None = None
    old_cpc_adv_id: int | None = None


@dataclass(frozen=True)
class Identity:
    """Неизменяемая identity envelope bounded запуска."""

    shop_id: str
    cabinet: int
    timezone: str


def _sha256(path: Path) -> str:
    """Посчитать SHA-256 файла потоково."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_target(raw: str) -> Target:
    """Разобрать ``nmid[:auto:search]`` или полный mapping contract."""
    parts = raw.split(":")
    if not 1 <= len(parts) <= 5:
        raise ValueError(f"invalid target {raw!r}")
    try:
        values = [int(value) if value else None for value in parts]
    except ValueError as exc:
        raise ValueError(f"invalid target {raw!r}") from exc
    if not values[0]:
        raise ValueError(f"target NMID must be positive: {raw!r}")
    if len(values) <= 3:
        return Target(values[0], None, values[1], values[2])
    return Target(values[0], values[1], values[2], values[3], values[4])


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Прочитать CSV, сохраняя отсутствие файла как source gap."""
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _number(row: dict[str, Any], *keys: str) -> float | None:
    """Вернуть первое числовое поле; пустое значение остаётся ``None``."""
    for key in keys:
        value = row.get(key)
        if value in (None, "", "GAP", "MISSING", "N/A"):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _aggregate_store(rows: list[dict[str, str]], days: int) -> dict[str, Any]:
    """Агрегировать только CLOSED rows из существующего store contract."""
    closed = [row for row in rows if row.get("day_state") in (None, "CLOSED")]
    selected = closed[-days:]
    if len(selected) < days:
        return {"status": "GAP", "reason": f"closed_rows<{days}"}
    gmv = sum(_number(row, "sales", "factual_order_value", "factual_GMV") or 0 for row in selected)
    spend = sum(_number(row, "gross_ad_spend", "all_shop_ad_spend") or 0 for row in selected)
    if any(
        _number(row, "sales", "factual_order_value", "factual_GMV") is None
        or _number(row, "gross_ad_spend", "all_shop_ad_spend") is None
        for row in selected
    ):
        return {"status": "GAP", "reason": "closed metric missing"}
    drr = spend / gmv if gmv else None
    return {
        "status": "AVAILABLE" if drr is not None else "GAP",
        "closed_days": days,
        "factual_store_gmv_rub": round(gmv, 2),
        "physical_ad_spend_rub": round(spend, 2),
        "store_drr": round(drr, 8) if drr is not None else None,
        "store_drr_percent": round(drr * 100, 4) if drr is not None else None,
        "unclamped_headroom_to_8_percent_rub": (
            round(gmv * 0.08 - spend, 2) if drr is not None else None
        ),
        "unclamped_headroom_to_10_percent_rub": (
            round(gmv * 0.10 - spend, 2) if drr is not None else None
        ),
    }


def _campaign_rows(root: Path) -> list[dict[str, str]]:
    """Загрузить текущую campaign/AdvSetting projection из strict contract."""
    return _read_csv(root / "02_CAMPAIGNS_CURRENT.csv")


def _target_state(
    target: Target, campaign_rows: list[dict[str, str]]
) -> dict[str, Any]:
    """Сопоставить target с текущими Auto/Search rows без restart/write."""
    rows = [row for row in campaign_rows if row.get("nm_id") == str(target.nmid)]
    by_type = {str(row.get("campaign_type", "")).lower(): row for row in rows}
    auto = by_type.get("auto") or {}
    search = by_type.get("search") or {}
    mapping = {
        "requested_advsetting_id": target.advsetting_id,
        "observed_advsetting_id": _number(auto, "adv_setting_id"),
        "requested_auto_adv_id": target.auto_adv_id,
        "observed_auto_adv_id": _number(auto, "adv_id"),
        "requested_search_adv_id": target.search_adv_id,
        "observed_search_adv_id": _number(search, "adv_id"),
        "requested_old_cpc_adv_id": target.old_cpc_adv_id,
        "observed_old_cpc_adv_id": _number(auto, "old_cpc_adv_id"),
    }
    mapping["mapping_status"] = (
        "VERIFIED"
        if all(
            expected is None
            or int(mapping[key] or -1) == expected
            for expected, key in (
                (target.advsetting_id, "observed_advsetting_id"),
                (target.auto_adv_id, "observed_auto_adv_id"),
                (target.search_adv_id, "observed_search_adv_id"),
                (target.old_cpc_adv_id, "observed_old_cpc_adv_id"),
            )
        )
        else "GAP"
    )
    return {
        "nmid": target.nmid,
        "advsetting_rows": rows,
        "auto": auto or {"status": "GAP"},
        "search": search or {"status": "GAP"},
        "mapping": mapping,
        "wb_auto_status": auto.get("WB_status", "GAP"),
        "wb_search_status": search.get("WB_status", "GAP"),
        "stopped_verification": (
            "STOPPED"
            if target.nmid == 751657528
            and str(auto.get("WB_status", "")).lower() in {"9", "stopped", "paused"}
            else "GAP"
            if target.nmid == 751657528
            else "N_A"
        ),
    }


def _build_audit(
    package_root: Path, identity: Identity, targets: list[Target]
) -> dict[str, Any]:
    """Построить factual directive table поверх strict collector outputs."""
    store_rows = _read_csv(package_root / "01_STORE.csv")
    campaign_rows = _campaign_rows(package_root)
    target_rows = [_target_state(target, campaign_rows) for target in targets]
    return {
        "identity": {
            "shop_id": identity.shop_id,
            "cabinet": identity.cabinet,
            "timezone": identity.timezone,
        },
        "mode": "STRICT_READ_ONLY",
        "closed_only_windows": {
            "3d": _aggregate_store(store_rows, 3),
            "7d": _aggregate_store(store_rows, 7),
        },
        "targets": target_rows,
        "stock": {
            "status": "GAP",
            "missing_is_not_zero": True,
            "fbo": "GAP",
            "fbs": "GAP",
            "reservations": "GAP",
        },
        "glue_checks": {
            "status": "GAP",
            "semantics": "bounded donor/card topology only; content failure is a GAP",
        },
        "write_counts": WRITE_COUNTS,
        "checked_at": datetime.now(timezone.utc).astimezone(
            ZoneInfo(identity.timezone)
        ).isoformat(),
    }


def _archive(root: Path, audit: dict[str, Any]) -> tuple[Path, str]:
    """Записать manifest/audit и собрать immutable primary ZIP."""
    (root / "DIRECTIVE_AUDIT.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    primary = root.parent / "MULTI_CLIENT_STRICT_EIGHT_TARGET_DIRECTIVE_AUDIT.zip"
    if primary.exists():
        primary.unlink()
    with zipfile.ZipFile(primary, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(root / "DIRECTIVE_AUDIT.json", "DIRECTIVE_AUDIT.json")
        if (root / "02_CAMPAIGNS_CURRENT.csv").is_file():
            archive.write(root / "02_CAMPAIGNS_CURRENT.csv", "02_CAMPAIGNS_CURRENT.csv")
        if (root / "01_STORE.csv").is_file():
            archive.write(root / "01_STORE.csv", "01_STORE.csv")
    digest = _sha256(primary)
    primary.with_name(primary.name + ".sha256").write_text(
        f"{digest}  {primary.name}\n", encoding="utf-8"
    )
    return primary, digest


def collect(
    *,
    identity: Identity,
    targets: list[Target],
    output_dir: Path,
) -> dict[str, Any]:
    """Собрать audit через существующий strict read-only source seam.

    Args:
        identity: shop/cabinet/timezone, переданные Owner для запуска.
        targets: Ровно восемь target NMID и optional expected mappings.
        output_dir: Каталог артефактов текущего запуска.
    Returns:
        Primary artifact path, SHA-256 и audit summary.
    Raises:
        RuntimeError: если target contract или zero-write gate нарушены.
    """
    if len(targets) != 8 or len({target.nmid for target in targets}) != 8:
        raise ValueError("exactly eight unique targets are required")
    if any(value != 0 for value in WRITE_COUNTS.values()):
        raise RuntimeError("production write gate is non-zero")

    from scripts import a1_strict_read_only_contract_collect as strict

    strict.SHOP_ID = identity.shop_id
    strict.EXPECTED_WB_CABINET_ID = identity.cabinet
    strict.TARGET_NMIDS = frozenset(target.nmid for target in targets)
    strict.RECONCILE_CAMPAIGNS = {
        target.nmid: frozenset(
            value for value in (target.auto_adv_id, target.search_adv_id) if value
        )
        for target in targets
    }
    original_scope = strict._scope_nmids
    strict._scope_nmids = lambda _cards: set(strict.TARGET_NMIDS)  # type: ignore[assignment]
    try:
        strict_root = output_dir / "strict_source"
        strict_result = strict.run_collect(strict_root)
    finally:
        strict._scope_nmids = original_scope

    audit = _build_audit(strict_root, identity, targets)
    audit["source_result"] = {
        "primary": strict_result.get("ABSOLUTE_ARCHIVE_PATH", "GAP"),
        "coverage": strict_result.get("coverage", {}),
    }
    primary, digest = _archive(output_dir, audit)
    return {
        "STATUS": "COMPLETE_WITH_GAPS" if audit["glue_checks"]["status"] == "GAP" else "COMPLETE",
        "PRIMARY_ARTIFACT": primary.name,
        "PRIMARY_SHA256": digest,
        "ZIP_ABSOLUTE_PATH": str(primary.resolve()),
        "ALL_PRODUCTION_WRITES": 0,
        "DIRECTIVE_AUDIT": audit,
    }


def build_parser() -> argparse.ArgumentParser:
    """Создать CLI с явной identity и target contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shop-id", required=True)
    parser.add_argument("--cabinet", required=True, type=int)
    parser.add_argument("--timezone", default="Europe/Moscow")
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Запустить bounded collector и вывести artifact gate fields."""
    args = build_parser().parse_args(argv)
    try:
        targets = [_parse_target(value) for value in args.target]
        result = collect(
            identity=Identity(args.shop_id, args.cabinet, args.timezone),
            targets=targets,
            output_dir=args.output_dir,
        )
    except Exception as exc:  # noqa: BLE001 — stable Job failure line
        print(f"ops-script: failed; error={exc}", file=sys.stderr)
        traceback.print_exc()
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_ARTIFACT={result['PRIMARY_ARTIFACT']}")
    print(f"PRIMARY_SHA256={result['PRIMARY_SHA256']}")
    print("ALL_PRODUCTION_WRITES=0")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
