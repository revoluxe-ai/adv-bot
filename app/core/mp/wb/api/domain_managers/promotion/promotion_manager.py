from dataclasses import dataclass
import json
import logging
import re
from typing import Any, cast
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
from app.core.mp.wb.api.excs import BadRequestError
from app.core.mp.wb.api.adapter.promotion_client.min_bids.command import (
    GetMinBidsCommand,
)
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


logger = logging.getLogger(__name__)

@dataclass(slots=True)
class CampaignBudgetInfo:
    total: int | None
    raw: dict[str, Any]


@dataclass(slots=True)
class BudgetTopUpResult:
    total: int | None
    raw: dict[str, Any]


@dataclass(slots=True, frozen=True)
class SetMinusPhrasesFallbackResult:
    """Результат set-minus с пошаговым отбрасыванием невалидных norm_query.

    Attributes:
        applied_phrases: Фразы, успешно отправленные в WB.
        dropped_invalid_phrases: Отброшенные WB как невалидные для nmid.
        attempts: Число попыток POST set-minus.
        skipped_unsupported_campaign: True, если WB ответил 400 «manual bid,
            search placement only» — тип/размещение РК не поддерживает normquery.
            Вызывающий код не должен падать; для auto non-search это ожидаемо
            при отсутствии раннего skip в ``MinusPhraseManager``.
    """

    applied_phrases: list[str]
    dropped_invalid_phrases: list[str]
    attempts: int
    skipped_unsupported_campaign: bool = False


_UNSUPPORTED_NORMQUERY_MINUS_MESSAGE = (
    "only for campaigns with manual bid, search placement"
)

_INVALID_NORM_QUERY_PATTERNS = (
    re.compile(r"norm_query\s+'(.+?)'\s+is not valid for nm\s+\d+"),
    re.compile(r'norm_query\s+"(.+?)"\s+is not valid for nm\s+\d+'),
    re.compile(r"norm_query\s+'(.+?)'\s+is not valid for nm"),
    re.compile(r'norm_query\s+"(.+?)"\s+is not valid for nm'),
)


def _extract_invalid_norm_query(detail: str | None) -> str | None:
    if not isinstance(detail, str):
        return None
    payload: dict[str, Any] | None = None
    try:
        loaded_payload = json.loads(detail)
        if isinstance(loaded_payload, dict):
            payload = cast(dict[str, Any], loaded_payload)
    except json.JSONDecodeError:
        pass

    message = detail
    if payload is not None:
        parsed_detail = payload.get("detail")
        if isinstance(parsed_detail, str):
            message = parsed_detail

    for pattern in _INVALID_NORM_QUERY_PATTERNS:
        match = pattern.search(message)
        if match is None:
            continue
        invalid_phrase = match.group(1).strip()
        if invalid_phrase:
            return invalid_phrase
    return None


