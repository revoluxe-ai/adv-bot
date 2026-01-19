from __future__ import annotations

import logging
from typing import Final

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.api.finance import (
    get_adv_v1_balance,
    get_adv_v1_budget,
    post_adv_v1_budget_deposit,
)
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import (
    GetAdvV1BalanceResponse200,
    GetAdvV1BudgetResponse200,
    PostAdvV1BudgetDepositBody,
    ResponseWithReturn,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator

logger = logging.getLogger(__name__)


class BalanceTypeNotSupportedError(ValueError):
    """Raised when WB balance type is not supported by the adapter."""


class FinanceAdapter(BaseSectionAdapter):
    """Adapter for WB promotion finance endpoints."""

    _BALANCE_TYPES: Final[dict[str, int]] = {
        "balance": 0,
        "net": 1,
        "bonus": 3,
    }

    @retry_decorator(period=1, limit=4)
    async def get_campaign_budget(
        self,
        adv_id: int,
    ) -> GetAdvV1BudgetResponse200 | None:
        """
        Retrieve campaign budget (total) via promotion API.
        """

        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(
            get_adv_v1_budget.asyncio_detailed,
            client,
            id=adv_id,
        )
        parsed = response.parsed
        if isinstance(parsed, GetAdvV1BudgetResponse200):
            return parsed
        logger.warning(
            "Unexpected WB get_adv_v1_budget response type for adv_id=%s: %s",
            adv_id,
            type(parsed).__name__,
        )
        return None

    @retry_decorator(period=5, limit=1)
    async def get_campaign_balance(self) -> GetAdvV1BalanceResponse200 | None:
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(
            get_adv_v1_balance.asyncio_detailed,
            client,
        )
        parsed = response.parsed
        if isinstance(parsed, GetAdvV1BalanceResponse200):
            return parsed
        logger.warning(
            "Unexpected WB get_adv_v1_balance response type: %s",
            type(parsed).__name__,
        )
        return None

    @retry_decorator(period=1, limit=1)
    async def top_up_budget(
        self,
        adv_id: int,
        amount: int,
        balance_type: str,
        return_total: bool = True,
    ) -> ResponseWithReturn | None:
        """
        Top up campaign budget. Optionally request WB to return current total.
        """

        resolved_balance_type = self._resolve_balance_type(balance_type)
        body = PostAdvV1BudgetDepositBody(
            sum_=amount,
            type_=resolved_balance_type,
            return_=return_total,
        )
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(
            post_adv_v1_budget_deposit.asyncio_detailed,
            client,
            body=body,
            id=adv_id,
        )
        parsed = response.parsed
        if isinstance(parsed, ResponseWithReturn):
            return parsed
        logger.warning(
            "Unexpected WB post_adv_v1_budget_deposit response type for adv_id=%s: %s",
            adv_id,
            type(parsed).__name__,
        )
        return None

    def _resolve_balance_type(self, balance_type: str) -> int:
        normalized = balance_type.strip().lower()
        if normalized.isdigit():
            return int(normalized)
        resolved = self._BALANCE_TYPES.get(normalized)
        if resolved is None:
            raise BalanceTypeNotSupportedError(
                f"Unsupported balance type '{balance_type}' for WB top-up"
            )
        return resolved
