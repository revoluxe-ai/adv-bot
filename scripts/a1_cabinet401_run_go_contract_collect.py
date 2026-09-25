"""A1 cabinet-401 strict read-only contract collector.

Собирает два существующих A1 factual-пакета для магазина 5339... и
объединяет их в один immutable ZIP: closed/open store economics, DRR headroom,
funding semantics, campaign state, glue/imtID и direct/associated attribution.
Недоступные в read-only источниках секции явно помечаются GAP; collector не
содержит WB, PostgreSQL, ClickHouse или Redis write-paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from tools.scripts.receipts import (
    invocation_output_path,
    prepare_invocation_output_dir,
)
from scripts import a1_current_performance_drr_snapshot as performance
from scripts import a1_strict_read_only_contract_collect as strict

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
WB_CABINET_ID = 401
TARGET_DRR = 0.10
TARGET_NMIDS = (
    1256595631,
    451263613,
    645328132,
    525419807,
    217149845,
    255636259,
    751657528,
    214754056,
)
PRESERVED_DECISIONS = {
    "751657528": "KEEP_STOPPED",
    "1256595631": "SCALE_FIRST",
}
SAFETY_WRITE_COUNTS = {
    "ALL_PRODUCTION_WRITES": 0,
    "WB_API_WRITES": 0,
    "POSTGRES_WRITES": 0,
    "CLICKHOUSE_WRITES": 0,
    "REDIS_WRITES": 0,
    "CAMPAIGN_WRITES": 0,
    "BUDGET_WRITES": 0,
    "TOPUP_WRITES": 0,
    "CPO_WRITES": 0,
    "AGGRESSION_WRITES": 0,
}
PRIMARY_NAME = "A1-CABINET401-RUN-GO-CONTRACT.zip"


def _sha256(path: Path) -> str:
    """Вычислить SHA-256 файла для локального artifact gate."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _patch_target_scope() -> None:
    """Ограничить существующие read-only collectors ровно восемью NMID."""
    strict.SHOP_ID = SHOP_ID
    strict.EXPECTED_WB_CABINET_ID = WB_CABINET_ID
    strict.TARGET_NMIDS = frozenset(TARGET_NMIDS)
    strict.RECONCILE_CAMPAIGNS = {}
    performance.SHOP_ID = SHOP_ID
    performance.PRIORITY_NMIDS = TARGET_NMIDS
    performance.ADJACENT_NMIDS = ()
    performance.ALL_PRIORITY_NMIDS = TARGET_NMIDS


def _scenario_rows() -> list[dict[str, Any]]:
    """Описать headroom scenarios без представления promo как cash."""
    return [
        {
            "additional_rub": amount,
            "target_drr": TARGET_DRR,
            "promo_is_cash": False,
            "interpretation": "bounded scenario input; no write or recommendation",
        }
        for amount in (2000, 4000, 6000)
    ]


def _contract_payload(
    strict_result: dict[str, Any],
    performance_result: dict[str, Any],
) -> dict[str, Any]:
    """Сформировать machine-readable contract envelope with explicit gaps."""
    return {
        "artifact_class": "A1_CABINET401_RUN_GO_CONTRACT",
        "mode": "STRICT_READ_ONLY",
        "identity": {"shop_id": SHOP_ID, "wb_cabinet_id": WB_CABINET_ID},
        "target_nmids": list(TARGET_NMIDS),
        "preserved_decisions": PRESERVED_DECISIONS,
        "store_economics": {
            "closed_windows": ["3d", "7d"],
            "open_day": performance_result.get("WINDOWS", {}).get("CURRENT_1D"),
            "target_drr": TARGET_DRR,
            "headroom_scenarios": _scenario_rows(),
            "factual_vs_attributed": "factual store sales and attributed ad rows remain separate",
        },
        "funding": {
            "snapshot": performance_result.get("PROMO_CURRENT"),
            "promo_is_cash": False,
            "net_bonus_cashbacks_and_scenarios": "see funding fields and explicit scenario inputs",
        },
        "campaign_inventory": {
            "source_primary": "strict/02_CAMPAIGNS_CURRENT.csv",
            "required_classes": ["CPC", "legacy", "unmanaged"],
            "search_leg_binding": "CPC binding is not treated as Search leg",
            "glue_imtid": "strict/04_MATS.csv and campaign rows",
        },
        "stock": {
            "fbo_fbs": "GAP: this bounded collector has no stock adapter",
            "missing_is_not_zero": True,
        },
        "attribution": {
            "windows": ["3d", "7d"],
            "direct_and_associated": "strict/03_PERFORMANCE.csv",
            "factual_store_sales": "strict/01_STORE.csv",
        },
        "readiness_classes": ["READY", "CONDITIONAL", "GAP", "BLOCKED"],
        "proposed_write_plan": {
            "bounded": True,
            "writes_executed": False,
            "content": "No advertising/configuration or production write plan is executed.",
        },
        "source_results": {
            "strict": strict_result,
            "performance": performance_result,
        },
        "coverage_gaps": [
            "FBO/FBS stock adapter is unavailable in this collector; missing is not zero.",
            "CPC/legacy/unmanaged class labels require physical inventory confirmation.",
        ],
        "write_counts": SAFETY_WRITE_COUNTS,
    }


