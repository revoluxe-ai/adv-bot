from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.mp.wb.api.adapter.promotion_client.finance.adapter import (
    FinanceAdapter,
    BalanceTypeNotSupportedError,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    GetAdvV1BudgetResponse200,
    ResponseWithReturn,
)
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager


class _FakeAuthHandler:
    shop_id = "test-shop"

    async def get_proxy_client(self, adapter):  # pragma: no cover - interface stub
        return "client"


def _build_adapter(monkeypatch, parsed) -> tuple[FinanceAdapter, AsyncMock]:
    request_limit_manager = RequestLimitManager()
    adapter = FinanceAdapter(
        base_url="https://advert-api.wildberries.ru",
        auth_client_handler=_FakeAuthHandler(),
        request_limit_manager=request_limit_manager,
    )

    async_mock = AsyncMock(return_value=SimpleNamespace(parsed=parsed))
    monkeypatch.setattr(
        "app.core.mp.wb.api.adapter.promotion_client.finance.adapter.with_raise_errors",
        async_mock,
    )
    return adapter, async_mock


@pytest.mark.asyncio
async def test_get_campaign_budget_returns_response(monkeypatch) -> None:
    adapter, mock_raise = _build_adapter(
        monkeypatch, GetAdvV1BudgetResponse200(total=500)
    )

    response = await adapter.get_campaign_budget(adv_id=123)

    assert isinstance(response, GetAdvV1BudgetResponse200)
    assert response.total == 500
    mock_raise.assert_awaited()


@pytest.mark.asyncio
async def test_top_up_budget_resolves_balance_type(monkeypatch) -> None:
    adapter, mock_raise = _build_adapter(
        monkeypatch, ResponseWithReturn(total=1500)
    )

    response = await adapter.top_up_budget(
        adv_id=456,
        amount=700,
        balance_type="bonus",
    )

    assert isinstance(response, ResponseWithReturn)
    assert response.total == 1500
    called_kwargs = mock_raise.call_args.kwargs
    body = called_kwargs.get("body")
    assert body is not None
    assert body.sum_ == 700
    assert body.type_ == 3  # bonus mapped to 3


@pytest.mark.asyncio
async def test_top_up_budget_sends_cashback_fields(monkeypatch) -> None:
    adapter, mock_raise = _build_adapter(
        monkeypatch, ResponseWithReturn(total=1500)
    )

    _ = await adapter.top_up_budget(
        adv_id=456,
        amount=700,
        balance_type="net",
        cashback_sum=350,
        cashback_percent=50,
    )

    called_kwargs = mock_raise.call_args.kwargs
    body = called_kwargs.get("body")
    assert body is not None
    assert body.type_ == 1
    assert body.cashback_sum == 350
    assert body.cashback_percent == 50


@pytest.mark.asyncio
async def test_get_costs_history_returns_upd_items(monkeypatch) -> None:
    from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
        GetAdvV1UpdResponse200Item,
    )

    item = GetAdvV1UpdResponse200Item(
        upd_num=1,
        upd_sum=50,
        advert_id=42,
        payment_type="Keshbek",
    )
    adapter, mock_raise = _build_adapter(monkeypatch, [item])
    rows = await adapter.get_costs_history(
        from_date=__import__("datetime").date(2026, 1, 1),
        to_date=__import__("datetime").date(2026, 1, 31),
    )
    assert len(rows) == 1
    assert rows[0].payment_type == "Keshbek"
    mock_raise.assert_awaited()


def test_resolve_balance_type_unknown(monkeypatch) -> None:
    adapter, _ = _build_adapter(monkeypatch, None)
    with pytest.raises(BalanceTypeNotSupportedError):
        adapter._resolve_balance_type("unsupported")  # type: ignore[attr-defined]



