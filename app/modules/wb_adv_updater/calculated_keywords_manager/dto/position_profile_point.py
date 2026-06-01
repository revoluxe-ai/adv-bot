"""Per-position row for keyword bid/conversion profile (AutoUpdater v3, Redis cache)."""

from datetime import datetime

from pydantic import BaseModel, Field


class PositionProfilePoint(BaseModel):
    """One search position for a keyword: bid + conversion-derived metrics."""

    position: int = Field(..., ge=1)
    bid: int = Field(..., ge=0)
    predicted_conversion: float | None = Field(
        default=None,
        description="Conv carts-to-views at this position (same unit as BidPosition.conv_carts_to_views).",
    )
    pay_for_cart: float | None = Field(
        default=None,
        description="Rub per cart at this bid/conv; infinity represented as None after sanitize.",
    )
    timestamp: datetime | None = None
    ch_observed: bool = Field(
        default=True,
        description="True — точка из CH bid_decision_log; False — синтетика _fill_positions.",
    )

    model_config = {"extra": "forbid"}