def _verify_tree(root: Path) -> dict[str, Any]:
    """Проверить JSON/JSONL и ZIP artifacts before primary packaging."""
    checked: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name == PRIMARY_NAME:
            continue
        if path.suffix.lower() == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    json.loads(line)
        elif path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                archive.testzip()
        checked.append(path.relative_to(root).as_posix())
    return {"checked_files": sorted(checked), "status": "PASS"}


def run_collect(output_dir: Path) -> dict[str, Any]:
    """Собрать и проверить единый contract ZIP.

    Args:
        output_dir: Каталог invocation-owned outputs.

    Returns:
        Machine-readable summary containing primary path and digest.

    Raises:
        RuntimeError: если identity или zero-write invariant нарушены.
    """
    _patch_target_scope()
    root = prepare_invocation_output_dir(output_dir)
    strict_result = strict.run_collect(root / "strict")
    performance_result = performance.run_collect(root / "performance")
    if strict_result.get("WB_CABINET_ID") != WB_CABINET_ID:
        raise RuntimeError("WB cabinet identity contradiction")
    payload = _contract_payload(strict_result, performance_result)
    if any(SAFETY_WRITE_COUNTS.values()):
        raise RuntimeError("production write invariant violated")
    (root / "contract.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    verification = _verify_tree(root)
    payload["verification"] = verification
    (root / "contract.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    primary = root / PRIMARY_NAME
    with zipfile.ZipFile(primary, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path != primary:
                archive.write(path, path.relative_to(root).as_posix())
    digest = _sha256(primary)
    sidecar = root / f"{PRIMARY_NAME}.sha256"
    sidecar.write_text(f"{digest}  {PRIMARY_NAME}\n", encoding="utf-8")
    report = root / "SCRIPTS_REPORT.md"
    report.write_text(
        "\n".join(
            [
                "# A1 cabinet-401 RUN GO contract",
                f"- shop_id: `{SHOP_ID}`",
                f"- wb_cabinet_id: `{WB_CABINET_ID}`",
                f"- target_nmids: `{','.join(str(n) for n in TARGET_NMIDS)}`",
                "- ALL_PRODUCTION_WRITES=0",
                f"- PRIMARY_ARTIFACT: `{PRIMARY_NAME}`",
                f"- PRIMARY_SHA256: `{digest}`",
                "- FBO/FBS: GAP; missing != 0",
                "- promo_is_cash: false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "EXECUTION_STATUS": "COMPLETE_WITH_GAPS",
        "SHOP_ID": SHOP_ID,
        "WB_CABINET_ID": WB_CABINET_ID,
        "TARGET_NMIDS": list(TARGET_NMIDS),
        "PRIMARY_ARTIFACT": PRIMARY_NAME,
        "PRIMARY_SHA256": digest,
        "ZIP_ABSOLUTE_PATH": str(primary),
        "VERIFICATION": verification,
        "GAPS": payload["coverage_gaps"],
        **SAFETY_WRITE_COUNTS,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать CLI output-dir для Kubernetes Job и локальной проверки."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        help="Optional precomputed invocation-owned output directory.",
    )
    parser.add_argument("--run-id", default="local-run")
    parser.add_argument("--caller-root", default=".")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить collector и вывести primary artifact metadata."""
    args = parse_args(argv)
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else invocation_output_path(
            Path(args.caller_root).resolve(),
            args.run_id,
            "a1-cabinet401-run-go-contract",
        )
    )
    result = run_collect(output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_ARTIFACT={result['PRIMARY_ARTIFACT']}")
    print(f"PRIMARY_SHA256={result['PRIMARY_SHA256']}")
    print("ALL_PRODUCTION_WRITES=0")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
