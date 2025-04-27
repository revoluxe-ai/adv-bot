import asyncio
import datetime
import json
import logging
import re
import time
import typing
from statistics import mean

from aiogram.client.session import aiohttp
from aiohttp import ServerDisconnectedError, ClientOSError

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


class EmptyDataDictFromSearchWB(Exception):
    pass


class DataError(Exception):
    pass


def try_except(requests_per_interval, interval_seconds, max_attempts=50, max_delay=1.5):
    def decorator(func):
        async def wrapper(instance, *args, **kwargs):
            if not hasattr(instance, "_api_call_state"):
                instance._api_call_state = {}

            method_name = func.__name__
            if method_name not in instance._api_call_state:
                next_pause = interval_seconds / requests_per_interval
                instance._api_call_state[method_name] = {
                    "_last_query_time": 0,
                    "_attempts": 0,
                    "_last_pauses": [0],
                    "_next_pause": next_pause,
                }

            state = instance._api_call_state[method_name]
            while state["_attempts"] < max_attempts:
                current_time = time.time()
                next_pause = state["_next_pause"]
                last_query_time = state["_last_query_time"]
                time_since_last_query = current_time - last_query_time
                time_to_wait = next_pause - time_since_last_query
                if time_to_wait < 0:
                    time_to_wait = 0
                logger.debug(f"Пауза между запросами: {time_to_wait} секунд")
                await asyncio.sleep(time_to_wait)
                state["_last_pauses"].append(time_to_wait)
                state["_last_pauses"] = state["_last_pauses"][-1000:]
                state["_last_query_time"] = int(time.time())
                try:
                    result = await func(instance, *args, **kwargs)
                    logger.debug(f"Запрос через {method_name} выполнен успешно")
                    max_pause = max(state["_last_pauses"])
                    min_pause = min(state["_last_pauses"])
                    current_pause = time_to_wait
                    if current_pause >= max_pause:
                        next_pause = current_pause * 2
                    elif current_pause <= min_pause:
                        next_pause = current_pause / 2
                    else:
                        mean_pause = mean(state["_last_pauses"])
                        next_pause = mean_pause * 0.95
                    if next_pause > max_delay:
                        next_pause = max_delay
                    state["_next_pause"] = next_pause
                    state["_attempts"] = 0  # Сброс попыток после успешного выполнения
                    return result
                except (DataError, ServerDisconnectedError, ClientOSError) as e:
                    logger.debug(
                        f"Ошибка при выполнении запроса через {method_name}: {e}, "
                        f'Пауза перед следующим запросом: {state["_next_pause"]} секунд'
                    )
                    state["_attempts"] += 1
                    if state["_attempts"] >= max_attempts:
                        logger.error(
                            f"Превышено максимальное количество попыток {max_attempts} "
                            f"для метода {method_name}, аргументы: {args}, {kwargs}"
                        )
                        raise e
                    last_pause = state["_last_pauses"][-1]
                    previous_pause = state["_last_pauses"][-2]
                    if last_pause >= previous_pause:
                        state["_next_pause"] = last_pause * 2
                    else:
                        state["_next_pause"] = mean([last_pause, previous_pause])
                    if state["_next_pause"] == 0:
                        state["_next_pause"] = 1
                    if state["_next_pause"] > max_delay:
                        state["_next_pause"] = max_delay
                    state["_attempts"] += 1

        return wrapper

    return decorator


def get_parse_url(text: str, page: int):
    assert 60 >= page > 0
    url = f"https://search.wb.ru/exactmatch/ru/common/v5/search?ab_testing=false&appType=32&curr=rub&dest=-1257786&page={page}&query={text}&resultset=catalog&sort=popular&suppressSpellcheck=false"
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
            if total_items:
                total_pages.total_pages = total_items // 100 + 1
        except Exception as e:
            logger.debug(
                f"Ошибка при парсинге страницы {page} ключа {text} {e}", exc_info=True
            )
            return []
        if cluster:
            await redis_manager.set_cluster_and_preset(text, cluster, preset)
        if not products:
            return []
        positions = []
        for place_on_page, product in enumerate(products):
            adv_type = None
            nmid = product["id"]
            real_position = first_place + place_on_page
            if "log" in product:
                log = product["log"]
                adv_id = log["advertId"]
                cpm = log["cpm"]
                base_position = log["position"]
                promo_position = log["promoPosition"]
                real_position = promo_position
                adv_type_original = log["tp"]
                if adv_type_original == "c":
                    adv_type = 9
                elif adv_type_original == "b":
                    adv_type = 8
                else:
                    raise DataError(
                        f"Неизвестный тип рекламы {adv_type_original}", text
                    )
            else:
                adv_id = None
                cpm = None
                promo_position = None
                base_position = real_position

            position = WBItemPosition(
                nmid=nmid,
                base_position=base_position,
                promo_position=promo_position,
                cpm=cpm,
                adv_id=adv_id,
                real_position=real_position,
                keyword_text=text,
                timestamp=datetime.datetime.now(),
                adv_type=adv_type,
            )
            positions.append(position)

            if cluster != text:
                position = WBItemPosition(
                    nmid=nmid,
                    base_position=base_position,
                    promo_position=promo_position,
                    cpm=cpm,
                    adv_id=adv_id,
                    real_position=real_position,
                    keyword_text=cluster,
                    timestamp=datetime.datetime.now(),
                )

                positions.append(position)

        return positions

    @try_except(1, 1)
    async def __parse_keywords_from_wb(self, text: str, page: int) -> tuple[
        typing.Optional[list[dict]],
        typing.Optional[str],
        typing.Optional[int],
        typing.Optional[int],
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
            raise DataError(f"{e}", text)

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
) -> (
    list[WBItemPosition],
    int,
):
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


async def add_wb_positions_to_clickhouse(positions):
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
        positions_for_catch_max_bet = [
            position
            for position in positions
            if position.promo_position and position.promo_position <= 40
        ]
        cpms = [position.cpm for position in positions_for_catch_max_bet]
        if cpms:
            max_bet = max(cpms)
            await redis_manager.set_max_bet_for_keyword(text, max_bet)
        else:
            logger.debug(f"Не найдена максимальная ставка для ключа {text}")
        for position in positions:
            nmid: int = position.nmid
            need_nmids.discard(nmid)
            if not need_nmids:
                stop_event.set()
                break
    return positions


async def add_wb_positions(text: str, need_nmids: set[int], delay, page_limit=60):
    try:
        await _add_wb_positions(text, set(need_nmids), delay, page_limit)
    except Exception:
        logger.error(f"Ошибка при парсинге позиций {text}", exc_info=True)
    return


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
        if page in checked_pages:
            continue
        if len(checked_pages) >= total_pages.total_pages:
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

        checked_pages.add(page)
        await asyncio.sleep(delay)

    if page_limit == page_limit and need_nmids:
        not_found_positions = [
            WBItemPosition(
                real_position=0,
                base_position=0,
                promo_position=0,
                keyword_text=text,
                timestamp=datetime.datetime.now(),
                nmid=nmid,
                cpm=0,
            )
            for nmid in need_nmids
        ]
        await add_wb_positions_to_redis(not_found_positions)
    return


async def add_wb_positions_to_redis(positions: list[WBItemPosition]):
    # for position in positions:
    # last_position = await redis_manager.get_keyword_position(position.keyword_text,
    #                                                          position.nmid)
    # asyncio.create_task(sender_manager.check_last_position(last_position, position))

    await redis_manager.add_positions_to_redis(positions)
