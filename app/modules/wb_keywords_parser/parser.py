import asyncio
import datetime
import hashlib
import json
import random
import re
import time
import typing
from asyncio import Task
from functools import wraps
import logging
from statistics import mean
from typing import AsyncGenerator
from aiohttp import ServerDisconnectedError, ClientOSError
from sqlalchemy.orm import joinedload

from app.admin_bot.sender import sender_manager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import KeywordStatus, CalculatedKeyword
from app.modules.wb_adv_updater import data_manager
from app.settings import settings
from app.utils import redis_manager
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker as sm
from sqlalchemy import select, and_, not_



from app.modules.common_slaves.wildberries.models import WBItemPosition, CommonKeyword, AdvSetting
from aiogram.client.session import aiohttp
from app.utils.db.session_maker import get_async_session_maker as sm
import logging
from app import settings

logger = logging.getLogger(__name__)

from sqlalchemy import exc as sa_exc



class EmptyDataDictFromSearchWB(Exception):
    pass

class DataError(Exception):
    pass



def try_except(requests_per_interval, interval_seconds, max_attempts=50, max_delay=1.5):
    def decorator(func):
        async def wrapper(instance, *args, **kwargs):
            if not hasattr(instance, '_api_call_state'):
                instance._api_call_state = {}

            method_name = func.__name__
            if method_name not in instance._api_call_state:
                instance._api_call_state[method_name] = {
                    '_last_query_time': 0,
                    '_attempts': 0,
                    '_last_pauses': [0],
                    '_next_pause': 0,

                }

            state = instance._api_call_state[method_name]
            while state['_attempts'] < max_attempts:
                current_time = time.time()
                next_pause = state['_next_pause']
                last_query_time = state['_last_query_time']
                time_since_last_query = current_time - last_query_time
                time_to_wait = next_pause - time_since_last_query
                if time_to_wait < 0:
                    time_to_wait = 0
                logger.debug(f'Пауза между запросами: {time_to_wait} секунд')
                await asyncio.sleep(time_to_wait)
                state['_last_pauses'].append(time_to_wait)
                state['_last_pauses'] = state['_last_pauses'][-1000:]
                state['_last_query_time'] = time.time()
                try:
                    result = await func(instance, *args, **kwargs)
                    logger.debug(f'Запрос через {method_name} выполнен успешно')
                    max_pause = max(state['_last_pauses'])
                    min_pause = min(state['_last_pauses'])
                    current_pause = time_to_wait
                    if current_pause >= max_pause:
                        next_pause = current_pause * 2
                    elif current_pause <= min_pause:
                        next_pause = current_pause/2
                    else:
                       mean_pause = mean(state['_last_pauses'])
                       next_pause = mean_pause*0.95
                    if next_pause > max_delay:
                        next_pause = max_delay
                    state['_next_pause'] = next_pause
                    state['_attempts'] = 0  # Сброс попыток после успешного выполнения
                    return result
                # except DataError:
                #     pause = 0.5
                #     state['_next_pause'] = pause
                #     state['_attempts'] += 1
                except (DataError,
                        ServerDisconnectedError,
                        ClientOSError) as e:
                    logger.debug(f'Ошибка при выполнении запроса через {method_name}: {e}, '
                                 f'Пауза перед следующим запросом: {state["_next_pause"]} секунд')
                    state['_attempts'] += 1
                    if state['_attempts'] >= max_attempts:
                        raise e
                    last_pause = state['_last_pauses'][-1]
                    previous_pause = state['_last_pauses'][-2]
                    if last_pause >= previous_pause:
                        state['_next_pause'] = last_pause * 2
                    else:
                        state['_next_pause'] = mean([last_pause, previous_pause])
                    if state['_next_pause'] == 0:
                        state['_next_pause'] = 1
                    if state['_next_pause'] > max_delay:
                        state['_next_pause'] = max_delay
                    state['_attempts'] += 1
        return wrapper
    return decorator


def get_parse_url(text: str, page: int):
    assert  100 >=  page > 0
    url = f'https://search.wb.ru/exactmatch/ru/common/v5/search?ab_testing=false&appType=32&curr=rub&dest=-1257786&page={page}&query={text}&resultset=catalog&sort=popular&suppressSpellcheck=false'
    return url

