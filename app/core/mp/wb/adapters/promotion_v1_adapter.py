import asyncio
import logging
from typing import Dict, List

from app.core.mp.wb.generated.promotion.v1.client.api.kampanii.get_adv_v0_auction_adverts import \
    asyncio_detailed as get_adv_v0_auction_adverts_async_detailed
from app.core.mp.wb.generated.promotion.v1.client.api.sozdanie_kampanij.post_adv_v0_bids_min import \
    asyncio_detailed as post_adv_v0_bids_min_async_detailed
from app.core.mp.wb.generated.promotion.v1.client.api.upravlenie_kampanijami.patch_adv_v0_bids import \
    asyncio_detailed as patch_adv_v0_bids_async_detailed
from app.core.mp.wb.generated.promotion.v1.client.models.get_adv_v0_auction_adverts_payment_type import (
    GetAdvV0AuctionAdvertsPaymentType,
)
from app.core.mp.wb.generated.promotion.v1.client.models.patch_adv_v0_bids_body import PatchAdvV0BidsBody
from app.core.mp.wb.generated.promotion.v1.client.models.post_adv_v0_bids_min_body import PostAdvV0BidsMinBody
from app.core.mp.wb.generated.promotion.v1.client.models.post_adv_v0_bids_min_body_payment_type import (
    PostAdvV0BidsMinBodyPaymentType,
)
from app.core.mp.wb.generated.promotion.v1.client.models.post_adv_v0_bids_min_body_placement_types_item import (
    PostAdvV0BidsMinBodyPlacementTypesItem,
)
from app.core.mp.wb.token_refresh_decorator import token_refresh_decorator

logger = logging.getLogger(__name__)


class _WBHttpError(Exception):
    def __init__(self, status_code: int, message: str = ""):
        super().__init__(message or f"WB HTTP error {status_code}")
        self.status_code = status_code


