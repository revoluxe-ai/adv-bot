import asyncio
import datetime
import json
import logging
from collections.abc import Iterable

from aiohttp import ClientSession

from app.core.wb_api.base import BaseAPI
from app.core.wb_api.data_classes.advs import adv_fabric
from app.core.wb_api.http_request import requests, try_except_decorator
from app.core.wb_api.v2_adverts_to_legacy import v2_advert_item_to_legacy
from app.core.wb_api.mixins.content import ContentMixin
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat

from .. import api_rights
from ..ABC_WB_API import ABC_WB_API
from ..data_classes.adv import Adv
from ..data_classes.card_from_wb import CardFromWB
from ..data_classes.keywordstat import KeywordStat
from ..data_classes.subcategories import Subcategory
from ..exceptions import CardNotFoundInWB
from ..models import AdvSetting
from ..super_cabinet_manager import WBCabinetAccess

"""

Пример ответа от API по полной статистики рекламы:
[
{
"views": 1052,
"clicks": 2,
"ctr": 0.19,
"cpc": 0.09,
"sum": 177.7,
"atbs": 0,
"orders": 0,
"cr": 0,
"shks": 0,
"sum_price": 0,
"dates": [
"2023-10-07",
"2023-10-06"
],
"days": [
{
"date": "2023-10-06T03:00:00+03:00",
"views": 414,
"clicks": 1,
"ctr": 0.24,
"cpc": 70,
"sum": 70,
"atbs": 0,
"orders": 0,
"cr": 0,
"shks": 0,
"sum_price": 0,
"apps": []
}
],
"boosterStats": [
{
"date": "2023-10-07T00:00:00Z",
"nm": 170095908,
"avg_position": 348
}
],
"advertId": 10524818
}
]


"""


logger = logging.getLogger(__name__)


def escape_special_characters(text):
    text = text.replace('"', '"')  # Экранирование двойных кавычек
    # text = text.replace("'", "\\'")  # Экранирование одинарных кавычек
    text = text.replace("\t", "\\t")  # Экранирование табуляции
    text = text.replace("\n", "\\n")  # Экранирование новой строки
    return text