class Parser:
    async def parse_keywords_from_wb(self, text: str, page: int):
        first_place = page*100 - 99
        products, cluster, preset = await self.__parse_keywords_from_wb(text, page)
        if cluster:
            await redis_manager.set_cluster_and_preset(text, cluster, preset)
        if not products:
            return None
        positions = []
        for place_on_page, product in enumerate(products):
            nmid = product['id']
            real_position = first_place + place_on_page
            if 'log' in product:
                log = product['log']
                adv_id = log['advertId']
                cpm = log['cpm']
                base_position = log['position']
                promo_position = log['promoPosition']
                real_position = promo_position
            else:
                adv_id = None
                cpm = None
                promo_position = None
                base_position = real_position

            position = WBItemPosition(
                nmid = nmid,
                base_position=base_position,
                promo_position=promo_position,
                cpm=cpm,
                adv_id=adv_id,
                real_position=real_position,
                keyword_text = text,
                timestamp = datetime.datetime.now()
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
                    timestamp=datetime.datetime.now()
                )

                positions.append(position)

        return positions



    @try_except(1, 1)
    async def __parse_keywords_from_wb(self, text: str, page: int)-> tuple[typing.Optional[list[WBItemPosition]],
                                                                     typing.Optional[str],
                                                                     typing.Optional[int]]:
        url = get_parse_url(text, page)
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(url) as response:
                response = await response.text()
        if not response:
            raise DataError('Пустой ответ от сервера', text)
        data = json.loads(response)
        if data == {}:
            return None, None, None
        try:
            assert data['payloadVersion'] == 2
        except Exception as e:
            raise DataError(f'{e}', text)
        metadata = data['metadata']
        catalog_type = metadata['catalog_type']
        if catalog_type == 'merger':
            preset = hash(text)
            cluster = text
        else:
            catalog_value = metadata['catalog_value']
            preset = int(re.search(r'preset=(\d+)', catalog_value).group(1))
            cluster = metadata['normquery']
        products = data['data']['products']
        if not products:
            return None, cluster, preset
        assert isinstance(preset, int)
        assert isinstance(cluster, str)
        assert isinstance(products, list)
        return products, cluster , preset



parser = Parser()

text_to_task = {}

write_to_db_queue = asyncio.Queue(10000)

queue_position_dict = {}



class ErrorParsingPositions(Exception):
    pass


async def add_positions_from_page(stop_event: asyncio.Event,
                                  catch_any_position: asyncio.Event,
                                  text: str,
                                  page: int,
                                  need_nmids: set[int]):
    try:
        await _add_positions_from_page(stop_event, catch_any_position, text, page, need_nmids)
    except Exception as e:
        logger.debug(f'Ошибка при парсинге страницы {page} ключа {text} {e}')
        logger.debug(f'{get_parse_url(text, page)}')



async def _add_positions_from_page(stop_event: asyncio.Event,
                                  catch_any_position: asyncio.Event,
                                  text: str,
                                  page: int,
                                  need_nmids: set[int],):
    if stop_event.is_set():
        return []
    try:
         positions = await parser.parse_keywords_from_wb(text, page)
    except Exception as e:
        logger.error(f'Ошибка при парсинге страницы {page} ключа {text}', exc_info=True)
        logger.debug(f'{get_parse_url(text, page)}')
        return []
    if not positions:
        return []
    catch_any_position.set()
    logger.debug(f'Найдено {len(positions)}')
    positions = [position for position in positions if position.nmid in need_nmids]
    logger.debug(f'После фильтра осталось {len(positions)}')
    if positions:
        await add_wb_positions_to_redis(positions)
        logger.debug('Записали позиции в Редис')
        for position in positions:
            nmid: int = position.nmid
            need_nmids.discard(nmid)
            if not need_nmids:
                stop_event.set()
                break
    return positions


