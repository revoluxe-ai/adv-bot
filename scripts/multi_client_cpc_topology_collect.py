"""Generic strict read-only CPC topology collector.

Модуль получает из Wildberries и read-only application adapters состояние
одной рекламной кампании для явно заданной пары shop/cabinet и nmID.
Он не собирает остатки, экономику или DRR и не вызывает production write
маршруты. Результат — изолированный ZIP с identity envelope и SHA-256.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Europe/Moscow")
WRITE_COUNTS = {
    "ALL_PRODUCTION_WRITES": 0,
    "WB_API_WRITES": 0,
    "POSTGRES_WRITES": 0,
    "CLICKHOUSE_WRITES": 0,
    "REDIS_WRITES": 0,
}
IDENTITY_KEYS = ("shop_id", "wb_cabinet_id", "target_nmid", "adv_id")


@dataclass(frozen=True)
class RunIdentity:
    """Неизменяемая identity envelope одного bounded запуска."""

    shop_id: str
    cabinet: int
    target_nmid: int
    adv_id: int

    def as_dict(self) -> dict[str, Any]:
        """Вернуть JSON-совместимую identity envelope."""
        return {
            "shop_id": self.shop_id,
            "cabinet": self.cabinet,
            "target_nmid": self.target_nmid,
            "adv_id": self.adv_id,
        }


def _sha256(path: Path) -> str:
    """Посчитать SHA-256 файла потоково."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows_from_json(root: Path) -> Iterable[dict[str, Any]]:
    """Извлечь JSON-объекты из локального evidence дерева."""
    for path in root.rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        values = value if isinstance(value, list) else [value]
        for row in values:
            if isinstance(row, dict):
                yield row


def reconcile_identity(root: Path, identity: RunIdentity) -> list[str]:
    """Отклонить payload rows с явно чужой identity."""
    expected = identity.as_dict()
    aliases = {
        "wb_cabinet_id": identity.cabinet,
        "cabinet": identity.cabinet,
        "target_nmid": identity.target_nmid,
        "nmID": identity.target_nmid,
        "adv_id": identity.adv_id,
        "advertId": identity.adv_id,
        "shop_id": identity.shop_id,
    }
    errors: list[str] = []
    for row in _rows_from_json(root):
        for key, wanted in aliases.items():
            if key not in row or row[key] in (None, "", "GAP", "MISSING"):
                continue
            if str(row[key]) != str(wanted):
                errors.append(f"{key}: expected={wanted}, got={row[key]}")
    return sorted(set(errors))


def validate_write_gate() -> list[str]:
    """Проверить, что collector объявляет только нулевые production writes."""
    return [
        f"{key} is non-zero"
        for key, value in WRITE_COUNTS.items()
        if value != 0
    ]


def _jsonable(value: Any) -> Any:
    """Преобразовать DTO-подобные объекты в JSON-safe структуру."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return str(value)


async def collect(identity: RunIdentity, output_dir: Path) -> dict[str, Any]:
    """Собрать read-only CPC topology и записать verified primary ZIP.

    Args:
        identity: Явные shop, cabinet, target nmID и campaign IDs.
        output_dir: Каталог результата; существующий каталог очищается.
    Returns:
        Поля primary artifact и SHA-256 для Job handoff.
    Raises:
        RuntimeError: Если campaign не принадлежит cabinet или нарушена identity.
    """
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.modules.common_slaves.wildberries.super_cabinet_manager import (
        get_access_for_wb_cabinet,
    )

    root = output_dir.resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    errors = validate_write_gate()
    if errors:
        raise RuntimeError("; ".join(errors))

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        access = await get_access_for_wb_cabinet(identity.shop_id)
        if access is None:
            raise RuntimeError("shop access was not resolved")
        factory = (
            container.module_resources.wb_manager_hub_factory_container
            .wb_manager_hub_factory()
        )
        manager = factory.get_wb_manager_hub(identity.shop_id).wb_data_manager
        promotion = manager.promotion_manager
        cabinet_adv_ids = list(
            await promotion._client.promotion_count_adapter.get_cabinet_adv_ids()
            or []
        )
        if identity.adv_id not in {int(value) for value in cabinet_adv_ids}:
            raise RuntimeError("target adv_id is not owned by the requested cabinet")
        raw_campaigns = await promotion.get_adverts_v2_by_ids([identity.adv_id])
        campaigns = [
            _jsonable(item)
            for item in raw_campaigns or []
            if isinstance(_jsonable(item), dict)
        ]

    topology = {
        "identity": identity.as_dict(),
        "campaigns": campaigns,
        "target": {
            "adv_id": identity.adv_id,
            "target_nmid": identity.target_nmid,
            "campaign_count": len(campaigns),
            "target_nmid_present": any(
                any(
                    isinstance(item, dict)
                    and str(item.get("nm_id") or item.get("nmId") or item.get("nmID"))
                    == str(identity.target_nmid)
                    for item in (
                        campaign.get("nm_settings")
                        or campaign.get("nmSettings")
                        or []
                    )
                )
                for campaign in campaigns
            ),
        },
        "scope": {
            "included": ["campaign_topology", "target_identity", "read_only_gates"],
            "excluded": ["stock", "economics", "drr", "writes"],
        },
        "write_counts": WRITE_COUNTS,
    }
    (root / "topology.json").write_text(
        json.dumps(topology, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    identity_errors = reconcile_identity(root, identity)
    if identity_errors:
        raise RuntimeError("foreign identity payload: " + "; ".join(identity_errors))

    stamp = datetime.now(timezone.utc).astimezone(TIMEZONE).strftime("%Y%m%dT%H%M%S%z")
    primary_name = f"multi-client-cpc-topology-cabinet-{identity.cabinet}-{stamp}.zip"
    primary = root / primary_name
    with zipfile.ZipFile(primary, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(root / "topology.json", "topology.json")
    digest = _sha256(primary)
    (root / f"{primary_name}.sha256").write_text(
        f"{digest}  {primary_name}\n", encoding="utf-8"
    )
    (root / "SCRIPTS_REPORT.md").write_text(
        "\n".join(
            [
                "# Generic CPC topology collector",
                f"- identity: `{json.dumps(identity.as_dict(), ensure_ascii=False)}`",
                "- mode: `STRICT_READ_ONLY`",
                "- ALL_PRODUCTION_WRITES=0",
                f"- PRIMARY_ARTIFACT: `{primary_name}`",
                f"- PRIMARY_SHA256: `{digest}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "PRIMARY_ARTIFACT": primary_name,
        "PRIMARY_SHA256": digest,
        "ZIP_ABSOLUTE_PATH": str(primary),
        "ALL_PRODUCTION_WRITES": 0,
        "LOCAL_REPORT_PATH": str(root / "SCRIPTS_REPORT.md"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать обязательную identity и каталог artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shop-id", required=True)
    parser.add_argument("--cabinet", required=True, type=int)
    parser.add_argument("--target-nmid", required=True, type=int)
    parser.add_argument("--adv-id", required=True, type=int)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить collector и вывести artifact gate поля."""
    args = parse_args(argv)
    identity = RunIdentity(
        shop_id=args.shop_id,
        cabinet=args.cabinet,
        target_nmid=args.target_nmid,
        adv_id=args.adv_id,
    )
    try:
        result = asyncio.run(collect(identity, Path(args.output_dir)))
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
