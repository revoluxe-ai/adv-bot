"""Read-only export helper for rec_system bid debug fixtures.

This module is intentionally not a pytest test. It can be run manually to
export raw ClickHouse rows into a JSON fixture for offline tests.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    AutoShelfBidRepository,
)


async def main() -> None:
    nmid_value = os.environ.get("REC_BID_DEBUG_NMID")
    if not nmid_value:
        raise RuntimeError("REC_BID_DEBUG_NMID is not set")
    mode = os.environ.get("REC_BID_DEBUG_MODE", "main")
    date_from_value = os.environ.get("REC_BID_DEBUG_DATE_FROM")
    date_to_value = os.environ.get("REC_BID_DEBUG_DATE_TO")
    if not date_from_value or not date_to_value:
        raise RuntimeError("REC_BID_DEBUG_DATE_FROM/TO are not set")

    nmid = int(nmid_value)
    date_from = datetime.fromisoformat(date_from_value)
    date_to = datetime.fromisoformat(date_to_value)

    repository = AutoShelfBidRepository(wb_manager_hub=None)  # type: ignore[arg-type]
    buckets = await repository.fetch_rec_bid_bucket_observations_for_nmid(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
    )

    payload = [
        {
            "bid": bucket.bid,
            "bucket_start": bucket.bucket_start.isoformat(),
            "impressions": bucket.impressions,
            "price_minor": bucket.price_minor,
        }
        for bucket in buckets
    ]

    output_dir = Path("tests/fixtures/rec_system_bid_math")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"rec_bid_debug_{nmid}_{mode}.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
