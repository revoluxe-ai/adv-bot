"""Доменный модификатор WB Promotion API для shop-runner и бота.

Auto PATCH ставок (``update_auto_adv_cpm``, ``patch_auto_adv_bids_kopecks``):
см. блок «Auto bid placement» ниже и ``_patch_auto_adv_with_placement_strategy``.
Аукционная общая ставка — ``update_search_adv_common_cpm`` / ``set_common_bids`` (``search``).
"""

from __future__ import annotations

import datetime
import json
import logging
import typing
from collections.abc import Awaitable
from typing import Callable

from app.core.mp.wb.api.excs import BadRequestError


from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager
from app.shared.domains.wb.enums import AdvType
from app.core.mp.wb.api.adapter.promotion_client.common_bids.command import (
    SetCommonBidsCommand,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PatchApiAdvertV1BidsBody,
    PatchApiAdvertV1BidsBodyBidsItem,
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItem,
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auto bid placement (PATCH /api/advert/v1/bids, только auto-РК)
# ---------------------------------------------------------------------------
# Допустимые placement для auto: ``combined`` (unified) и ``recommendations`` (manual
# полка). ``search`` — только аукцион (``set_common_bids``, AdvType.SEARCH).
#
# 1) v2/adverts вернул ``bid_type=unified`` → один PATCH ``combined``.
#    v2 вернул ``bid_type=manual`` → один PATCH ``recommendations``.
#    Если WB отклонил placement (400) — **ошибка наружу, без второй попытки**.
#    Это намеренно: v2 считается источником правды; silent fallback маскирует
#    рассинхрон данных и неверную конфигурацию РК.
#
# 2) v2 miss (пустой ответ) или неизвестный ``bid_type`` → retry по порядку:
#    ``combined`` → ``recommendations``; только на placement-400 из
#    ``_AUTO_BID_PLACEMENT_ERROR_MARKERS``. Иная 400 — сразу raise. Обе попытки
#    failed → raise последней BadRequestError.
# ---------------------------------------------------------------------------

_AUTO_BID_PLACEMENT_RETRY_ORDER: tuple[
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement, ...
] = (
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED,
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS,
)

_AUTO_BID_PLACEMENT_ERROR_MARKERS: tuple[str, ...] = (
    "invalid target type recom",
    "combined placement is disabled",
)


def _bad_request_message(detail: str | None) -> str:
    """Извлечь текст ошибки WB из ``BadRequestError.detail`` (JSON или plain)."""
    if not isinstance(detail, str):
        return ""
    message = detail
    try:
        loaded = json.loads(detail)
        if isinstance(loaded, dict):
            parsed_detail = loaded.get("detail") # pyright: ignore
            if isinstance(parsed_detail, str):
                message = parsed_detail
    except json.JSONDecodeError:
        pass
    return message.lower()


def _is_auto_bid_placement_error(exc: BadRequestError) -> bool:
    """True, если WB отклонил PATCH из-за неверного auto-placement (combined/recom).

    ``search`` не используется для auto — не распознаём ``invalid target type search``.
    """
    message = _bad_request_message(exc.detail)
    return any(marker in message for marker in _AUTO_BID_PLACEMENT_ERROR_MARKERS)


if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.domain_managers.promotion import (
        PromotionManager,
        CampaignBudgetInfo,
        BudgetTopUpResult,
        SetMinusPhrasesFallbackResult,
    )
    from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
        GetAdvV1BalanceResponse200,
    )
    from app.core.mp.wb.api.domain_managers.promotion import PromotionManager
    from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.command import (
        SetNormqueryBidsCommandItem,
    )
    from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
        UpdateBidsCommand,
    )



