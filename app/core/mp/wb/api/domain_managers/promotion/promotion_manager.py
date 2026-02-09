from dataclasses import dataclass
from typing import Any
import datetime
from typing import List, TYPE_CHECKING

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import (
    NormqueryStatsDTO,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import (
    NormqueryBidDTO,
)
from app.core.mp.wb.api.domain_managers.promotion.methods.campaign_control import (
    pause_adv as pause_adv_method,
    rename_adv as rename_adv_method,
    start_adv as start_adv_method,
    stop_adv as stop_adv_method,
)
from app.core.mp.wb.api.domain_managers.promotion.methods.set_minus_phrases import (
    request,
)
from app.core.mp.wb.api.adapter.promotion_client.promotion_client import PromotionClient
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv
from app.core.mp.wb.api.adapter.promotion_client.common_bids.command import (
    SetCommonBidsCommand,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    GetAdvV1BalanceResponse200,
    PatchAdvV0BidsBody,
)

if TYPE_CHECKING:
    from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.command import (
        SetNormqueryBidsCommandItem,
    )
    from app.core.mp.wb.dto.adv_info import AdvInfoDTO


@dataclass(slots=True)
class CampaignBudgetInfo:
    total: int | None
    raw: dict[str, Any]


@dataclass(slots=True)
class BudgetTopUpResult:
    total: int | None
    raw: dict[str, Any]


class PromotionManager:
    """Доменный менеджер для работы с сущностями продвижения (WB API)."""

    def __init__(self, promotion_client: PromotionClient) -> None:
        self._client = promotion_client

    async def set_minus_phrases(
        self, advert_id: int, nm_id: int, phrases: list[str]
    ) -> None:
        from app.core.mp.wb.api.adapter.promotion_client.minus_phrases.post_adv_v0_normquery_set_minus.command import (
            SetMinusPhrasesCommand,
        )
        command = SetMinusPhrasesCommand(
            advert_id=advert_id, nm_id=nm_id, norm_queries=phrases
        )
        await request(
            self._client.minus_phrases_adapter.post_adv_v0_normquery_set_minus,
            command,
        )

    async def get_normquery_stats(
        self,
        complex_advs: list[ComplexAdv],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> List[NormqueryStatsDTO] | None:
        from .methods.get_normquery_stats import method

        result = await method.get_normquery_stats(
            self._client.normquery_stats_adapter,
            complex_advs,
            date_from,
            date_to,
        )
        return result

    async def get_normquery_bids(
        self,
        complex_advs: list[ComplexAdv],
    ) -> List[NormqueryBidDTO] | None:
        from .methods.get_current_bids import method

        return await method.get_current_bids(
            self._client.normquery_bids_adapter,
            complex_advs,
        )

    async def get_min_bids_for_complex_adv(
        self,
        complex_advs: list[ComplexAdv],
    ) -> AdvMinNmidsBids | None:
        """Получить минимальные ставки CPM (auto + search) для переданных РК."""
        from .methods.get_min_bids import method

        result = await method.get_min_bids(
            self._client.min_bids_adapter,
            complex_advs,
        )
        return result

    async def get_campaigns_info(
        self, complex_advs: list[ComplexAdv], *, get_auto: bool = True
    ) -> dict[int, "AdvInfoDTO"]:
        from .methods.get_campaigns_info import get_campaigns_info as method
        return await method(
            self._client.campaigns_info_v2_adapter,
            complex_advs,
            get_auto=get_auto,
        )

    async def set_cluster_bids(
        self,
        bids: list["SetNormqueryBidsCommandItem"],
    ) -> None:
        from .methods.set_cluster_bids import set_cluster_bids as method

        await method(self._client.normquery_bids_adapter, bids)

    async def patch_adv_bids(self, body: PatchAdvV0BidsBody) -> None:
        await self._client.campaigns_management_adapter.patch_adv_bids(body)

    async def set_common_bids(self, command: SetCommonBidsCommand) -> None:
        await self._client.common_bids_adapter.patch_common_bids(command)

    async def get_campaign_budget(self, adv_id: int) -> CampaignBudgetInfo:
        response = await self._client.finance_adapter.get_campaign_budget(adv_id)
        raw: dict[str, Any] = response.to_dict() if response else {}
        total = raw.get("total")
        return CampaignBudgetInfo(total=total if isinstance(total, int) else None, raw=raw)

    async def top_up_budget(
        self,
        adv_id: int,
        amount: int,
        balance_type: str,
        return_total: bool = True,
    ) -> BudgetTopUpResult:
        response = await self._client.finance_adapter.top_up_budget(
            adv_id=adv_id,
            amount=amount,
            balance_type=balance_type,
            return_total=return_total,
        )
        raw: dict[str, Any] = response.to_dict() if response else {}
        total = raw.get("total")
        return BudgetTopUpResult(total=total if isinstance(total, int) else None, raw=raw)

    async def get_campaign_balance(self) -> GetAdvV1BalanceResponse200 | None:
        return await self._client.finance_adapter.get_campaign_balance()

    async def start_campaign(self, advert_id: int) -> None:
        """Запустить рекламную кампанию WB."""
        await start_adv_method(
            self._client.campaigns_management_adapter,
            adv_id=advert_id,
        )

    async def pause_campaign(self, advert_id: int) -> None:
        """Приостановить рекламную кампанию."""
        await pause_adv_method(
            self._client.campaigns_management_adapter,
            adv_id=advert_id,
        )

    async def stop_campaign(self, advert_id: int) -> None:
        """Остановить рекламную кампанию окончательно."""
        await stop_adv_method(
            self._client.campaigns_management_adapter,
            adv_id=advert_id,
        )

    async def rename_campaign(self, advert_id: int, new_name: str) -> None:
        """Переименовать рекламную кампанию WB."""
        await rename_adv_method(
            self._client.campaigns_management_adapter,
            adv_id=advert_id,
            new_name=new_name,
        )