class PromotionV1Adapter:
    def __init__(self, promotion_client_factory):
        self._promotion_client_factory = promotion_client_factory  # UniversalClientFactory для promotion

    @property
    def client_factory(self):
        """
        Возвращает фабрику клиента для раздела promotion.
        Можно расширить для других адаптеров/разделов.
        """
        return self._promotion_client_factory

    async def _retry_call(self, *, coro_factory, attempts: int, backoffs: List[float], op_name: str):
        last_exc: Exception | None = None
        for i in range(attempts):
            try:
                return await coro_factory()
            except asyncio.TimeoutError as e:
                logger.error(f"API attempt {i + 1}/{attempts} failed (timeout) in {op_name}: {e}")
                last_exc = e
            except _WBHttpError as e:
                # 5xx/429/400 будем ретраить; 401 обрабатывается декоратором и сюда не попадает
                if 500 <= e.status_code < 600 or e.status_code == 429:
                    logger.error(
                        f"API attempt {i + 1}/{attempts} failed ({e.status_code}) in {op_name}: {e}"
                    )
                    last_exc = e
                else:
                    # Прочие коды — не ретраим
                    last_exc = e
                    break
            except Exception as e:
                logger.error(f"API attempt {i + 1}/{attempts} failed in {op_name}: {e}")
                last_exc = e
            if i < attempts - 1:
                await asyncio.sleep(backoffs[i])
        # исчерпали попытки
        logger.critical(f"API failed after {attempts} attempts in {op_name}: {last_exc}")
        if last_exc:
            raise last_exc
        raise RuntimeError(f"API failed after {attempts} attempts in {op_name}")

    @token_refresh_decorator
    async def get_min_bids(
            self,
            shop_id: str,
            *,
            client,
            adv_id: int,
            nmids: list[int],
            timeout: float = 5.0,
    ) -> Dict[int, int]:
        """
        Получить минимальные ставки для списка nmids в рамках кампании.
        Возвращает словарь nmid -> min_bid.
        """
        body = PostAdvV0BidsMinBody(
            advert_id=int(adv_id),
            nm_ids=[int(x) for x in nmids],
            payment_type=PostAdvV0BidsMinBodyPaymentType.CPM,
            placement_types=[PostAdvV0BidsMinBodyPlacementTypesItem.SEARCH],
        )

        async def _call():
            resp = await asyncio.wait_for(
                get_adv_v0_bids_min := post_adv_v0_bids_min_async_detailed(client=client, body=body),
                timeout=timeout,
            )
            status = int(resp.status_code)
            if status == 200 and resp.parsed:
                result: Dict[int, int] = {}
                for item in resp.parsed.bids:
                    nm = int(item.nm_id)
                    # ищем ставку по зоне поиска
                    min_value = None
                    for zone in item.bids:
                        if getattr(zone.type_, "value", getattr(zone.type_, "name", "")).lower() == "search":
                            min_value = int(zone.value)
                            break
                    if min_value is not None:
                        result[nm] = min_value
                return result
            if status == 401:
                raise _WBHttpError(401, "Unauthorized")
            # 4xx/5xx
            raise _WBHttpError(status, f"Unexpected status for min bids: {status}")

        return await self._retry_call(
            coro_factory=_call, attempts=3, backoffs=[0.5, 1.0, 2.0], op_name="get_min_bids"
        )

    @token_refresh_decorator
    async def get_current_bids(
            self,
            shop_id: str,
            *,
            client,
            adv_id: int,
            nmids: list[int],
            timeout: float = 5.0,
    ) -> Dict[int, int]:
        """
        Получить текущие ставки для ручной кампании в зоне поиска.
        Если кампания не ручная или ставка отсутствует, возвращает пустой словарь.
        По ТЗ — одна ставка маппится на все переданные nmids.
        """
        ids_param = ",".join([str(int(adv_id))])

        async def _call():
            resp = await asyncio.wait_for(
                get_adv_v0_auction_adverts_async_detailed(
                    client=client,
                    ids=ids_param,
                    payment_type=GetAdvV0AuctionAdvertsPaymentType.CPM,
                ),
                timeout=timeout,
            )
            status = int(resp.status_code)
            if status == 200 and resp.parsed and resp.parsed.adverts:
                adverts = resp.parsed.adverts
                manual_bid: int | None = None
                for adv in adverts:
                    if int(adv.id) == int(adv_id):
                        # возьмем ставку из первого товара (по опыту для ручной кампании одинаковая для всех)
                        if adv.nm_settings:
                            try:
                                manual_bid = int(adv.nm_settings[0].bids.search)
                            except Exception:
                                manual_bid = None
                        break
                if manual_bid is None:
                    return {}
                return {int(nm): manual_bid for nm in nmids}
            if status == 401:
                raise _WBHttpError(401, "Unauthorized")
            # 4xx/5xx
            raise _WBHttpError(status, f"Unexpected status for current bids: {status}")

        return await self._retry_call(
            coro_factory=_call, attempts=3, backoffs=[0.5, 1.0, 2.0], op_name="get_current_bids"
        )

    @token_refresh_decorator
    async def update_bids(
            self,
            shop_id: str,
            *,
            client,
            payload: PatchAdvV0BidsBody,
            timeout: float = 10.0,
    ) -> None:
        """
        Отправляет ставки пачкой согласно контракту PatchAdvV0BidsBody.
        Ретраи 3 раза с backoff, 401 — через декоратор.
        """

        async def _call():
            resp = await asyncio.wait_for(
                patch_adv_v0_bids_async_detailed(client=client, body=payload),
                timeout=timeout,
            )
            status = int(resp.status_code)
            if status in (200, 204):
                return None
            if status == 401:
                raise _WBHttpError(401, "Unauthorized")
            if status == 429:
                raise _WBHttpError(429, "Too Many Requests")
            if 500 <= status < 600:
                raise _WBHttpError(status, f"Server error {status}")
            # 4xx прочее — считаем ошибкой
            raise _WBHttpError(status, f"Unexpected status for update bids: {status}")

        await self._retry_call(
            coro_factory=_call, attempts=3, backoffs=[0.5, 1.0, 2.0], op_name="update_bids"
        )
