"""READ_ONLY whole-shop economics collector for WB cabinet 573.

Собирает закрытые окна фактических заказов/GMV и валового рекламного расхода
для магазина, текущий открытый день, кампании и bounded control diagnostics.
Переиспользует проверенный A1 current-performance pipeline, но переопределяет
shop_id и добавляет расчёты DRR=10% для указанного кабинета. Production writes
отсутствуют; выходной JSON предназначен для ручного экономического решения.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from scripts import a1_current_performance_drr_snapshot as base
from scripts import a1_daily_spend_control_reconciliation as spend_control
from scripts import a1_glue_topology_web_review_collect as glue
from scripts import a1_promo_adjusted_drr_collect as promo
from scripts import a1_promotion_funding_snapshot as funding
from scripts import ch_a1_evidence as evidence

SHOP_ID = "5586b2ff-449c-4151-9518-60f46d32b7d9"
WB_CABINET_ID = 573
TARGET_DRR = 0.10
TARGET_NMIDS = (
    751657528,
    266109990,
    143023475,
    234375724,
    214754056,
    1256595631,
)


def _patch_scope() -> None:
    """Переиспользовать pipeline для целевого магазина без изменения его кода."""
    evidence.SHOP_ID = SHOP_ID
    funding.SHOP_ID = SHOP_ID
    promo.SHOP_ID = SHOP_ID
    spend_control.SHOP_ID = SHOP_ID
    glue.SHOP_ID = SHOP_ID
    base.SHOP_ID = SHOP_ID
    base.PRIORITY_NMIDS = TARGET_NMIDS
    base.ADJACENT_NMIDS = ()
    base.ALL_PRIORITY_NMIDS = TARGET_NMIDS
    promo.WB_CABINET_ID_EXPECTED = WB_CABINET_ID


def _ratio(numerator: Any, denominator: Any) -> float | str:
    try:
        n = float(numerator or 0)
        d = float(denominator or 0)
    except (TypeError, ValueError):
        return "N/A"
    return round(n / d, 4) if d > 0 else "N/A"


def _enrich(report: dict[str, Any]) -> dict[str, Any]:
    """Добавить store headroom и нормализованный decision payload."""
    windows = report.get("windows") or report.get("window_rows") or {}
    normalized: dict[str, Any] = {}
    for name, row in windows.items() if isinstance(windows, dict) else []:
        gmv = row.get("factual_gmv", row.get("factual_order_value", 0))
        spend = row.get("gross_ad_spend", row.get("ad_spend", 0))
        orders = row.get("factual_orders", row.get("purchase_events", row.get("units", 0)))
        aov = _ratio(gmv, orders)
        store_cpo = _ratio(spend, orders)
        store_drr = _ratio(spend, gmv)
        normalized[name] = {
            **row,
            "total_factual_orders": orders,
            "total_factual_gmv": gmv,
            "average_order_value": aov,
            "total_ad_spend": spend,
            "store_cpo": store_cpo,
            "store_drr": store_drr,
            "allowed_spend_at_10_drr": round(float(gmv or 0) * TARGET_DRR, 2),
            "spend_headroom": round(float(gmv or 0) * TARGET_DRR - float(spend or 0), 2),
            "target_store_cpo_at_10_drr": (
                round(float(aov) * TARGET_DRR, 2)
                if isinstance(aov, (int, float))
                else "N/A"
            ),
            "cpo_headroom": (
                round(float(aov) * TARGET_DRR - float(store_cpo), 2)
                if isinstance(aov, (int, float)) and isinstance(store_cpo, (int, float))
                else "N/A"
            ),
        }
    report["store_windows_drr_10"] = normalized
    report["target_store_drr"] = TARGET_DRR
    report["target_nmids"] = list(TARGET_NMIDS)
    report["wb_cabinet_id"] = WB_CABINET_ID
    report["all_production_writes"] = 0
    return report


def _write_primary(output_dir: Path, report: dict[str, Any]) -> Path:
    """Записать primary JSON artifact с полным фактическим payload."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "whole_shop_economics.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    """Разобрать non-interactive параметры Job."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    """Собрать whole-shop read-only report и вывести primary path."""
    args = parse_args()
    _patch_scope()
    output_dir = Path(args.output_dir)
    report = base.run_collect(output_dir)
    primary = _write_primary(output_dir, _enrich(report))
    print(f"PRIMARY_ARTIFACT={primary}")
    print("ARTIFACT_CLASS=WHOLE_SHOP_ECONOMICS")
    print("ALL_PRODUCTION_WRITES=0")


if __name__ == "__main__":
    main()
