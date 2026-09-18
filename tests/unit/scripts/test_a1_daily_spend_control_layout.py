"""Regression: collect_v2 layout paths for A1 daily spend loaders."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.collect_layout import (
    COLLECT_V2_ORDERS_JSONL,
    read_jsonl_from_zip,
)


def test_collect_v2_orders_jsonl_layout(tmp_path: Path) -> None:
    """A1 loaders must read orders from collect_v2 path raw/orders.jsonl."""
    staging = tmp_path / "staging"
    staging.mkdir()
    orders_path = staging / "raw" / "orders.jsonl"
    orders_path.parent.mkdir(parents=True)
    orders_path.write_text(
        json.dumps({"date": "2026-08-29", "nmId": 1, "totalPrice": 100}) + "\n",
        encoding="utf-8",
    )
    archive = tmp_path / "wb_readonly_research.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in staging.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(staging).as_posix())

    with zipfile.ZipFile(archive) as zf:
        assert COLLECT_V2_ORDERS_JSONL in zf.namelist()
        rows, member = read_jsonl_from_zip(zf, COLLECT_V2_ORDERS_JSONL)
    assert member == "raw/orders.jsonl"
    assert len(rows) == 1
    assert rows[0]["nmId"] == 1