def _is_unsupported_campaign_for_normquery_minus(detail: str | None) -> bool:
    """True, если WB отклонил set-minus из-за типа/размещения кампании.

    Текст ошибки: ``only for campaigns with manual bid, search placement``.
    Возникает для полочной/unified auto и любой РК без manual+search.

    Страховочный слой, если ``MinusPhraseManager`` не сделал ранний skip
    (auto-ветка пропускает только ``wb_is_manual_shelf_only``, не все auto).
    """
    if not isinstance(detail, str):
        return False
    message = detail
    payload: dict[str, Any] | None = None
    try:
        loaded_payload = json.loads(detail)
        if isinstance(loaded_payload, dict):
            payload = cast(dict[str, Any], loaded_payload)
    except json.JSONDecodeError:
        pass
    if payload is not None:
        parsed_detail = payload.get("detail")
        if isinstance(parsed_detail, str):
            message = parsed_detail
    return _UNSUPPORTED_NORMQUERY_MINUS_MESSAGE in message


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

    async def set_minus_phrases_with_fallback(
        self,
        advert_id: int,
        nm_id: int,
        phrases: list[str],
        *,
        max_attempts: int | None = None,
    ) -> SetMinusPhrasesFallbackResult:
        """POST normquery set-minus с отбрасыванием невалидных фраз по одной.

        Два вида BadRequestError обрабатываются по-разному:

        1. **Unsupported campaign** (не manual+search) — warning, возврат с
           ``skipped_unsupported_campaign=True``, без raise. См. docstring
           ``MinusPhraseManager._update_minuses_in_auto_adv`` про asymmetry skip.
        2. **Invalid norm_query** для nmid — фраза удаляется из списка, retry.

        Side effects: вызов WB API ``POST /adv/v0/normquery/set-minus``.
        """
        active_phrases = list(dict.fromkeys(phrases))
        dropped_invalid_phrases: list[str] = []
        # Максимум одна "полезная" попытка на каждую уникальную фразу
        # плюс финальная попытка после удалений.
        effective_max_attempts = (
            max_attempts if max_attempts is not None else len(active_phrases) + 1
        )

        for attempt in range(1, effective_max_attempts + 1):
            try:
                await self.set_minus_phrases(advert_id, nm_id, active_phrases)
                return SetMinusPhrasesFallbackResult(
                    applied_phrases=active_phrases,
                    dropped_invalid_phrases=dropped_invalid_phrases,
                    attempts=attempt,
                )
            except BadRequestError as exc:
                if _is_unsupported_campaign_for_normquery_minus(exc.detail):
                    logger.warning(
                        "normquery set-minus не поддерживается для advert_id=%s nm_id=%s: %s",
                        advert_id,
                        nm_id,
                        exc.detail,
                    )
                    return SetMinusPhrasesFallbackResult(
                        applied_phrases=[],
                        dropped_invalid_phrases=[],
                        attempts=attempt,
                        skipped_unsupported_campaign=True,
                    )
                invalid_phrase = _extract_invalid_norm_query(exc.detail)
                if invalid_phrase is None or invalid_phrase not in active_phrases:
                    raise
                active_phrases = [p for p in active_phrases if p != invalid_phrase]
                dropped_invalid_phrases.append(invalid_phrase)
                continue
        raise BadRequestError(
            "Max attempts reached for set_minus_phrases_with_fallback "
            f"advert_id={advert_id} nm_id={nm_id} attempts={effective_max_attempts}"
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

    async def get_min_bids_for_command(
        self,
        command: GetMinBidsCommand,
    ) -> AdvMinNmidsBids | None:
        """Минимальные ставки по уже собранной команде (например урезанной по кешу)."""
        from .methods.get_min_bids import method

        return await method.get_min_bids_for_command(
            self._client.min_bids_adapter,
            command,
        )

    async def get_min_bids_per_command_item(
        self,
        command: GetMinBidsCommand,
    ) -> list[AdvMinNmidsBids] | None:
        """Минимальные ставки отдельно по каждому item команды (без слияния dict по nmid)."""
        from .methods.get_min_bids import method

        return await method.get_min_bids_per_command_item(
            self._client.min_bids_adapter,
            command,
        )

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
        cashback_sum: int | None = None,
        cashback_percent: int | None = None,
    ) -> BudgetTopUpResult:
        response = await self._client.finance_adapter.top_up_budget(
            adv_id=adv_id,
            amount=amount,
            balance_type=balance_type,
            return_total=return_total,
            cashback_sum=cashback_sum,
            cashback_percent=cashback_percent,
        )
        raw: dict[str, Any] = response.to_dict() if response else {}
        total = raw.get("total")
        return BudgetTopUpResult(total=total if isinstance(total, int) else None, raw=raw)

    async def get_campaign_balance(self) -> GetAdvV1BalanceResponse200 | None:
        return await self._client.finance_adapter.get_campaign_balance()

    async def get_costs_history(
        self,
        *,
        from_date: datetime.date,
        to_date: datetime.date,
    ) -> list[Any]:
        """Фактические списания с бюджета кампаний WB (УПД), не аналитический spend.

        Это не ClickHouse-статистика показов/кликов и не live ``GET /adv/v1/budget``
        (там только fungible ``total``). WB отдаёт бухгалтерские строки начисления
        за период: сколько списали с конкретной кампании и **с какого кошелька**.

        Поле ``paymentType`` (v1: ``Keshbek`` / ``Balans`` / ``Bonusy`` / ``Schet``;
        в более новых версиях API встречается ``Кэшбэк``) — источник денег.
        Для promo remaining учитываются только строки кэшбэка; этот метод **не
        фильтрует** типы: фильтр делает ``iter_promo_upd_items``.

        Read-only WB API. Вызывающий путь: ``PromoStateService.refresh`` → ingest
        в ``WBCampaignPromoSpend``.

        Args:
            from_date: начало периода ``from`` в ``GET /adv/v1/upd``.
            to_date: конец периода ``to``.

        Returns:
            Список ``GetAdvV1UpdResponse200Item`` (advertId, updSum, paymentType,
            updTime, updNum). Пустой список при неожиданном ответе WB.
        """
        return await self._client.finance_adapter.get_costs_history(
            from_date=from_date,
            to_date=to_date,
        )

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

    async def discover_cabinet_campaigns(self) -> list[GetAdvertsAdvertsItem]:
        """WB discovery всех кампаний кабинета для shop-wide collection tick (design L1).

        Использует promotion_count + campaigns_info_v2 — тот же источник id, что
        ``get_connect_existing_candidates`` и ``update_advs_data_from_wb_to_pg``.
        """
        adv_ids = await self._client.promotion_count_adapter.get_cabinet_adv_ids()
        adapter = self._client.campaigns_info_v2_adapter
        if adv_ids:
            return await adapter.get_campaigns_info(adv_ids)
        return await adapter.get_all_campaigns()

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