async def add_wb_positions(text: str, need_nmids: set[int], delay, page_limit=100):
    stop_event = asyncio.Event()
    catch_any_position = asyncio.Event()
    tasks = []
    last_positions = []
    checked_pages = set()
    # Получаем последние позиции для всех артикулов
    for nmid in need_nmids:
        last_position: WBItemPosition = await redis_manager.get_keyword_position(text, nmid)
        if last_position:
            last_positions.append(last_position)
    # Если нет предыдущих позиций или все позиции на первой странице, начинаем с конца
    if not last_positions or any([lp.real_position for lp in last_positions]) == 0:
            for page in range(1, 101):
                if len(checked_pages) >= page_limit:
                    break
                if stop_event.is_set():
                    break
                checked_pages.add(page)
                task = asyncio.create_task(
                    add_positions_from_page(stop_event, catch_any_position, text, page, need_nmids=need_nmids)
                )
                tasks.append(task)
                await asyncio.sleep(delay)
    else:
        for position in last_positions:
            start_page = position.real_position // 100 + 1
            min_page = start_page
            max_page = start_page

            while need_nmids and not stop_event.is_set():
                # Прерывание, если страница выходит за пределы
                if min_page < 1 and max_page > 100:
                    logger.debug('Достигнут предел страниц')
                    break

                logger.debug(f'Проверка артикула {position.nmid} запроса {text}: {min_page} {max_page}')

                # Проверка max_page
                if max_page <= 100 and max_page not in checked_pages:
                    try:
                        await add_positions_from_page(stop_event,
                                                      catch_any_position,
                                                      text, max_page,
                                                      need_nmids=need_nmids)
                        checked_pages.add(max_page)
                    except Exception as e:
                        logger.error(f'Ошибка при парсинге страницы {max_page}: {e}')
                    max_page += 1
                    await asyncio.sleep(delay)

                # Проверка min_page
                if min_page > 1 and min_page not in checked_pages:
                    try:
                        await add_positions_from_page(stop_event,
                                                      catch_any_position,
                                                      text, min_page,
                                                      need_nmids=need_nmids)
                        checked_pages.add(min_page)
                    except Exception as e:
                        logger.error(f'Ошибка при парсинге страницы {min_page}: {e}')
                    min_page -= 1
                    await asyncio.sleep(delay)

                # Прерывание, если обе страницы уже проверены
                if (min_page in checked_pages or min_page < 1) and (max_page in checked_pages or max_page > 100):
                    logger.debug('Достигнут предел страниц или все страницы проверены')
                    break



    for task in tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f'Ошибка при парсинге страницы {e}')

    if page_limit in [1, 100] and not catch_any_position.is_set():
        raise ErrorParsingPositions('Не найдено ни одной позиции в выдаче')
    if page_limit == 100 and need_nmids:
        not_found_positions = [
            WBItemPosition(
                real_position=0,
                base_position=0,
                promo_position=0,
                keyword_text=text,
                timestamp=datetime.datetime.now(),
                nmid=nmid,
                cpm=0
            )
            for nmid in need_nmids
        ]
        await add_wb_positions_to_redis(not_found_positions)

async def add_wb_positions_to_redis(positions: list[WBItemPosition]):
    for position in positions:
        last_position = await redis_manager.get_keyword_position(position.keyword_text,
                                                                 position.nmid)
        # asyncio.create_task(sender_manager.check_last_position(last_position, position))

    await redis_manager.add_positions_to_redis(positions)




max_threads = settings.MAX_THREAD_PARSER

semaphore = asyncio.Semaphore(max_threads)

async def limited_add_wb_positions(text:str,
                                   need_nmids: set[int],
                                   last_view,
                                   adv_id,
                                   max_page: int):
    async with semaphore:
        try:
            await add_wb_positions(text, need_nmids, 1, max_page)
            if last_view:
                 await redis_manager.set_last_views(adv_id, text, last_view)
        except ErrorParsingPositions as e:
            logger.error(f'По запросу {text} не найдено ни одной позиции')



