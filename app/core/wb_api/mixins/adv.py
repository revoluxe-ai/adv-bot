import asyncio
import datetime
import json
import logging
from json import JSONDecodeError
from typing import Any, TypeVar

from app.core.wb_api.protocols import WBAPIProtocol
from app.modules.common_slaves.wildberries.data_classes.adv import Adv
from app.modules.common_slaves.wildberries.data_classes.adv import Balances
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from .excs import (
    ItemCategoryNotInStockError,
    StartAdvError,
)
from ..data_classes.advs import adv_fabric
from ..data_classes.advs.auction_adv import AuctionAdv
from ..exceptions import BadRequestError, MinAdvBidWBApiError
from ..http_request import requests, try_except_decorator
from ..v2_adverts_to_legacy import v2_advert_item_to_legacy

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=WBAPIProtocol)


class MinCPMData:
    def __init__(self, api_answer: dict[str, Any]):
        category_id_to_min_cpm: dict[int, int] = {}
        category_name_to_min_cpm: dict[str, int] = {}

        for data in api_answer["categories"]:
            category_id = data["id"]
            category_name = data["name"]
            min_cpm = data["cpm_min"]
            category_id_to_min_cpm[category_id] = min_cpm
            category_name_to_min_cpm[category_name] = min_cpm

        self.category_id_to_min_cpm = category_id_to_min_cpm
        self.category_name_to_min_cpm = category_name_to_min_cpm

    def get_min_cpm_data_for_cagegory_name_match(self) -> dict[str, int]:
        return self.category_name_to_min_cpm


