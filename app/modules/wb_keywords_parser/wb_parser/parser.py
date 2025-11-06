import asyncio
import datetime
import json
import logging
import re
import typing
import aiohttp
from sqlalchemy.orm import load_only


from aiohttp import ClientSession
from dependency_injector.wiring import Provide, inject

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import WBItemPosition, WBCard
from app.modules.wb_adv_updater import data_manager
from app.settings import settings
from app.utils import redis_manager
from app.utils.rate_limit import rate_limited_request
from .excs import TooManyRequestsInParserError, WBConnectionRateLimitError

if typing.TYPE_CHECKING:
    from .rate_limit_manager import ParserRateLimitRedisManager

logger = logging.getLogger(__name__)


class TotalPages:
    def __init__(self):
        self._total_pages = 60

    @property
    def total_pages(self) -> int:
        return self._total_pages

    @total_pages.setter
    def total_pages(self, value: int) -> None:
        if value > 60:
            value = 60
        self._total_pages: int = value

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

    def __init__(self, rate_limit_manager: 'ParserRateLimitRedisManager' =Provide['module_resources.wb_keywords_parser.rate_limit_manager'],
                 delay: float = settings.PARSING_LIMITER_DELAY):
        self._rate_limit_manager: 'ParserRateLimitRedisManager' = rate_limit_manager

            # Применяем декоратор rate limiting к методу парсинга
        # TODO: Прошла ошибка на smoke test - из-за неаннотированости функции-обертки (декоратора) и отсутствия тестов

        self._parse_with_rate_limit = rate_limited_request(rate_limit_manager, delay=delay)(
            self._parse_keywords_from_wb_impl,
        )

    async def parse_keywords_from_wb(
        self, text: str, page: int, total_pages: TotalPages, delay: float = settings.PARSING_LIMITER_DELAY
    ) -> list[WBItemPosition]:
        first_place = page * 100 - 99
        try:
            # TODO: Сделать тест на эту функцию, прошла ошибка на smoke test
            data = await self._parse_with_rate_limit(text, page)
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
        except TooManyRequestsInParserError as e:
            # Rate limiting ошибки должны пробраситься наверх
            raise e
        except Exception as e:
            logger.error(
                "Ошибка при парсинге страницы %s ключа %s %s",
                page,
                text,
                e,
                exc_info=True,
            )
            raise e
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
            positions.append(position) # pyright: ignore

            if cluster and cluster != text:
                position = WBItemPosition(
                    nmid=nmid,
                    adv_id=adv_id,
                    position=real_position,
                    keyword_text=cluster,
                    timestamp=datetime.datetime.now(),
                )

                positions.append(position) # pyright: ignore

        return positions # pyright: ignore

    async def _parse_keywords_from_wb_impl(self,
        text: str,
        page: int,
         ):
        # для проброса ошибок сети, интерпретируемых как слишком много запросов
        try:
            result = await self.__parse_keywords_from_wb_impl(text, page)
            return result # pyright: ignore
        except aiohttp.ClientError as e:
            raise WBConnectionRateLimitError("Rate limit exceeded in ParserService") from e


    @inject
    async def __parse_keywords_from_wb_impl(self, # pyright: ignore
                                           text: str,
                                           page: int,
                                           client: ClientSession = Provide['http_sessions.aiohttp_client_for_parser'],
                                           ) -> tuple[
        list[dict[typing.Any, typing.Any]] | None, # pyright: ignore
        str | None,
        int | None,
        int | None,
    ]:
        url = get_parse_url(text, page)
        logger.debug(f"Запрос к URL: {url}")
        async with client.get(url) as response:
            response_text = await response.text()

        if not response_text:
            raise DataError("Пустой ответ от сервера", text)

        if "Too Many Requests" in response_text:
            raise TooManyRequestsInParserError(
                "Слишком много запросов к серверу WB",
            )

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSONDecode при парсинге данных: {e}", exc_info=True)
            raise DataError(f"Ошибка JSONDecode: {e}", text) from e
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
            preset = int(re.search(r"preset=(\d+)", catalog_value).group(1)) # pyright: ignore
            cluster = metadata["normquery"]
        total_items = data["data"]["total"]
        products: list[typing.Any] = data["data"]["products"]

        if not products:
            logger.info(f"Нет продуктов для ключа {text} на странице {page}")
            return None, cluster, preset, total_items

        assert isinstance(preset, int)
        assert isinstance(cluster, str)
        assert isinstance(products, list)
        return products, cluster, preset, total_items

    @staticmethod
    def _raise_too_many_requests_error(response_text: str) -> None:
        # Deprecated: оставлено для совместимости (не используется после inlined check)
        if "Too Many Requests" in response_text:
            raise TooManyRequestsInParserError("Слишком много запросов к серверу WB")


