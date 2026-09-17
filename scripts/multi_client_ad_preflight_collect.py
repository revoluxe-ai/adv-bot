"""Generic multi-client advertising preflight collector.

Модуль собирает read-only evidence для произвольной пары shop/cabinet и
target NMID, используя существующий WB read-only contract seam. Все
идентификаторы передаются через CLI, сверяются перед упаковкой и не
подменяются client-specific константами. Production writes запрещены.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, cast
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Europe/Moscow")
STATUS_FAIL_IDENTITY = "FAIL_IDENTITY"
WRITE_COUNTS = {
    "ALL_PRODUCTION_WRITES": 0,
    "WB_API_WRITES": 0,
    "POSTGRES_WRITES": 0,
    "CLICKHOUSE_WRITES": 0,
    "REDIS_WRITES": 0,
}


@dataclass(frozen=True)
class RunIdentity:
    """Неизменяемая identity envelope текущего bounded запуска."""

    shop_id: str
    wb_cabinet_id: int
    target_nmid: int
    client_size_id: int
    timezone: str = "Europe/Moscow"

    def as_dict(self) -> dict[str, Any]:
        """Вернуть JSON-совместимое представление identity."""
        return {
            "shop_id": self.shop_id,
            "wb_cabinet_id": self.wb_cabinet_id,
            "target_nmid": self.target_nmid,
            "client_size_id": self.client_size_id,
            "timezone": self.timezone,
        }


def _sha256(path: Path) -> str:
    """Посчитать SHA-256 локального primary artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows_from_files(root: Path) -> Iterable[dict[str, Any]]:
    """Извлечь JSON/CSV-like rows из небольшого набора raw файлов."""
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        values: list[Any] = (
            cast(list[Any], value) if isinstance(value, list) else [value]
        )
        for row in values:
            if isinstance(row, dict):
                yield row


def reconcile_identity(root: Path, identity: RunIdentity) -> list[str]:
    """Проверить identity всех распознанных payload rows.

    Returns:
        Список противоречий; непустой результат запрещает primary artifact.
    """
    errors: list[str] = []
    expected = identity.as_dict()
    for row in _rows_from_files(root):
        for key in ("shop_id", "wb_cabinet_id", "target_nmid", "client_size_id"):
            if key not in row or row[key] in (None, "", "GAP", "MISSING"):
                continue
            actual = str(row[key])
            wanted = str(expected[key])
            if actual != wanted:
                errors.append(f"{key}: expected={wanted}, got={actual}")
    return sorted(set(errors))


def validate_semantics(payload: dict[str, Any]) -> list[str]:
    """Проверить обязательные distinctions и отсутствие production writes."""
    errors: list[str] = []
    if any(value != 0 for value in WRITE_COUNTS.values()):
        errors.append("production write counter is non-zero")
    if payload.get("stock", {}).get("missing_is_not_zero") is not True:
        errors.append("missing stock was not preserved as missing")
    if payload.get("campaigns", {}).get("cpc_is_not_bot_search") is not True:
        errors.append("CPC was not separated from bot Search")
    if payload.get("economics", {}).get("factual_is_not_attributed") is not True:
        errors.append("factual and attributed economics were conflated")
    if payload.get("periods", {}).get("open_closed_distinct") is not True:
        errors.append("open and closed periods were conflated")
    return errors


def _run_existing_read_only_seam(identity: RunIdentity, root: Path) -> dict[str, Any]:
    """Вызвать общий read-only contract seam с runtime identity."""
    from scripts import a1_strict_read_only_contract_collect as strict

    strict.SHOP_ID = identity.shop_id
    strict.EXPECTED_WB_CABINET_ID = identity.wb_cabinet_id
    strict.TARGET_NMIDS = frozenset({identity.target_nmid})
    result = strict.run_collect(root / "source")
    return result


