import asyncio
import datetime
import json
import logging
import re

from aiogram.client.session import aiohttp

from app.modules.common_slaves.wildberries.models import WBItemPosition
from app.modules.wb_adv_updater import data_manager
from app.utils import redis_manager

logger = logging.getLogger(__name__)


class TotalPages:
    def __init__(self):
        self._total_pages = 60

    @property
    def total_pages(self):
        return self._total_pages

    @total_pages.setter
    def total_pages(self, value):
        if value > 60:
            value = 60
        self._total_pages = value

    @property
    def all_pages_list(self):
        all_pages = set(range(1, self.total_pages + 1))
        return all_pages


class EmptyDataDictFromSearchWB(Exception):
    pass


class DataError(Exception):
    pass


def get_parse_url(text: str, page: int) -> str:
    """
    https://search.wb.ru/exactmatch/ru/common/v5/search?ab_testing=false&appType=32&curr=rub&dest=-1257786&page=1&query=картина&resultset=catalog&sort=popular&suppressSpellcheck=false


    """
    assert 60 >= page > 0
    url = (
        f"https://search.wb.ru/exactmatch/ru/common/v5/search?ab_testing=false&appType=32&curr=rub&dest=-1257786&"
        f"page={page}&query={text}&resultset=catalog&sort=popular&suppressSpellcheck=false"
    )
    return url


class ParserService:
    async def parse_keywords_from_wb(
        self, text: str, page: int, total_pages: TotalPages
    ) -> list[WBItemPosition]:
        first_place = page * 100 - 99
        try:
            data = await self.__parse_keywords_from_wb(text, page)
            if data:
                products, cluster, preset, total_items = data
            else:
                return []
            if total_items is not None:
                max_page = (total_items + 99) // 100 if total_items else 0
                total_pages.total_pages = max_page
                if max_page and page > max_page:
                    logger.info(
                        "Страница %s превышает максимальное количество страниц %s для ключа %s",
                        page,
                        max_page,
                        text,
                    )
                    return []
        except Exception as e:
            logger.debug(
                f"Ошибка при парсинге страницы {page} ключа {text} {e}", exc_info=True
            )
            del e
            return []
        if cluster:
            await redis_manager.set_cluster_and_preset(text, cluster, preset)
        if not products:
            return []
        positions = []
        for place_on_page, product in enumerate(products):
            adv_type = None
            try:
                nmid = product["id"]
                real_position = first_place + place_on_page
                if "log" in product:
                    log = product["log"]
                    adv_id = log["advertId"]

                    try:
                        adv_type_original = log["tp"]
                    except KeyError:
                        adv_type_original = None

                    if adv_type_original == "c":
                        adv_type = 9
                    elif adv_type_original == "b":
                        adv_type = 8
                    elif isinstance(adv_type_original, int):
                        raise DataError(
                            f"Неизвестный тип рекламы {adv_type_original}", text
                        )
                else:
                    adv_id = None

            except KeyError:
                logger.error("Ошибка парсинга данных о позициях с WB")
                continue
            position = WBItemPosition(
                nmid=nmid,
                adv_id=adv_id,
                position=real_position,
                keyword_text=text,
                timestamp=datetime.datetime.now(),
                adv_type=adv_type,
            )
            positions.append(position)

            if cluster and cluster != text:
                position = WBItemPosition(
                    nmid=nmid,
                    adv_id=adv_id,
                    position=real_position,
                    keyword_text=cluster,
                    timestamp=datetime.datetime.now(),
                )

                positions.append(position)

        return positions

    @staticmethod
    async def __parse_keywords_from_wb(text: str, page: int) -> tuple[
        list[dict] | None,
        str | None,
        int | None,
        int | None,
    ]:
        url = get_parse_url(text, page)
        logger.debug(f"Запрос к URL: {url}")
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(url) as response:
                response_text = await response.text()

        if not response_text:
            raise DataError("Пустой ответ от сервера", text)

        data = json.loads(response_text)

        if data == {}:
            logger.warning(
                f"Получены пустые данные для ключа {text} на странице {page}"
            )
            return None, None, None, None

        try:
            assert data["payloadVersion"] == 2
        except Exception as e:
            logger.debug(f"Ошибка в проверке версии данных: {e}", exc_info=True)
            raise DataError(f"{e}", text) from e

        metadata = data["metadata"]
        catalog_type = metadata["catalog_type"]

        if catalog_type == "merger":
            preset = hash(text)
            cluster = text
        else:
            catalog_value = metadata["catalog_value"]
            preset = int(re.search(r"preset=(\d+)", catalog_value).group(1))
            cluster = metadata["normquery"]
        total_items = data["data"]["total"]
        products = data["data"]["products"]

        if not products:
            logger.info(f"Нет продуктов для ключа {text} на странице {page}")
            return None, cluster, preset, total_items

        assert isinstance(preset, int)
        assert isinstance(cluster, str)
        assert isinstance(products, list)
        return products, cluster, preset, total_items