class AdvMixin(WBAPIProtocol):
    PREFIX = "https://advert-api"

    @try_except_decorator(1, 60)
    async def get_min_cpm_adv_data(self) -> MinCPMData:
        url = f"{self.PREFIX}.{self.HOST}/adv/v0/config"

        response_text = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        answer = json.loads(response_text)
        return MinCPMData(answer)

    @try_except_decorator(1, 3)
    async def get_advertIds(self: T) -> list[int]:
        advertIds: list[int] = []
        url = "https://advert-api.wildberries.ru/adv/v1/promotion/count"

        response_text: str = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        answer: dict[str, Any] = json.loads(response_text)

        adverts: list[dict[str, Any]] = answer.get("adverts", [])

        if not adverts:
            return []

        for advert in adverts:
            advert_type = advert.get("type")
            # Type 8 = auto (unified), type 9 = search (manual). Both needed for ComplexAdv (auto_adv_id + search_adv_id)
            if isinstance(advert_type, int) and advert_type in (8, 9):
                advert_list: list[dict[str, Any]] = advert.get("advert_list", [])
                for advert_item in advert_list:
                    advertId = advert_item["advertId"]
                    advertIds.append(advertId)

        return advertIds

    @try_except_decorator(1, 2)
    async def _get_advs(self, adv_ids: list[int]) -> list[Adv]:
        if not adv_ids:
            return []
        url = "https://advert-api.wildberries.ru/api/advert/v2/adverts"
        ids_param = ",".join(str(i) for i in adv_ids)

        response_text = await requests(
            self.session,
            "GET",
            f"{url}?ids={ids_param}",
            headers=self.headers.standart,
        )
        answer = json.loads(response_text)
        adverts_list = answer.get("adverts", [])
        advs: list[Adv] = []
        for item in adverts_list:
            legacy = v2_advert_item_to_legacy(item)
            adv = adv_fabric.get_adv_data_class(legacy)
            if adv is not None:
                advs.append(adv)
        return advs

    @try_except_decorator(1, 1)
    async def get_advs(self, adv_ids: list[int] | None = None) -> list[AuctionAdv]:
        if not adv_ids:
            adv_ids = await self.get_advertIds()
        all_advs = []
        part = 50
        for i in range(0, len(adv_ids), part):
            if i > 0:
                await asyncio.sleep(0.2)
            part_of_advs = adv_ids[i : i + part]
            advs = await self._get_advs(part_of_advs)
            if advs:
                all_advs.extend(advs)
        return all_advs

    async def create_auto_adv(self, nmids: list[int], adv_name: str) -> int:
        bid_type = "unified"
        placement_types = None
        adv_id = await self.__create_adv(
            name=adv_name,
            nmids=nmids,
            bid_type=bid_type,
            placement_types=placement_types,
        )
        return adv_id

    async def create_search_adv(self, nmids: list[int], adv_name: str) -> int:

        bid_type = "manual"
        placement_types = ["search"]
        adv_id = await self.__create_adv(
            name=adv_name,
            nmids=nmids,
            bid_type=bid_type,
            placement_types=placement_types,
        )
        # WB может не применить placement_types при создании — явно выставляем размещение «в поиске»,
        # иначе /adv/v0/bids вернёт "Auction campaigns with disabled search placement cannot be processed".
        await self.upcast_target_placement(adv_id, search=True, recommendations=False)
        return adv_id

    @try_except_decorator(1, 60)
    async def __create_adv(
        self,
        name: str,
        nmids: list[int],
        bid_type: str,
        placement_types: list[str] | None,
    ) -> int:

        url = "https://advert-api.wildberries.ru/adv/v2/seacat/save-ad"
        data = {
            "name": name,
            "nms": nmids,
            "bid_type": bid_type,
            "placement_types": placement_types,
        }

        response_text = await requests(
            self.session, "POST", url, json_data=data, headers=self.headers.standart
        )
        try:
            answer = json.loads(response_text)
        except JSONDecodeError as e:
            logger.error(
                "Ошибка декодирования JSON при создании РК: %s",
                response_text,
                exc_info=True,
            )
            raise e

        if isinstance(answer, int):
            return answer
        else:
            error_text = answer["error"]
            if (
                error_text == "Invalid Params or payload:"
                " Товары выбранной категории не в наличии, размещение невозможно"
            ):
                raise ItemCategoryNotInStockError()
            else:
                raise Exception("Неизвестная ошибка создания РК")

    @try_except_decorator(1, 20)
    async def check_balance(self, adv_id: int) -> dict[str, Any]:
        url = f"https://advert-api.wildberries.ru/adv/v0/get-balance/{adv_id}"

        response_text = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        answer = json.loads(response_text)
        return answer  # type: ignore[no-any-return]

    @try_except_decorator(1, 10)
    async def start_adv(self, adv_id: int) -> None:
        try:
            url = f"https://advert-api.wildberries.ru/adv/v0/start?id={adv_id}"

            response = await requests(
                self.session, "GET", url, headers=self.headers.standart
            )
            if response != "":
                raise StartAdvError()
        except Exception as exc:
            raise StartAdvError(
                f"Не удалось запустить компанию {adv_id}. Ошибка: {exc}"
            )

    @try_except_decorator(1, 10)
    async def get_adv_balances(self) -> Balances:
        url = "https://advert-api.wildberries.ru/adv/v1/balance"

        response = await requests(
            self.session, "GET", url=url, headers=self.headers.standart
        )
        response = json.loads(response)
        logger.debug(f"Ответ на получение баланса: {response}")
        balance = Balances(response)
        return balance

    @try_except_decorator(1, 1)
    async def rename_adv(self, adv_id: int, new_name: str) -> None:
        url = "https://advert-api.wildberries.ru/adv/v0/rename"

        data = {"advertId": adv_id, "name": new_name}

        await requests(
            self.session, "POST", url, json_data=data, headers=self.headers.standart
        )
        return None

    async def update_nmids_in_adv(
        self, adv_id: int, nmids_for_add: list[int], nmids_for_del: list[int]
    ) -> None:
        url = f"https://advert-api.wildberries.ru/adv/v1/auto/updatenm?id={adv_id}"
        data = {"add": nmids_for_add, "delete": nmids_for_del}

        await requests(
            self.session, "POST", url, json_data=data, headers=self.headers.standart
        )

    @try_except_decorator(1, 2)
    async def get_nmids_to_add(self, adv_id: int) -> list[int]:
        url = f"https://advert-api.wildberries.ru/adv/v1/auto/getnmtoadd?id={adv_id}"

        response_text = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        answer = json.loads(response_text)
        if answer is None:
            return []
        return answer  # type: ignore[no-any-return]

    @try_except_decorator(1, 2)
    async def update_nmids_in_auto_adv(
        self, adv_id: int, nmids_for_add: list[int], nmids_for_del: list[int]
    ) -> None:
        url = f"https://advert-api.wildberries.ru/adv/v1/auto/updatenm?id={adv_id}"
        data = {"add": nmids_for_add, "delete": nmids_for_del}

        await requests(
            self.session, "POST", url, json_data=data, headers=self.headers.standart
        )

    async def add_to_balance(self, adv_id: int, balance_type: int, sum_: int) -> int:
        url = f"https://advert-api.wildberries.ru/adv/v1/budget/deposit?id={adv_id}"

        data = {"sum": sum_, "type": balance_type, "return": True}

        response_text = await requests(
            self.session, "POST", url, json_data=data, headers=self.headers.standart
        )
        answer = json.loads(response_text)
        new_balance = answer["total"]
        return new_balance  # type: ignore[no-any-return]

    async def stop_adv(self, adv_id: int) -> None:
        url = f"https://advert-api.wildberries.ru/adv/v0/pause?id={adv_id}"

        await requests(self.session, "GET", url, headers=self.headers.standart)
        return None

    @try_except_decorator(1, 3)
    async def get_all_adv_ids(self) -> list[int]:
        advertIds = []
        url = "https://advert-api.wildberries.ru/adv/v1/promotion/count"

        response_text = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        answer = json.loads(response_text)
        # Используем json.loads для преобразования текста ответа в JSON
        adverts: list[dict[str, Any]] = answer["adverts"]
        if not adverts:
            return []
        for advert_data in adverts:
            if advert_data.get("type") not in (8, 9):
                continue
            for advert in advert_data["advert_list"]:
                advertId = advert["advertId"]
                advertIds.append(advertId)

        return advertIds

    def __get_update_cpm_data(
        self, adv_id: int, nmid: int, new_bid: int
    ) -> dict[str, Any]:
        data = {
            "bids": [
                {"advert_id": adv_id, "nm_bids": [{"nm": nmid, "bid": int(new_bid)}]}
            ]
        }
        return data

    @try_except_decorator(5, 60)
    async def update_cpm(self, adv_id: int, nmid: int, new_bid: int) -> None:
        url = "https://advert-api.wildberries.ru/adv/v0/bids"
        max_attempts = 2
        attempts = 0
        while True:
            data = self.__get_update_cpm_data(adv_id, nmid, new_bid)
            try:
                attempts += 1
                await requests(
                    self.session,
                    "PATCH",
                    url,
                    json_data=data,
                    headers=self.headers.standart,
                )
                break
            except MinAdvBidWBApiError as exc:
                if attempts >= max_attempts:
                    logger.error(
                        "Не удалось обновить ставку для {adv_id}, {nmid}, {new_bid}"
                    )
                    raise BadRequestError from exc
                new_bid = exc.new_min_bid
                await asyncio.sleep(1)
                continue
            except Exception as exc:
                raise exc

    @try_except_decorator(1, 1)
    async def set_search_cpm(self, search_adv_id: int, cpm: int) -> None:
        url = "https://advert-api.wildberries.ru/adv/v0/cpm"
        data = {"advertId": search_adv_id, "type": 9, "cpm": cpm}

        response = await requests(
            self.session, "POST", url, json_data=data, headers=self.headers.standart
        )
        if response == "":
            logger.debug(f"CPM для поисковой кампании {search_adv_id} установлен")
            return
        else:
            logger.error(
                f"Ошибка установки CPM для поисковой кампании {search_adv_id}, ответ: {response}"
            )

    async def get_adv_full_state(
        self, adv_ids: list[int], dates: list[datetime.date] | None = None
    ) -> list[FullAdvStat]:
        if not adv_ids:
            return []
        # Chunking by 50 is done inside _get_adv_full_state → fetch_fullstats_v3 → _fetch_single_range
        return (await self._get_adv_full_state(adv_ids, dates)) or []

    @try_except_decorator(1, 60)
    async def _get_adv_full_state(
        self, adv_ids: list[int], dates: list[datetime.date] | None = None
    ) -> list[FullAdvStat] | None:
        if not dates:
            return None
        assert [isinstance(dt, datetime.date) for dt in dates]
        assert [isinstance(adv_id, int) for adv_id in adv_ids]
        from app.modules.full_stat_adv_updater.fullstats_v3_legacy import (
            get_adv_full_state_for_dates,
        )

        return await get_adv_full_state_for_dates(
            self.session, self.headers.standart, adv_ids, dates
        )

    async def upcast_target_placement(
        self, adv_id: int, /, search: bool, recommendations: bool
    ) -> None:
        type_query = "PUT"
        url = "https://advert-api.wildberries.ru/adv/v0/auction/placements"
        data = {
            "placements": [
                {
                    "advert_id": adv_id,
                    "placements": {
                        "search": search,
                        "recommendations": recommendations,
                    },
                }
            ]
        }

        async with self.session.request(
            method=type_query, url=url, headers=self.headers.standart, json=data
        ) as response:
            if response.status not in (200, 204):
                response_text = await response.text()
                logger.error(
                    f"Ошибка при обновлении таргетинга размещений"
                    f" для РК {adv_id}: {response.status} - {response_text}"
                )
                raise Exception(
                    f"Ошибка при обновлении таргетинга размещений для РК {adv_id}"
                )
            else:
                logger.debug(
                    f"Таргетинг размещений для РК {adv_id} успешно обновлен: search={search},"
                    f" recommendations={recommendations}"
                )