class AdvertApi(ABC_WB_API):
    _rights: set[str] = {api_rights.Rights.PROMOTION}
    _only_read = api_rights.OnlyRead.FALSE
    live_company_status = [4, 9, 11]
    auto_adv_types = [8, 9]

    # @try_except_decorator(1, 1)
    # async def get_search_keywords_stat(self, adv_id):
    #     url = f"https://advert-api.wildberries.ru/adv/v1/stat/words?id={adv_id}"
    #     async with aiohttp.ClientSession() as session:
    #         response_text = await requests(
    #           "GET", url, headers=self.headers.standart
    #         )
    #         answer = json.loads(response_text)
    #         keywords = []
    #         return keywords

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

    @try_except_decorator(1, 1)
    async def set_search_keywords(self, search_adv_id, texts):
        url = f"https://advert-api.wildberries.ru/adv/v1/search/set-plus?id={search_adv_id}"
        data = {"pluse": texts}
        await requests(
            self.session, "POST", url, json_data=data, headers=self.headers.standart
        )
        logger.debug("Плюс-фразы установлены")

    @try_except_decorator(1, 1)
    async def set_minus_phrase_for_search_adv(
        self, search_adv_id, texts: Iterable[str]
    ):
        url = f"https://advert-api.wildberries.ru/adv/v1/search/set-excluded?id={search_adv_id}"
        data = {"excluded": list(texts)}
        await requests(
            self.session, "POST", url, json_data=data, headers=self.headers.standart
        )
        logger.debug("Минус-фразы в Аукцион установлены")

    @try_except_decorator(1, 1)
    async def set_pluse_status_in_search_adv(self, adv_id: int, status: bool):
        status = "true" if status else "false"
        url = f"https://advert-api.wildberries.ru/adv/v1/search/set-plus?id={adv_id}&fixed={status}"
        response = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        logger.debug(f"Статус фиксированных фраз установлен: {response}")

    async def _get_adv_full_state(
        self, adv_ids: list[int], dates: list[datetime.date] = None
    ) -> list[FullAdvStat] | None:
        if not dates:
            return None
        from app.modules.full_stat_adv_updater.fullstats_v3_legacy import (
            fetch_fullstats_v3,
        )

        begin_date = min(dates)
        end_date = max(dates)
        headers = self.headers.standart
        stats = await fetch_fullstats_v3(
            self.session, headers, adv_ids, begin_date, end_date
        )
        return stats if stats else None

    @try_except_decorator(1, 60)
    async def get_adv_full_state(
        self, adv_ids: list[int], dates: list[datetime.date] = None
    ) -> list[FullAdvStat] | None:
        if not adv_ids:
            return []
        assert [isinstance(dt, datetime.date) for dt in dates]
        assert [isinstance(adv_id, int) for adv_id in adv_ids]
        # Chunking by 50 is done inside _get_adv_full_state → fetch_fullstats_v3 → _fetch_single_range
        return (await self._get_adv_full_state(list(adv_ids), dates)) or []

    async def get_full_adv_stat_for_date(
        self, adv_ids: list[int], date: datetime.date
    ) -> list[FullAdvStat]:
        return (await self.get_adv_full_state(adv_ids, [date])) or []

    @try_except_decorator(5, 60)
    async def get_keywords_stat(self, adv_id) -> list[KeywordStat]:
        keywords = []
        # Используем дату по московскому времени (UTC+3)
        moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
        date_now_msk = datetime.datetime.now(moscow_tz)
        date_to = date_now_msk.date()
        date_from = date_to - datetime.timedelta(days=6)
        url = f"https://advert-api.wildberries.ru/adv/v0/stats/keywords?advert_id={adv_id}&from={date_from}&to={date_to}"

        response_text = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        answer = json.loads(response_text)
        update_timestamp = datetime.datetime.now()
        if not answer:
            logger.debug("Нет данных по ключевым словам: %s", adv_id)
            return []
        for data in answer["keywords"]:
            wb_timestamp = datetime.datetime.fromisoformat(data["date"]).date()
            stat = data["stats"]
            for keyword_stat in stat:
                keyword_text = keyword_stat.pop("keyword")
                keyword_text = keyword_text.replace(r'"', "")
                keyword_text = keyword_text.replace("_", "")
                keyword_stat["date"] = wb_timestamp
                keyword_stat["update_timestamp"] = update_timestamp
                keyword_stat["adv_id"] = adv_id
                keyword_stat["text"] = keyword_text
                keyword_stat["spend"] = keyword_stat.pop("sum")
                keyword = KeywordStat(**keyword_stat)
                keywords.append(keyword)
        return keywords

    @try_except_decorator(2, 1)
    async def get_keywords_stat_depr(
        self, adv_setting: AdvSetting
    ) -> list[KeywordStat]:
        keywords = []
        url = f"https://advert-api.wildberries.ru/adv/v2/auto/daily-words?id={adv_setting.adv_id}"

        response_text = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )

        response_text = escape_special_characters(response_text)
        answer = json.loads(response_text)
        update_timestamp = datetime.datetime.now()
        if not answer:
            logger.debug("Нет данных по ключевым словам: %s", adv_setting.name)
            return []
        for data in answer:
            wb_timestamp = datetime.datetime.fromisoformat(data["date"]).date()
            stat = data["stat"]
            for keyword_stat in stat:
                keyword_text = keyword_stat.pop("keyword")
                keyword_text = keyword_text.replace(r'"', "")
                keyword_text = keyword_text.replace("_", "")
                keyword_stat["date"] = wb_timestamp
                keyword_stat["update_timestamp"] = update_timestamp
                keyword_stat["adv_id"] = adv_setting.adv_id
                keyword_stat["text"] = keyword_text
                keyword_stat["spend"] = keyword_stat.pop("sum")
                keyword = KeywordStat(**keyword_stat)
                keywords.append(keyword)
        keywords.sort(key=lambda x: x.date)
        return keywords

    @try_except_decorator(1, 3)
    async def get_advertIds(self) -> list[int]:
        advertIds = []
        url = "https://advert-api.wildberries.ru/adv/v1/promotion/count"

        response_text = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        answer = json.loads(response_text)
        # Используем json.loads для преобразования текста ответа в JSON
        adverts: list = answer["adverts"]
        if not adverts:
            return []
        for advert_group in adverts:
            # Type 8 = auto (unified), type 9 = search (manual). Both needed for ComplexAdv
            if advert_group.get("type") not in (8, 9):
                continue
            for advert in advert_group["advert_list"]:
                advertId = advert["advertId"]
                advertIds.append(advertId)

        return advertIds

    @try_except_decorator(1, 2)
    async def _get_advs(self, adv_ids: list) -> list[Adv]:
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

    async def get_advs(self, adv_ids: list[int] = None) -> list[Adv]:
        if not adv_ids:
            adv_ids = await self.get_advertIds()
        all_advs: list[Adv] = []
        part = 50
        for i in range(0, len(adv_ids), part):
            if i > 0:
                await asyncio.sleep(0.2)
            part_of_advs = adv_ids[i : i + part]
            advs = await self._get_advs(part_of_advs)
            all_advs.extend(advs)
        return all_advs

    @try_except_decorator(1, 6)
    async def set_minus_phrases(self, adv_setting: AdvSetting, phrases: list):
        url = f"https://advert-api.wildberries.ru/adv/v1/auto/set-excluded?id={adv_setting.adv_id}"
        data = {"excluded": phrases}
        await requests(
            self.session, "POST", url, json_data=data, headers=self.headers.standart
        )
        logger.debug("Минус-фразы установлены")

    @try_except_decorator(1, 1)
    async def pause_company(self, adv_id: int):
        url = f"https://advert-api.wildberries.ru/adv/v0/pause?id={adv_id}"
        try:
            await requests(self.session, "GET", url, headers=self.headers.standart)
            logger.debug(f"Рекламная кампания {adv_id} успешно поставлена на паузу")
        except:
            raise
        return

    @try_except_decorator(1, 2)
    async def get_clusters_for_adv(self, adv: AdvSetting):
        url = (
            f"https://advert-api.wildberries.ru/adv/v2/auto/stat-words?id={adv.adv_id}"
        )

        response_text = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        if response_text:
            answer = json.loads(response_text)
            return answer
        else:
            return {}


