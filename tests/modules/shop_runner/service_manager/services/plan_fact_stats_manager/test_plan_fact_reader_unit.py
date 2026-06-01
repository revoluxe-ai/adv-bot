from unittest.mock import AsyncMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PLAN_FACT_CH_TS_FORMAT_MSK,
    PlanFactReader,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_latest_plan_facts_returns_mapping() -> None:
    reader = PlanFactReader()
    rows = [
        (111, 95.5, 520.0, 90.0, "DIRECT_SALES", "02.01.2025 03:04"),
        (222, 180.0, 610.0, 175.0, "BY_CARTS", "03.01.2025 04:05"),
    ]
    mock_result = AsyncMock()
    mock_result.result_rows = rows
    mock_client = AsyncMock()
    mock_client.query = AsyncMock(return_value=mock_result)
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader.get_clickhouse_client",
        return_value=mock_context,
    ):
        result = await reader.get_latest_plan_facts([111, 222])

    mock_client.query.assert_awaited_once()
    call_args = mock_client.query.call_args
    assert call_args.kwargs["parameters"] == {
        "adv_ids": [111, 222],
        "plan_fact_ts_format": PLAN_FACT_CH_TS_FORMAT_MSK,
    }
    assert "IN %(adv_ids)s" in call_args.args[0]

    assert set(result.keys()) == {111, 222}
    assert result[111].fact_predict_orders == 95.5
    assert result[111].fact_original_orders == 90.0
    assert result[111].fact_method == "DIRECT_SALES"
    assert result[111].plan_fact_ch_ts_msk == "02.01.2025 03:04"
    assert result[222].fact_pay_for_order == 610.0
    assert result[222].fact_original_orders == 175.0
    assert result[222].fact_method == "BY_CARTS"
    assert result[222].plan_fact_ch_ts_msk == "03.01.2025 04:05"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_latest_plan_facts_empty_ids_short_circuit() -> None:
    reader = PlanFactReader()
    result = await reader.get_latest_plan_facts([])
    assert result == {}
