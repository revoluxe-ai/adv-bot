"""Unit checks for the ProKraft historical SPP collector."""

from scripts import a1_prokraft_spp_dynamics_collect as collector


def test_daily_sku_preserves_observed_spp_and_excludes_empty_days() -> None:
    """SPP is calculated only for SKU/day rows with factual orders."""
    rows = [
        {
            "date_msk": "2026-08-17",
            "nmid": 143023475,
            "spp_valid": 12.0,
            "quantity": 1.0,
            "finishedPrice": 100,
        },
        {
            "date_msk": "2026-08-17",
            "nmid": 143023475,
            "spp_valid": 18.0,
            "quantity": 2.0,
            "finishedPrice": 90,
        },
    ]

    result = collector._daily_sku(rows)  # pyright: ignore[reportPrivateUsage]

    assert len(result) == 1
    assert result[0]["SPP_STATUS"] == "OBSERVED"
    assert result[0]["median_spp"] == 15.0
    assert result[0]["units_count"] == 3.0


def test_store_series_marks_no_order_observation_explicitly() -> None:
    """Calendar days without orders are not emitted as SPP zero."""
    result = collector._store_series([])  # pyright: ignore[reportPrivateUsage]

    assert len(result) == 29
    assert all(row["SPP_STATUS"] == "NO_ORDER_OBSERVATION" for row in result)
    assert all(row["median_spp"] is None for row in result)