class ContentApi(BaseAPI, ContentMixin):
    _only_read = api_rights.OnlyRead.FALSE
    _rights: set = {api_rights.Rights.CONTENT}

    async def get_subcategories(self):
        @try_except_decorator(1, 1)
        async def request(session, url) -> list[Subcategory]:
            all_categories = []
            response = await requests(
                session, "GET", url, headers=self.headers.standart
            )
            answer = json.loads(response)
            for data in answer["data"]:
                subcategory = Subcategory(**data)
                all_categories.append(subcategory)
            return all_categories

        offset = 0
        limit = 1000

        all_categories = []

        while True:
            url = f"{self.HOST}/content/v2/object/all?offset={offset}&limit={limit}"
            categories = await request(url)
            if categories:
                all_categories.extend(categories)
            if not categories:
                break
            else:
                offset += limit

        return all_categories

    async def get_patent_categories(self):
        url = f"{self.HOST}/content/v2/object/parent/all"

        response_text = await requests(
            self.session, "GET", url, headers=self.headers.standart
        )
        answer = json.loads(response_text)
        return answer["data"]

    async def get_cards_by_text(self, texts):
        cards = []
        for text in texts:
            try:
                cards.append(await self.get_card_by_text(text))
            except CardNotFoundInWB:
                logger.debug(
                    "Карточка с текстом %s не найдена на Wildberries, возможно, карточка не существует",
                    text,
                )
                continue
            await asyncio.sleep(0)
        return cards

    @try_except_decorator(1, 2)
    async def get_card_by_text(self, text: str | int):
        url = f"{self.HOST}/content/v2/get/cards/list"
        text = str(text)
        data_for_req = {
            "settings": {
                "sort": {"ascending": False},
                "cursor": {"limit": 1},
                "filter": {"withPhoto": -1, "textSearch": str(text)},
            }
        }

        response = await requests(
            self.session,
            "POST",
            url=url,
            json_data=data_for_req,
            headers=self.headers.standart,
        )
        answer = json.loads(response)
        cards = answer["cards"]
        if not cards:
            raise CardNotFoundInWB(
                f"Карточка с текстом {text} не найдена на Wildberries"
            )
        card_json = answer["cards"][0]
        card = CardFromWB(card_json)
        return card

    async def get_product_list(
        self,
        updated_at: str | None = None,
        nm_id: int | None = None,
    ) -> dict:
        """Возвращает список товаров на Wildberries."""

        url = f"{self.HOST}/content/v2/get/cards/list"

        limit = 100

        data = json.dumps(
            {
                "settings": {
                    "cursor": {
                        "limit": limit,
                        "updatedAt": updated_at,
                        "nmID": nm_id,
                    },
                    "filter": {
                        "withPhoto": -1,
                        # 'textSearch': str(nm_id),
                    },
                },
            }
        )

        response = await requests(
            self.session, "POST", url=url, data=data, headers=self.headers.standart
        )
        return json.loads(response)


class WBApi:
    def __init__(self, wb_access: WBCabinetAccess, session: ClientSession) -> None:
        self.advert = AdvertApi(wb_access, session)
        self.content = ContentApi(wb_access, session)
        self.wb_access = wb_access
        self.wb_cabinet = wb_access.wb_cabinet
        self.client_session = session
