"""Convert ClickHouse bid/conv rows into Redis-safe profile points."""

from __future__ import annotations

import math
from datetime import datetime

from app.modules.predict_keywords_target_place.clickhouse_manager.dto.bid_position import (
    BidPosition,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)


def profile_points_from_bid_positions(rows: list[BidPosition]) -> list[PositionProfilePoint]:
    out: list[PositionProfilePoint] = []
    for p in rows:
        pay = p.pay_for_cart
        pay_out: float | None
        if not math.isfinite(pay):
            pay_out = None
        else:
            pay_out = float(pay)
        ts: datetime | None = p.timestamp
        out.append(
            PositionProfilePoint(
                position=p.position,
                bid=int(p.bid),
                predicted_conversion=p.conv_carts_to_views,
                pay_for_cart=pay_out,
                timestamp=ts,
            )
        )
    return sorted(out, key=lambda x: x.position)
