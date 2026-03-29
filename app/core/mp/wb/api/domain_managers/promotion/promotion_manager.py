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
from app.modules.full_stat_adv_updater.full_adv_stat_utils import (
    filter_full_adv_stat_to_dates,
    requested_dates_are_contiguous,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv
from app.core.mp.wb.api.adapter.promotion_client.common_bids.command import (
    SetCommonBidsCommand,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    GetAdvV1BalanceResponse200,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvertsAdvertsItem,
    GetAdvV1SupplierSubjectsResponse200Type0Item,
    PatchApiAdvertV1BidsBody,
    PostAdvV2SupplierNmsResponse200Item,
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

    async def get_minus_phrases(self, advert_id: int, nm_id: int) -> list[str]:
        """Получить список минус-фраз для пары кампания + номенклатура (POST /adv/v0/normquery/get-minus)."""
        from .methods.get_minus_phrases import method

        return await method.get_minus_phrases(
            self._client.minus_phrases_adapter, advert_id, nm_id
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

    async def get_full_adv_stat(
        self,
        adv_ids: list[int],
        dates: list[datetime.date],
    ) -> list[FullAdvStat]:
        """Полная статистика кампаний за указанные даты (GET /adv/v3/fullstats)."""
        if not dates:
            return []
        begin_date = min(dates)
        end_date = max(dates)
        stats = await self._client.fullstats_adapter.get_full_adv_stat(
            adv_ids, begin_date, end_date
        )
        if not requested_dates_are_contiguous(dates):
            stats = filter_full_adv_stat_to_dates(stats, dates)
        return stats

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

    async def patch_adv_v1_bids(self, body: PatchApiAdvertV1BidsBody) -> None:
        await self._client.campaigns_management_adapter.patch_adv_v1_bids(body)

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

    async def get_adverts_v2_by_ids(self, adv_ids: list[int]) -> list[GetAdvertsAdvertsItem]:
        """Сырые элементы GET /api/advert/v2/adverts по числовым id (не путать с get_campaigns_info)."""
        return await self._client.campaigns_info_v2_adapter.get_campaigns_info(adv_ids)

    async def get_campaign_status(self, adv_id: int) -> int | None:
        """Статус кампании на WB (например 7=завершена) или None, если не найдена.

        None возвращается, когда GET /api/advert/v2/adverts?ids=<adv_id> отдаёт пустой список.
        Мы не передаём параметр statuses — фильтрации по статусу с нашей стороны нет.
        Пустой ответ возможен: кампания удалена; или WB по своему правилу не возвращает
        часть кампаний (например, завершённые) при запросе по ids — зависит от API WB.
        """
        campaigns = await self.get_adverts_v2_by_ids([adv_id])
        if not campaigns:
            return None
        return int(campaigns[0].status)

    async def get_connect_existing_candidates(
        self, nmid: int, extra_adv_ids: list[int] | None = None
    ):
        """Кандидаты для подключения существующих РК по nmid (аукцион + авто).

        Используется тот же источник id, что и для регулярного обновления (update_advs_data_from_wb_to_pg):
        1) GET /adv/v1/promotion/count (promotion_count) — список id кампаний типа 8 и 9.
        2) GET /api/advert/v2/adverts (campaigns_info_v2) — полная инфа по id.
        extra_adv_ids: id из БД по этому артикулу — добавляем к списку на случай рассинхрона.
        """
        from app.modules.connect_existing_advs.candidates_service import (
            filter_and_classify_campaigns_by_nmid,
        )

        adv_ids = await self._client.promotion_count_adapter.get_cabinet_adv_ids()
        if extra_adv_ids:
            adv_ids = list(set(adv_ids) | set(extra_adv_ids))
        if adv_ids:
            campaigns = await self._client.campaigns_info_v2_adapter.get_campaigns_info(
                adv_ids
            )
        else:
            campaigns = await self._client.campaigns_info_v2_adapter.get_all_campaigns()
        return filter_and_classify_campaigns_by_nmid(campaigns, nmid)

    async def rename_campaign(self, advert_id: int, new_name: str) -> None:
        """Переименовать рекламную кампанию WB."""
        await rename_adv_method(
            self._client.campaigns_management_adapter,
            adv_id=advert_id,
            new_name=new_name,
        )

    async def set_auction_placement(
        self, adv_id: int, *, search: bool = True, recommendations: bool = False
    ) -> None:
        """Установить размещение для поисковой (аукционной) кампании (поиск / рекомендации)."""
        await self._client.campaigns_management_adapter.put_auction_placements(
            adv_id, search=search, recommendations=recommendations
        )

    async def get_supplier_subjects(
        self,
        payment_type: str = "cpm",
    ) -> list[GetAdvV1SupplierSubjectsResponse200Type0Item] | None:
        """
        Получить список предметов (категорий) поставщика для рекламы.

        Возвращает предметы, по которым у поставщика есть карточки товаров,
        доступные для добавления в рекламные кампании. Используется для
        фильтрации и отображения товаров по категориям при настройке рекламы.

        Args:
            payment_type: Тип оплаты рекламы, например "cpm". По умолчанию "cpm".

        Returns:
            Список объектов с полями id (идентификатор предмета), name (название),
            count (количество артикулов WB с данным предметом). None при ошибке
            или пустом ответе.
        """
        return await self._client.product_cards_adapter.get_supplier_subjects(
            payment_type=payment_type,
        )

    async def get_supplier_nms_available_for_adv(
        self,
        nm_ids: list[int],
    ) -> list[PostAdvV2SupplierNmsResponse200Item] | None:
        """
        Проверить, какие номенклатуры доступны для добавления в рекламные кампании.

        По переданному списку nm_id возвращает только те карточки поставщика,
        которые можно добавить в рекламу (все кампании). Остальные номенклатуры
        в ответ не входят.

        Args:
            nm_ids: Список номенклатурных идентификаторов (nm_id) для проверки.

        Returns:
            Список карточек с полями title (название), nm (артикул WB),
            subject_id (идентификатор предмета). None при ошибке. При слишком
            большом списке или невалидных данных API может вернуть 400 или 429 —
            адаптер пробрасывает BadRequestError или TooManyRequests (лимит:
            5 запросов в минуту, интервал 12 с).
        """
        return await self._client.product_cards_adapter.post_supplier_nms(
            body=nm_ids,
        )

    async def get_nms_available_to_add_to_auto_campaign(
        self,
        adv_id: int,
    ) -> list[int] | None:
        """
        Получить список nm_id, доступных для добавления в авторекламу по кампании.

        По идентификатору кампании авторекламы возвращает номенклатуры, которые
        ещё можно добавить в эту кампанию (карточки с единой ставкой).

        Args:
            adv_id: Идентификатор рекламной кампании (автореклама).

        Returns:
            Список номенклатурных идентификаторов (nm_id). None при ошибке или
            пустом ответе.

        Note:
            В документации WB метод помечен как устаревающий; запланировано
            удаление (см. release notes WB).
        """
        return await self._client.product_cards_adapter.get_auto_nms_to_add(
            adv_id=adv_id,
        )