class WBModifier:
    def __init__(self, promotion_manager: "PromotionManager") -> None:
        self._promotion_manager: "PromotionManager" = promotion_manager


    async def set_minus_phrases_with_fallback_for_adv(
        self,
        adv_id: int,
        nmid: int,
        phrases: list[str],
        update_redis_timestamp_manager: AdvActiveKeywordUpdateStateManager,
    ) -> "SetMinusPhrasesFallbackResult":
        try:
            result = await self._promotion_manager.set_minus_phrases_with_fallback(
                advert_id=adv_id,
                nm_id=nmid,
                phrases=phrases,
            )
        except Exception as e:
            logger.error("Ошибка обновления минус-фраз: %s", e, exc_info=True)
            raise e
        if not result.skipped_unsupported_campaign:
            await update_redis_timestamp_manager.set_one(adv_id=adv_id)
        return result

    async def get_minus_phrases_for_adv(self, adv_id: int, nmid: int) -> list[str]:
        """Получить текущий список минус-фраз для пары кампания + номенклатура."""
        return await self._promotion_manager.get_minus_phrases(
            advert_id=adv_id, nm_id=nmid
        )

    async def set_cluster_bids_for_adv(self, bids: "UpdateBidsCommand") -> None:
        """Устанавливает ставки по кластерам для РК.

        Args:
            bids: Список ставок. Каждый элемент содержит:
                - advert_id: ID рекламной кампании
                - nm_id: Артикул WB
                - norm_query: Поисковый кластер (фраза)
                - bid: Ставка за 1000 показов в рублях
        """
        from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.command import (
            SetNormqueryBidsCommandItem,
        )

        # Конвертируем NewBid в SetNormqueryBidsCommandItem
        converted_bids = [
            SetNormqueryBidsCommandItem(
                advert_id=bid.search_adv_id,
                nm_id=bid.nmid,
                norm_query=bid.cluster,
                bid=bid.new_bid,
            )
            for bid in bids.new_bids
        ]

        await self._promotion_manager.set_cluster_bids(converted_bids)
        return None

    async def set_normquery_bids(
        self,
        bids: list["SetNormqueryBidsCommandItem"],
    ) -> None:
        """Set bids for specific search normquery clusters via existing promotion flow."""
        await self._promotion_manager.set_cluster_bids(bids)
        return None

    async def update_auto_adv_cpm(
        self, adv_id: int, nm_bid_pairs: dict[int, int]
    ) -> None:
        """Обновляет CPM auto-РК через PATCH /api/advert/v1/bids (вход в рублях).

        Placement — ``_patch_auto_adv_with_placement_strategy`` (см. module docstring).
        При известном ``bid_type`` из v2 ошибка WB не перехватывается: caller должен
        увидеть сбой, если placement не подошёл.
        """
        if not nm_bid_pairs:
            return None
        nm_bid_kopecks = {
            int(nm_id): int(bid_rub * 100) for nm_id, bid_rub in nm_bid_pairs.items()
        }
        await self._patch_auto_adv_with_placement_strategy(adv_id, nm_bid_kopecks)
        return None

    async def _resolve_auto_adv_bid_placement(
        self, adv_id: int
    ) -> PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement | None:
        """Placement для auto PATCH по v2/adverts.

        Returns:
            ``combined`` для ``unified``, ``recommendations`` для ``manual`` —
            вызывающий код делает **один** PATCH без fallback.
            ``None`` если v2 miss или ``bid_type`` неизвестен — retry в
            ``_patch_auto_adv_with_placement_strategy``.

        Для auto допустимы только ``combined`` и ``recommendations``; ``search`` —
        аукционный путь (``set_common_bids`` / ``AdvType.SEARCH``).
        """
        campaigns = await self._promotion_manager.get_adverts_v2_by_ids([int(adv_id)])
        if not campaigns:
            logger.warning("auto_adv_bid_placement_v2_miss adv_id=%s", adv_id)
            return None

        bid_type = (getattr(campaigns[0], "bid_type", None) or "").lower()
        if bid_type == "unified":
            return PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED
        if bid_type == "manual":
            return PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.RECOMMENDATIONS

        logger.warning(
            "auto_adv_bid_placement_unknown_bid_type adv_id=%s bid_type=%s",
            adv_id,
            bid_type or "?",
        )
        return None

    async def _patch_auto_adv_v1_bids(
        self,
        adv_id: int,
        nm_bid_kopecks: dict[int, int],
        placement: PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement,
    ) -> None:
        """PATCH /api/advert/v1/bids для auto-РК с явным placement."""
        nm_bids = [
            PatchApiAdvertV1BidsBodyBidsItemNmBidsItem(
                nm_id=int(nm_id),
                bid_kopecks=int(kopecks),
                placement=placement,
            )
            for nm_id, kopecks in nm_bid_kopecks.items()
        ]
        body = PatchApiAdvertV1BidsBody(
            bids=[
                PatchApiAdvertV1BidsBodyBidsItem(
                    advert_id=int(adv_id),
                    nm_bids=nm_bids,
                )
            ]
        )
        await self._promotion_manager.patch_adv_v1_bids(body)

    async def _patch_auto_adv_with_placement_strategy(
        self,
        adv_id: int,
        nm_bid_kopecks: dict[int, int],
    ) -> None:
        """PATCH auto-ставки с выбором placement.

        Ветка A — v2 известен (``unified`` / ``manual``):
            Один PATCH с placement из ``_resolve_auto_adv_bid_placement``.
            ``BadRequestError`` пробрасывается без retry — нужна явная ошибка,
            если v2 и WB расходятся (не подменяем другим placement молча).

        Ветка B — v2 miss или неизвестный ``bid_type`` (resolver вернул ``None``):
            Перебор ``_AUTO_BID_PLACEMENT_RETRY_ORDER`` (combined → recommendations).
            Retry только при placement-400 (``_is_auto_bid_placement_error``).
            После двух неудач — raise последней ошибки.

        Side effects: WB API ``PATCH /api/advert/v1/bids``.
        """
        placement = await self._resolve_auto_adv_bid_placement(adv_id)
        if placement is not None:
            # Намеренно без try/retry: известный bid_type → fail loud.
            await self._patch_auto_adv_v1_bids(adv_id, nm_bid_kopecks, placement)
            return None

        last_exc: BadRequestError | None = None
        for attempt, candidate in enumerate(_AUTO_BID_PLACEMENT_RETRY_ORDER, start=1):
            try:
                await self._patch_auto_adv_v1_bids(adv_id, nm_bid_kopecks, candidate)
            except BadRequestError as exc:
                is_last = attempt >= len(_AUTO_BID_PLACEMENT_RETRY_ORDER)
                if not _is_auto_bid_placement_error(exc) or is_last:
                    raise
                last_exc = exc
                logger.warning(
                    "auto_adv_bid_placement_retry adv_id=%s placement=%s attempt=%s err=%s",
                    adv_id,
                    candidate.value,
                    attempt,
                    exc.detail,
                )
                continue
            logger.info(
                "auto_adv_bid_placement_retry_ok adv_id=%s placement=%s attempt=%s",
                adv_id,
                candidate.value,
                attempt,
            )
            return None

        if last_exc is not None:
            raise last_exc
        return None

    async def patch_auto_adv_bids_kopecks(
        self, adv_id: int, nm_bid_kopecks: dict[int, int]
    ) -> None:
        """PATCH /api/advert/v1/bids: ``nm_bid_kopecks`` уже в копейках (shelf control).

        Placement — ``_patch_auto_adv_with_placement_strategy``; при известном v2
        типе ошибка placement не глотается (см. module docstring).
        """
        if not nm_bid_kopecks:
            return None
        normalized = {
            int(nm_id): int(kopecks) for nm_id, kopecks in nm_bid_kopecks.items()
        }
        await self._patch_auto_adv_with_placement_strategy(adv_id, normalized)
        return None

    async def get_campaign_budget(self, adv_id: int) -> "CampaignBudgetInfo":
        return await self._promotion_manager.get_campaign_budget(adv_id)

    async def top_up_budget(
        self,
        adv_id: int,
        amount: int,
        balance_type: str,
        return_total: bool = True,
        cashback_sum: int | None = None,
        cashback_percent: int | None = None,
    ) -> "BudgetTopUpResult":
        return await self._promotion_manager.top_up_budget(
            adv_id=adv_id,
            amount=amount,
            balance_type=balance_type,
            return_total=return_total,
            cashback_sum=cashback_sum,
            cashback_percent=cashback_percent,
        )

    async def get_campaign_balance(self) -> typing.Union["GetAdvV1BalanceResponse200", None]:
        return await self._promotion_manager.get_campaign_balance()

    async def get_costs_history(
        self,
        *,
        from_date: datetime.date,
        to_date: datetime.date,
    ) -> list[typing.Any]:
        """Фактические списания с бюджета кампаний (УПД, ``GET /adv/v1/upd``).

        Не аналитический spend и не текущий budget.total: строки начисления
        с ``paymentType`` источника денег. Кэшбэк из ответа идёт в promo remaining;
        остальные типы здесь не отбрасываются.

        Args:
            from_date: начало периода.
            to_date: конец периода.

        Returns:
            Список UPD-items от ``FinanceAdapter.get_costs_history``.
        """
        return await self._promotion_manager.get_costs_history(
            from_date=from_date,
            to_date=to_date,
        )


    async def start_auto_campaign(self, complex_adv: ComplexAdv) -> None:
        """Запустить автоматическую кампанию для магазина."""
        await self.start_campaign_by_type(complex_adv, AdvType.AUTO)

    async def pause_auto_campaign(self, complex_adv: ComplexAdv) -> None:
        """Поставить на паузу автоматическую кампанию."""
        await self.pause_campaign_by_type(complex_adv, AdvType.AUTO)

    async def stop_auto_campaign(self, complex_adv: ComplexAdv) -> None:
        """Полностью остановить автоматическую кампанию."""
        await self.stop_campaign_by_type(complex_adv, AdvType.AUTO)

    async def start_auction_campaign(self, complex_adv: ComplexAdv) -> None:
        """Запустить аукционную кампанию по Cluster."""
        await self.start_campaign_by_type(complex_adv, AdvType.SEARCH)

    async def pause_auction_campaign(self, complex_adv: ComplexAdv) -> None:
        """Приостановить аукционную кампанию."""
        await self.pause_campaign_by_type(complex_adv, AdvType.SEARCH)

    async def stop_auction_campaign(self, complex_adv: ComplexAdv) -> None:
        """Остановить аукционную кампанию наверняка."""
        await self.stop_campaign_by_type(complex_adv, AdvType.SEARCH)

    async def start_campaign_by_type(
        self, complex_adv: ComplexAdv, adv_type: AdvType
    ) -> None:
        """Запустить кампанию заданного типа."""
        await self._control_campaign_by_type(
            complex_adv, adv_type, self._promotion_manager.start_campaign
        )

    async def pause_campaign_by_type(
        self, complex_adv: ComplexAdv, adv_type: AdvType
    ) -> None:
        """Поставить на паузу кампанию заданного типа."""
        await self._control_campaign_by_type(
            complex_adv, adv_type, self._promotion_manager.pause_campaign
        )

    async def stop_campaign_by_type(
        self, complex_adv: ComplexAdv, adv_type: AdvType
    ) -> None:
        """Остановить кампанию заданного типа."""
        await self._control_campaign_by_type(
            complex_adv, adv_type, self._promotion_manager.stop_campaign
        )

    async def rename_campaign(self, advert_id: int, new_name: str) -> None:
        """Переименовать рекламную кампанию по её ID."""
        await self._promotion_manager.rename_campaign(advert_id, new_name)

    async def rename_campaign_by_type(
        self, complex_adv: ComplexAdv, adv_type: AdvType, new_name: str
    ) -> None:
        """Переименовать кампанию заданного типа (авто или аукцион)."""
        adv_id = complex_adv.get_adv_id_by_type(adv_type)
        await self.rename_campaign(adv_id, new_name)

    @staticmethod
    async def _control_campaign_by_type(
        complex_adv: ComplexAdv,
        adv_type: AdvType,
        action: Callable[[int], Awaitable[None]],
    ) -> None:
        adv_id = complex_adv.get_adv_id_by_type(adv_type)
        await action(adv_id)

    async def update_search_adv_common_cpm(
        self, command: SetCommonBidsCommand
    ) -> None:
        await self._promotion_manager.set_common_bids(command)
