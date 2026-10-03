"""collect_v2 layout: canonical JSONL paths inside wb_readonly_research.zip.

Standalone module (не под пакетом collect/) — избегает eager import runner при load.
"""

from __future__ import annotations

import json
import zipfile
from typing import Any

COLLECT_LAYOUT_VERSION = "collect_v2"

COLLECT_V2_ORDERS_JSONL = "raw/orders.jsonl"
COLLECT_V2_SALES_JSONL = "raw/sales.jsonl"
COLLECT_V2_FUNNEL_JSONL = "raw/funnel/funnel.jsonl"
COLLECT_V2_CAMPAIGNS_JSONL = "raw/ads/campaigns.jsonl"
COLLECT_V2_FULLSTATS_JSONL = "raw/ads/fullstats.jsonl"

LEGACY_ORDERS_JSONL = "orders.jsonl"
LEGACY_FUNNEL_JSONL = "funnel/funnel.jsonl"

COLLECT_V2_REQUIRED_FOR_A1_DAILY_SPEND = (
    COLLECT_V2_ORDERS_JSONL,
    COLLECT_V2_FUNNEL_JSONL,
    COLLECT_V2_CAMPAIGNS_JSONL,
    COLLECT_V2_FULLSTATS_JSONL,
)


def read_jsonl_from_zip(
    zf: zipfile.ZipFile,
    canonical: str,
    *,
    legacy: str | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Прочитать JSONL из zip; вернуть rows и фактический member path."""
    candidates = [canonical]
    if legacy and legacy not in candidates:
        candidates.append(legacy)
    for member in candidates:
        if member in zf.namelist():
            rows = _decode_jsonl(zf.read(member).decode("utf-8"))
            return rows, member
    raise KeyError(f"collect zip missing {canonical!r} (layout={COLLECT_LAYOUT_VERSION})")


def _decode_jsonl(data: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except json.JSONDecodeError:
            continue
    return rows
