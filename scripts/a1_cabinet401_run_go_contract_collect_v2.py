"""A1 cabinet-401 strict read-only collector with isolated async workers.

Модуль объединяет существующие A1 factual-пакеты в контрактный ZIP для
магазина 5339... и кабинета 401. Каждый пакет запускается в отдельном
процессе, поэтому asyncpg и WB DI не разделяют event loop между
последовательными коллекторами. Production write-paths отсутствуют.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

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
PRIMARY_NAME = "A1-CABINET401-RUN-GO-CONTRACT-V2.zip"


def _sha256(path: Path) -> str:
    """Вычислить SHA-256 файла для artifact gate."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _worker_result(mode: str, output_dir: Path) -> dict[str, Any]:
    """Запустить один существующий collector в отдельном Python-процессе."""
    if mode == "strict":
        strict.SHOP_ID = SHOP_ID
        strict.EXPECTED_WB_CABINET_ID = WB_CABINET_ID
        strict.TARGET_NMIDS = frozenset(TARGET_NMIDS)
        strict.RECONCILE_CAMPAIGNS = {}
        result = strict.run_collect(output_dir)
    elif mode == "performance":
        performance.SHOP_ID = SHOP_ID
        performance.PRIORITY_NMIDS = TARGET_NMIDS
        performance.ADJACENT_NMIDS = ()
        performance.ALL_PRIORITY_NMIDS = TARGET_NMIDS
        result = performance.run_collect(output_dir)
    else:
        raise ValueError(f"unknown worker mode: {mode}")
    print(f"RESULT_JSON={json.dumps(result, ensure_ascii=False)}")
    return result


def _run_isolated_worker(mode: str, output_dir: Path) -> dict[str, Any]:
    """Выполнить worker с отдельным event loop и вернуть его summary."""
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        mode,
        "--output-dir",
        str(output_dir),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().replace("\n", " ")
        raise RuntimeError(f"{mode} worker failed: {detail[-2000:]}")
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("RESULT_JSON="):
            value = json.loads(line.removeprefix("RESULT_JSON="))
            if isinstance(value, dict):
                return value
    raise RuntimeError(f"{mode} worker returned no result")


def _scenario_rows() -> list[dict[str, Any]]:
    """Описать сценарии headroom без представления promo как cash."""
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
    strict_result: dict[str, Any], performance_result: dict[str, Any]
) -> dict[str, Any]:
    """Сформировать machine-readable envelope с явными coverage gaps."""
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
        "stock": {"fbo_fbs": "GAP: no stock adapter", "missing_is_not_zero": True},
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
        "source_results": {"strict": strict_result, "performance": performance_result},
        "coverage_gaps": [
            "FBO/FBS stock adapter is unavailable; missing is not zero.",
            "CPC/legacy/unmanaged labels require physical inventory confirmation.",
        ],
        "write_counts": SAFETY_WRITE_COUNTS,
    }


def run_collect(output_dir: Path) -> dict[str, Any]:
    """Собрать contract ZIP через два изолированных read-only worker процесса.

    Args:
        output_dir: Каталог артефактов текущего запуска.
    Returns:
        Summary с primary artifact и SHA-256.
    Raises:
        RuntimeError: при contradiction identity, worker failure или write gate.
    """
    root = output_dir.resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    strict_result = _run_isolated_worker("strict", root / "strict")
    performance_result = _run_isolated_worker("performance", root / "performance")
    if strict_result.get("WB_CABINET_ID") != WB_CABINET_ID:
        raise RuntimeError("WB cabinet identity contradiction")
    if any(SAFETY_WRITE_COUNTS.values()):
        raise RuntimeError("production write invariant violated")

    payload = _contract_payload(strict_result, performance_result)
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
                "- event_loop_isolation: separate worker process per collector",
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
        "GAPS": payload["coverage_gaps"],
        **SAFETY_WRITE_COUNTS,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать режим worker и каталог output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("strict", "performance"))
    parser.add_argument("--output-dir", default=".tmp/a1_cabinet401_run_go_contract_v2")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить collector или один из его изолированных workers."""
    args = parse_args(argv)
    if args.worker:
        _worker_result(args.worker, Path(args.output_dir))
        return 0
    result = run_collect(Path(args.output_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_ARTIFACT={result['PRIMARY_ARTIFACT']}")
    print(f"PRIMARY_SHA256={result['PRIMARY_SHA256']}")
    print("ALL_PRODUCTION_WRITES=0")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