async def get_phrases_for_parsing(queue: asyncio.Queue, semaphore=None):
    max_views_difference = 10
    async with sm(semaphore) as session:
        logger.debug("Открытие сессии для выполнения запросов к базе данных.")

        stmt = select(AdvSetting).where(
            AdvSetting.parsing_active == True,
            AdvSetting.active_status == 'started'
        )
        logger.debug("Формирование запроса для выбора активных рекламных кампаний.")

        advs = await session.execute(stmt)
        advs = advs.scalars().all()
    logger.debug(f"Получено {len(advs)} активных рекламных кампаний для парсинга.")

    adv_ids = [adv.adv_id for adv in advs]
    logger.debug(f"Список ID рекламных кампаний: {adv_ids}. Перемешивание списка для случайного порядка обработки.")

    random.shuffle(advs)
    for adv in advs:
        logger.debug(f'Обработка кампании {adv.name}')
        need_nmids = set(adv.nmids)
        adv_id = adv.adv_id
        logger.debug(f"Обработка рекламной кампании ID: {adv_id}. Получение ключевых слов.")
        try:
             keywords: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv)
        except Exception as exc:
            logger.error('Ошибка получения фраз для парсинга', exc_info=True)
            continue
        for keyword in keywords:
            if keyword.views == 0:
                logger.debug(f"Ключевое слово '{keyword.text}' не имеет просмотров. Пропуск.")
                await asyncio.sleep(0)
                continue
            total_views = keyword.views
            text = keyword.text
            logger.debug(f"Поиск кластера и пресета для ключевого слова '{text}'.")
            cluster_name, _ = await redis_manager.get_cluster_and_preset(text)
            if not cluster_name:
                logger.debug(
                    f"Кластер не найден для ключевого слова '{text}'. Определение необходимых nmids для парсинга.")
                max_page = 1
                await queue.put((text, adv.adv_id, list(need_nmids), None, max_page,))
                continue

            if keyword.status == KeywordStatus.GOOD:
                logger.debug(f"Ключевое слово '{text}' отмечено как хорошее. Проверка изменения просмотров.")
                last_views = await redis_manager.get_last_views(adv_id, text)
                last_position = await redis_manager.get_keyword_position(text, adv.nmids[0])
                if not last_views or\
                        (total_views - last_views) > max_views_difference and keyword.hard_status == 2 or\
                        last_views == total_views and keyword.hard_status == 2\
                        or not last_position:
                        await queue.put((text, adv.adv_id, list(need_nmids), last_views, 100))
                        logger.debug(f"Ключевое слово '{text}' добавлено в список обработанных.")




async def parser_all_white_phrase():
    tasks = {}
    queue = asyncio.Queue()
    while True:
        logger.debug('Получаем фразы для парсинга')
        generate_tasks = asyncio.create_task(get_phrases_for_parsing(queue))
        while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=5.0)
                    text, adv_id, need_nmids, last_views,  max_page = data
                    key = hashlib.md5(f'{text}{adv_id}'.encode()).hexdigest()
                    if not key in tasks:
                        tasks[key] = asyncio.create_task(limited_add_wb_positions(text,
                                                                                  set(need_nmids),
                                                                                  last_views,
                                                                                  adv_id,
                                                                                  max_page))
                    queue.task_done()
                except asyncio.TimeoutError:
                    logger.debug('Очередь пуста в течение 5 секунд, проверяем завершение генерации задач.')
                    if generate_tasks.done():
                        break
                finally:
                    keys = list(tasks.keys())
                    for key in keys:
                        task = tasks[key]
                        if task.done():
                            if task.exception():
                                logger.error(f'Ошибка при выполнении задачи {task.exception()}')
                        del tasks[key]



async def reset_from_redis_positions_of_out_index():
    async with sm() as session:
        # Выбираем позиции, для которых нет более новых позиций по этому ключевому слову
        stmt = (
            select(WBItemPosition)
            .join(WBItemPosition.keyword)  # Предполагается, что этот join корректно настроен
            .options(joinedload(WBItemPosition.keyword))
        ).where(and_(not_(WBItemPosition.keyword.has(CommonKeyword.last_full_update < WBItemPosition.timestamp)),
                CommonKeyword.last_full_update is not None))
        result = await session.execute(stmt)
        positions = result.scalars().all()

        for position in positions:
            await redis_manager.set_position_to_out_index(position)
            await asyncio.sleep(0)  # Чтобы предотвратить блокировку event loop


count_semaphore = settings.MAX_THREAD_PARSER
semaphore = asyncio.Semaphore(count_semaphore)