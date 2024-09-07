import asyncio
import datetime
import hashlib
import json
import re
import time
from asyncio import Task
from functools import wraps
import logging
from statistics import mean
from typing import AsyncGenerator
from aiohttp import ServerDisconnectedError, ClientOSError
from sqlalchemy.orm import joinedload

from app.admin_bot.sender import sender_manager
from app.modules.wb_adv_updater import data_manager
from app.settings import settings
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker as sm
from sqlalchemy import select, and_, not_



from app.modules.common_slaves.wildberries.models import WBItemPosition, CommonKeyword
from aiogram.client.session import aiohttp
from app.utils.db.session_maker import get_async_session_maker as sm
import logging
from app import settings

logger = logging.getLogger(__name__)

from sqlalchemy import exc as sa_exc



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




class Parser:
    async def parse_keywords_from_wb(self, text: str, page: int):
        first_place = page*100 - 99
        products, cluster, preset = await self.__parse_keywords_from_wb(text, page)
        if page == 1 and cluster:
            await redis_manager.set_cluster_and_preset(text, cluster, preset)
        if not products:
            return None
        positions = []
        text = cluster
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

            # Создаем объект WBItemPosition и устанавливаем все атрибуты перед добавлением в сессию
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
        return positions



    @try_except(1, 1)
    async def __parse_keywords_from_wb(self, text: str, page: int):
        url = f'https://search.wb.ru/exactmatch/ru/common/v5/search?ab_testing=false&appType=32&curr=rub&dest=-1257786&page={page}&query={text}&resultset=catalog&sort=popular&suppressSpellcheck=false'
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
            return None, None, None
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
                                  need_nmids: set[int],):
    if stop_event.is_set():
        return []
    positions = await parser.parse_keywords_from_wb(text, page)
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


async def add_wb_positions(text: str, need_nmids: set[int], delay):
    stop_event = asyncio.Event()
    catch_any_position = asyncio.Event()
    tasks = []
    try:
        for page in range(1, 100):
            if stop_event.is_set():
                break
            task = asyncio.create_task(
                add_positions_from_page(stop_event, catch_any_position, text, page, need_nmids=need_nmids)
            )
            tasks.append(task)
            await asyncio.sleep(delay)

        # Ожидаем завершения всех задач
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f'Ошибка в процессе добавления позиций: {e}', exc_info=True)
    finally:
        # Отменяем оставшиеся задачи, если такие есть
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Проверяем, была ли найдена хоть одна позиция
        if not catch_any_position.is_set():
            raise ErrorParsingPositions('Не найдено ни одной позиции в выдаче')

        # Добавляем не найденные позиции в Redis
        if need_nmids:
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

        asyncio.create_task(sender_manager.check_last_position(last_position, position))

    await redis_manager.add_positions_to_redis(positions)






semaphore = asyncio.Semaphore(settings.MAX_THREAD_PARSER)

async def limited_add_wb_positions(text:str, need_nmids: set[int]):
    async with semaphore:
        try:
            await add_wb_positions(text, need_nmids, 1)
        except Exception as e:
            logger.error(f'Ошибка при добавлении позиций в базу данных: {e}', exc_info=True)



async def parser_all_white_phrase():
    tasks_by_text = {}
    while True:
        logger.debug('Получаем фразы для парсинга')
        all_white_phrases_generator: AsyncGenerator[str] = data_manager.get_phrases_for_parsing()
        async for text, need_nmids in all_white_phrases_generator:
            if text not in tasks_by_text:
                logger.debug(f'Добавляем фразу {text} в список задач')
                if need_nmids:
                    task = asyncio.create_task(limited_add_wb_positions(text, need_nmids))
                    tasks_by_text[text] = task
            else:
                logger.debug(f'Фраза {text} уже есть в списке задач')
                task = tasks_by_text[text]
                if task.done():
                    if task.exception():
                        logger.error(f'Ошибка при выполнении задачи: {task.exception()}', exc_info=True)
                    del tasks_by_text[text]
            logger.debug(f'Задач в поиске: {len(tasks_by_text)}')
            await asyncio.sleep(0)


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