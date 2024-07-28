import asyncio
import datetime
import json
import time
from asyncio import Task
from functools import wraps
import logging
from statistics import mean
from typing import AsyncGenerator
from aiohttp import ServerDisconnectedError
from sqlalchemy.orm import joinedload

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



import warnings
from sqlalchemy import exc as sa_exc

# Включение отображения всех предупреждений
warnings.simplefilter("always", sa_exc.SAWarning)

# Пример обработки SAWarning как исключение
def handle_warnings_as_exceptions(message, category, filename, lineno, file=None, line=None):
    raise category(message)

# Назначаем обработчик
warnings.showwarning = handle_warnings_as_exceptions


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
                        ServerDisconnectedError) as e:
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
        products = await self.__parse_keywords_from_wb(text, page)
        if not products:
            return []
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



    @try_except(2, 1)
    async def __parse_keywords_from_wb(self, text: str, page: int):
        url = f'https://search.wb.ru/exactmatch/ru/common/v5/search?ab_testing=false&appType=32&curr=rub&dest=-1257786&page={page}&query={text}&resultset=catalog&sort=popular&suppressSpellcheck=false'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                text = await response.text()
        if not text:
            raise DataError('Пустой ответ от сервера', text)
        data = json.loads(text)
        if data == {}:
            return []
        try:
            assert data['payloadVersion'] == 2
        except Exception as e:
            raise DataError(f'{e}', text)
        products = data['data']['products']
        if not products:
            return []
        return products

    # @staticmethod
    # async def get_common_keyword(text: str)-> CommonKeyword:
    #     async with sm() as session:
    #         stmt = select(CommonKeyword).where(CommonKeyword.text == text)
    #         result = await session.execute(stmt)
    #         keyword = result.scalar()
    #         if not keyword:
    #             keyword = CommonKeyword(text=text)
    #             session.add(keyword)
    #             await session.commit()
    #     return keyword


parser = Parser()
#
# async def create_tasks_for_adding_wb_positions_to_db(positions: list[WBItemPosition]):
#     if positions == []:
#         return
#     async with sm() as session:
#         for position in positions:
#             stmt = select(WBItemPosition) \
#                 .where(and_(WBItemPosition.nmid == position.nmid,  # .options(joinedload(WBItemPosition.keyword))
#                             WBItemPosition.keyword_id == CommonKeyword.id)) \
#                 .order_by(WBItemPosition.timestamp.desc()) \
#                 .limit(1)
#             pos_in_db = await session.execute(stmt)
#             pos_in_db = pos_in_db.scalar_one_or_none()
#             if not pos_in_db:
#                 session.add(position)
#                 await session.commit()
#             else:
#                 if any([pos_in_db.base_position != position.base_position,
#                         pos_in_db.promo_position != position.promo_position,
#                         pos_in_db.cpm != position.cpm,
#                         pos_in_db.adv_id != position.adv_id,
#                         pos_in_db.real_position != position.real_position]):
#                     session.add(position)
#                     await session.commit()
#                 else:
#                     pos_in_db.timestamp = position.timestamp
#         await session.commit()


text_to_task = {}

write_to_db_queue = asyncio.Queue(10000)

queue_position_dict = {}

async def add_wb_positions_from_queue_to_db():
    position: WBItemPosition = await write_to_db_queue.get()
    key = f'{position.keyword.text}:{position.nmid}'
    queue_position_dict[key] = position
    last_key = list(queue_position_dict.keys())[-1]
    position = list(queue_position_dict.values())[-1]
    async with sm() as session:
        stmt = select(WBItemPosition) \
            .where(WBItemPosition.nmid == position.nmid,  # .options(joinedload(WBItemPosition.keyword))
                        WBItemPosition.keyword_id == CommonKeyword.id,
                   WBItemPosition.timestamp > datetime.datetime.now() - datetime.timedelta(hours=8)) \
            .order_by(WBItemPosition.timestamp.desc()) \
            .limit(1)
        pos_in_db = await session.execute(stmt)
        pos_in_db = pos_in_db.scalar_one_or_none()
        if not pos_in_db:
            keyword = position.keyword
            session.add(keyword)  # Добавляем keyword в сессию
            session.add(position)  # Добавляем position в сессию
            await session.commit()
    del queue_position_dict[last_key]


async def add_wb_positions(text: str, need_nmids: set[int]):
    pass
    global done_count
    for page in range(1, 100):
        positions = await parser.parse_keywords_from_wb(text, page)
        positions = [position for position in positions if position.nmid in need_nmids]
        if positions:
            await redis_manager.add_positions_to_redis(positions)
            logger.debug('Записали позиции в Редис')
            for position in positions:
                need_nmids.discard(position.nmid)
        else:
            break
        if not need_nmids:
            break
    else:
        # Если какие-то nmids не найдены
        not_found_positions = []
        for nmid in need_nmids:
            position = WBItemPosition(
                real_position=0,
                base_position=0,
                promo_position=0,
                keyword_text=text,
                timestamp=datetime.datetime.now(),
                nmid=nmid,
                cpm=0
            )
            not_found_positions.append(position)
            await redis_manager.add_positions_to_redis(not_found_positions)

async def limited_add_wb_positions(text:str, need_nmids: set[int], sem: asyncio.Semaphore):
    async with sem:
        try:
            await add_wb_positions(text, need_nmids)
        except Exception as e:
            logger.error(f'Ошибка при добавлении позиций в базу данных: {e}', exc_info=True)



async def parser_all_white_phrase(semaphore):
    tasks_by_text = {}
    while True:
        logger.debug('Получаем фразы для парсинга')
        all_white_phrases_generator: AsyncGenerator[str] = data_manager.get_phrases_for_parsing()
        async for text, need_nmids in all_white_phrases_generator:
            if text not in tasks_by_text:
                logger.debug(f'Добавляем фразу {text} в список задач')
                if need_nmids:
                    task = asyncio.create_task(limited_add_wb_positions(text, need_nmids, semaphore))
                    tasks_by_text[text] = task
            else:
                logger.debug(f'Фраза {text} уже есть в списке задач')
                task = tasks_by_text[text]
                if task.done():
                    if task.exception():
                        logger.error(f'Ошибка при выполнении задачи: {task.exception()}', exc_info=True)
                    del tasks_by_text[text]
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