parser = ParserService()

from .parsing_page_queue_manager import ParsingQueueManager

parsing_queue_manager = ParsingQueueManager()


class ErrorParsingPositions(Exception):
    pass


async def add_positions_from_page(
    stop_event: asyncio.Event,
    catch_any_position: asyncio.Event,
    text: str,
    page: int,
    need_nmids: set[int],
    total_pages: TotalPages,
    checked_pages: set[int],
) -> None:
    try:
        await _add_positions_from_page(
            stop_event,
            catch_any_position,
            text,
            page,
            need_nmids,
            total_pages,
        )
        logger.debug(f"Добавляем страницу {page} в проверенные")
        checked_pages.add(page)
        logger.debug("Проверенные позиции добавили")
        logger.debug(f"Проверенные страницы: {checked_pages}")
    except Exception as e:
        logger.error(
            f"Ошибка при парсинге страницы {page} ключа {text} {e}", exc_info=True
        )
        logger.debug(f"{get_parse_url(text, page)}")
        del e


async def add_wb_positions_to_clickhouse(positions) -> None:
    await data_manager.add_positions_to_clickhouse(positions)


async def add_wb_positions_to_all_bases(
    positions: list[WBItemPosition], need_nmids: set[int]
):
    my_positions = [position for position in positions if position.nmid in need_nmids]
    await asyncio.gather(
        add_wb_positions_to_redis(my_positions),
        add_wb_positions_to_clickhouse(my_positions),
    )


async def _add_positions_from_page(
    stop_event: asyncio.Event,
    catch_any_position: asyncio.Event,
    text: str,
    page: int,
    need_nmids: set[int],
    total_pages: TotalPages,
) -> (list[WBItemPosition],):
    if stop_event.is_set():
        return []
    try:
        positions = await parser.parse_keywords_from_wb(text, page, total_pages)
    except Exception:
        logger.error(f"Ошибка при парсинге страницы {page} ключа {text}", exc_info=True)
        logger.debug(f"{get_parse_url(text, page)}")
        return []
    if not positions:
        return []
    catch_any_position.set()
    logger.debug(f"Найдено {len(positions)}")
    if positions:
        await parsing_queue_manager.add_found_not_found_page(
            text, positions, need_nmids, page
        )
        await add_wb_positions_to_all_bases(positions, need_nmids)
        logger.debug("Записали позиции в базы")
        # Ставка больше не доступна при парсинге, блок вычисления max_bet удален
        for position in positions:
            nmid: int = position.nmid
            need_nmids.discard(nmid)
            if not need_nmids:
                stop_event.set()
                break
    return positions


async def add_wb_positions(
    text: str, need_nmids: set[int], delay, page_limit=60
) -> None:
    await _add_wb_positions(text, set(need_nmids), delay, page_limit)


async def _add_wb_positions(
    text: str, need_nmids: set[int], delay, page_limit=60
) -> None:
    total_pages = TotalPages()
    stop_event = asyncio.Event()
    catch_any_position = asyncio.Event()
    checked_pages: set[int] = set()
    parsing_pages_queue: list[int] = await parsing_queue_manager.get_parsing_queue(
        text, need_nmids, 60
    )
    for page in parsing_pages_queue:
        if page not in total_pages.all_pages_list:
            continue
        if page in checked_pages:
            continue
        if len(set(total_pages.all_pages_list) - checked_pages) == 0:
            break
        if len(checked_pages) >= page_limit:
            break
        if len(need_nmids) == 0:
            break
        try:
            await add_positions_from_page(
                stop_event,
                catch_any_position,
                text,
                page,
                need_nmids,
                total_pages,
                checked_pages,
            )
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы {page}: {e}")
            del e
        checked_pages.add(page)
        await asyncio.sleep(delay)

    not_found_positions = [
        WBItemPosition(
            position=0,
            keyword_text=text,
            timestamp=datetime.datetime.now(),
            nmid=nmid,
        )
        for nmid in need_nmids
    ]
    if not_found_positions:
        await add_wb_positions_to_redis(not_found_positions)
    return


async def add_wb_positions_to_redis(positions: list[WBItemPosition]):
    # for position in positions:
    # last_position = await redis_manager.get_keyword_position(position.keyword_text,
    #                                                          position.nmid)
    # asyncio.create_task(sender_manager.check_last_position(last_position, position))

    await redis_manager.add_positions_to_redis(positions)