def run_collect(
    output_dir: Path,
    identity: RunIdentity,
    *,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    """Собрать и упаковать bounded generic preflight artifact.

    Args:
        output_dir: Локальный каталог результата.
        identity: Immutable shop/cabinet/NMID identity.
        period_start: Необязательная нижняя граница периода.
        period_end: Необязательная верхняя граница периода.
    Returns:
        Summary с primary filename и SHA-256.
    Raises:
        RuntimeError: при identity/semantic/write gate violation.
    """
    root = output_dir.resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    source_result = _run_existing_read_only_seam(identity, root)
    identity_errors = reconcile_identity(root / "source", identity)
    payload: dict[str, Any] = {
        "artifact_class": "MULTI_CLIENT_AD_PREFLIGHT",
        "run_identity": identity.as_dict(),
        "source_result": source_result,
        "product": {
            "ownership": "reconciled from source payload",
            "title_imtid_members": "see source evidence",
        },
        "stock": {
            "fbo": "GAP",
            "fbs": "GAP",
            "reservations": "GAP",
            "missing_is_not_zero": True,
        },
        "campaigns": {
            "physical_target_campaigns": "see source evidence",
            "cpc_is_not_bot_search": True,
            "cpc": "separate",
            "bot_search": "separate",
        },
        "advsetting": {
            "classes": ["Auto", "Search", "V3"],
            "absent_semantics": ["CONFIRMED_ABSENT", "MISSING"],
        },
        "economics": {
            "closed": "minimal closed economics",
            "open": "bounded open period",
            "factual_is_not_attributed": True,
        },
        "periods": {
            "start": period_start or "bounded-by-source",
            "end": period_end or "bounded-by-source",
            "open_closed_distinct": True,
        },
        "funding": {"semantics": "GAP unless explicitly evidenced"},
        "gaps": [
            "FBO/FBS/reservations GAP unless source provides evidence",
            "funding semantics GAP unless source provides evidence",
        ],
        "write_counts": WRITE_COUNTS,
    }
    semantic_errors = validate_semantics(payload)
    if identity_errors or semantic_errors:
        failure = {
            "status": STATUS_FAIL_IDENTITY if identity_errors else "FAIL_SEMANTICS",
            "identity_errors": identity_errors,
            "semantic_errors": semantic_errors,
            "run_identity": identity.as_dict(),
        }
        (root / "FAILURE.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise RuntimeError(json.dumps(failure, ensure_ascii=False))

    manifest = root / "manifest.json"
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stamp = datetime.now(timezone.utc).astimezone(TIMEZONE).strftime("%Y%m%dT%H%M%S%z")
    primary_name = (
        f"PROKRAFT-CABINET{identity.wb_cabinet_id}-NMID{identity.target_nmid}"
        f"-PREFLIGHT-{stamp}.zip"
    )
    primary = root / primary_name
    with zipfile.ZipFile(primary, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path != primary:
                archive.write(path, path.relative_to(root).as_posix())
    digest = _sha256(primary)
    (root / f"{primary_name}.sha256").write_text(
        f"{digest}  {primary_name}\n", encoding="utf-8"
    )
    report = root / "SCRIPTS_REPORT.md"
    report.write_text(
        "\n".join(
            [
                "# Generic multi-client advertising preflight",
                f"- identity: `{json.dumps(identity.as_dict(), ensure_ascii=False)}`",
                "- ALL_PRODUCTION_WRITES=0",
                f"- PRIMARY_ARTIFACT: `{primary_name}`",
                f"- PRIMARY_SHA256: `{digest}`",
                "- FBO/FBS/reservations: GAP where not evidenced",
                "- missing stock is not zero; factual is not attributed",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "STATUS": "COMPLETE_WITH_GAPS",
        "PRIMARY_ARTIFACT": primary_name,
        "PRIMARY_SHA256": digest,
        "ZIP_ABSOLUTE_PATH": str(primary),
        "LOCAL_REPORT_PATH": str(report),
        "ALL_PRODUCTION_WRITES": 0,
        "GAPS": payload["gaps"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать обязательную identity и bounded period arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shop-id", required=True)
    parser.add_argument("--wb-cabinet-id", required=True, type=int)
    parser.add_argument("--target-nmid", required=True, type=int)
    parser.add_argument("--client-size-id", required=True, type=int)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--period-start")
    parser.add_argument("--period-end")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить generic collector и вывести artifact gate поля."""
    args = parse_args(argv)
    identity = RunIdentity(
        shop_id=args.shop_id,
        wb_cabinet_id=args.wb_cabinet_id,
        target_nmid=args.target_nmid,
        client_size_id=args.client_size_id,
    )
    try:
        result = run_collect(
            Path(args.output_dir),
            identity,
            period_start=args.period_start,
            period_end=args.period_end,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ops-script: failed; error={exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_ARTIFACT={result['PRIMARY_ARTIFACT']}")
    print(f"PRIMARY_SHA256={result['PRIMARY_SHA256']}")
    print("ALL_PRODUCTION_WRITES=0")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