# TODO: Мертвый код, удалить после проверки
@inject
def _create_rate_limit_manager(client: RedisClient = Provide["redis_client"]) -> "ParserRateLimitRedisManager": # pyright: ignore
    try:
        return ParserRateLimitRedisManager(redis_client=client)
    except Exception as e:
        logger.warning(f"Не удалось создать rate_limit_manager: {e}. Rate limiting отключен.")
        raise e



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
) -> list[WBItemPosition]:
    try:
        positions = await _add_positions_from_page(
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
        logger.debug("Проверенные страницы для запроса: %s: %s", text, checked_pages)
        return positions
    except Exception as e:
        logger.error(
            f"Ошибка при парсинге страницы {page} ключа {text} {e}", exc_info=True
        )
        logger.debug(f"{get_parse_url(text, page)}")
        raise e


async def add_wb_positions_to_clickhouse(positions: list[WBItemPosition]) -> None:
    await data_manager.add_positions_to_clickhouse(positions)


async def add_wb_positions_to_all_bases(
    positions: list[WBItemPosition], need_nmids: set[int]
):
    my_positions = [position for position in positions if position.nmid in need_nmids]
    await asyncio.gather(
        add_wb_positions_to_redis(my_positions),
        add_wb_positions_to_clickhouse(my_positions),
    )

@inject
async def _add_positions_from_page(
    stop_event: asyncio.Event,
    catch_any_position: asyncio.Event,
    text: str,
    page: int,
    need_nmids: set[int],
    total_pages: TotalPages,
    parser: ParserService = Provide['module_resources.wb_keywords_parser.parser_service']
) -> list[WBItemPosition]:
    if stop_event.is_set():
        return []
    try:
        positions = await parser.parse_keywords_from_wb(text, page, total_pages)
    except Exception as e:
        logger.error(f"Ошибка при парсинге страницы {page} ключа {text}", exc_info=True)
        logger.error(f"{get_parse_url(text, page)}")
        raise e
    if not positions:
        return []
    catch_any_position.set()
    logger.debug(f"Найдено {len(positions)}")
    if positions:
        await parsing_queue_manager.add_found_not_found_page(
            text, positions, need_nmids, page
        )
        # Ставка больше не доступна при парсинге, блок вычисления max_bet удален
        for position in positions:
            nmid: int | None = position.nmid
            if nmid is None:
                raise RuntimeError("nmid не может быть None в позиции")
            need_nmids.discard(nmid)
            if not need_nmids:
                stop_event.set()
                break
    return positions


# TODO: Сделать проверку прав токенов check запросами к WB

async def add_wb_positions(
    text: str, need_nmids: set[int],
        delay: float = settings.PARSING_LIMITER_DELAY,
        page_limit: int = 60
) -> list[WBItemPosition]:
    """
    Функция подходит только для карточек, которые точно есть в базе. Если какой-то нет - логика сломается

    Args:
        text:
        need_nmids:
        delay:
        page_limit:

    Returns:

    """
    original_nmids = set(need_nmids)
    in_indexes: dict[int, bool | None] = await __check_index(text, need_nmids, delay=delay)
    not_found_positions: list[WBItemPosition] = []
    for nmid, in_index in in_indexes.items():
        if not in_index:
            position = WBItemPosition(
                position=-1,
                keyword_text=text,
                timestamp=datetime.datetime.now(),
                nmid=nmid,
            )
            not_found_positions.append(position)
            need_nmids.discard(nmid)


    positions = await _get_wb_positions(text, set(need_nmids), delay, page_limit)
    positions.extend(not_found_positions)
    await add_wb_positions_to_all_bases(positions, original_nmids)
    logger.debug("Записали позиции в базы")
    return positions

@inject
async def __check_index(
    text: str,
    need_nmids: set[int],
    delay: float = settings.PARSING_LIMITER_DELAY,
    parser: ParserService = Provide['module_resources.wb_keywords_parser.parser_service']
) -> dict[int, bool | None]:
    """
    Проверяет, находятся ли товары в индексе по запросу "бренд + текст".
    Проверяет до 60 страниц, прерывая поиск при нахождении нужного артикула.
    """
    from sqlalchemy import select
    from app.utils.db.session_maker import get_async_session_maker as sm

    stmt = select(WBCard).options(
        load_only(WBCard.nmid, WBCard.json)
    ).where(
        WBCard.nmid.in_(need_nmids),
    )

    async with sm(read_only=True) as session:
        result = await session.execute(stmt)
        wb_cards = result.scalars().all()
    nmids_in_cards = {card.nmid for card in wb_cards}
    if not nmids_in_cards == need_nmids:
        missing_nmids = set(need_nmids) - set(nmids_in_cards)
        raise RuntimeError(f"Некоторые nmids не найдены в базе WBCard при проверке индексации {missing_nmids}")
    nmids_to_index: dict[int, bool | None] = {}
    for card in  wb_cards:
        nmid = card.nmid
        brand = card.brand
        query = f'{brand} {text}'
        found = False

        # Проверяем до 60 страниц, прерывая при нахождении артикула
        try:
            total_pages = TotalPages()
            for page in range(1, 61):
                positions = await parser.parse_keywords_from_wb(query, page, total_pages, delay)
                # Проверяем, найден ли наш nmid в результатах
                if any(pos.nmid == nmid for pos in positions):
                    found = True
                    break
                # Прерываем, если достигли максимальной страницы
                if page >= total_pages.total_pages:
                    break
                # Небольшая задержка между запросами для избежания rate limiting
                await asyncio.sleep(0.1)
            nmids_to_index[nmid] = found
        except Exception as e:
            logger.error("Ошибка при проверке индекса для nmid %s, query '%s': %s",
                           nmid, query, e, exc_info=True)
            raise e

    return nmids_to_index



async def _get_wb_positions(
    text: str, need_nmids: set[int], delay: float, page_limit: int =60
) -> list[WBItemPosition]:
    total_pages = TotalPages()
    stop_event = asyncio.Event()
    catch_any_position = asyncio.Event()
    checked_pages: set[int] = set()
    parsing_pages_queue: list[int] = await parsing_queue_manager.get_parsing_queue(
        text, need_nmids, 60
    )

    positions: list[WBItemPosition] = []
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

        pos: list[WBItemPosition] = await add_positions_from_page(
            stop_event,
            catch_any_position,
            text,
            page,
            need_nmids,
            total_pages,
            checked_pages,
        )
        positions.extend(pos)

        checked_pages.add(page)
        await asyncio.sleep(delay)
    not_found_positions: list[WBItemPosition] = []
    for nmid in need_nmids:
        position = WBItemPosition(
            position=0,
            keyword_text=text,
            timestamp=datetime.datetime.now(),
            nmid=nmid,
        )
        not_found_positions.append(position)
    positions.extend(not_found_positions)
    return positions


async def add_wb_positions_to_redis(positions: list[WBItemPosition]):
    # for position in positions:
    # last_position = await redis_manager.get_keyword_position(position.keyword_text,
    #                                                          position.nmid)
    # asyncio.create_task(sender_manager.check_last_position(last_position, position))

    await redis_manager.add_positions_to_redis(positions)
