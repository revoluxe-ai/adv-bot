import datetime
from app.utils.redis_manager import RedisEvent
from app.utils.redis_func_cache import set_config
from ..wb_keywords_parser import parser
from ...admin_bot.sender import sender_manager
set_config()
import asyncio
import logging
from app.modules.wb_adv_updater.data_manager import DataGetter
from app.utils.db.session_maker import get_async_session_maker
from ..common_slaves.wildberries import super_cabinet_manager as users_manager
from .wb_manager import Manager

sm = get_async_session_maker

logger = logging.getLogger(__name__)



class Runner:
    def __init__(self):
        self._manager = Manager()
        self._data_getter = DataGetter()

    def run(self, debug_mode: bool):
        asyncio.run(self.main_loop(),
                    debug=debug_mode)

    async def main_loop(self):
        update_model_on_new_features = asyncio.Event()
        need_update_model = asyncio.Event()
        need_update_model.set()
        predicted = RedisEvent(key='predicted')
        await predicted.set()
        await asyncio.gather(
            # self.clear_data_for_expired_wb_cabinets(),
            self.process_payment_for_advs(),
            # self.update_min_ctr_in_global_wb_category_settings(),
            self.run_update_vectors(need_update_model, update_model_on_new_features),
            self.run_update_model(update_model_on_new_features, need_update_model),
            self.run_update_predict_ctr(update_model_on_new_features, predicted),
            return_exceptions=False
        )

    async def run_update_predict_ctr(self,update_model_on_new_features: asyncio.Event, predicted: RedisEvent):
        while True:
             logger.debug('Ожидание разрешения обновления ключей')
             await update_model_on_new_features.wait()
             logger.debug('Блокировка снята')
             await self._manager.update_predict_ctr(predicted)
             await asyncio.sleep(1)


    async def run_update_keyword_stat(self, need_update_model: asyncio.Event, semaphore: asyncio.Semaphore):
        wb_cabinet_tasks = {}
        adv_update_tasks = {}
        # not_first_runs = set()
        while True:
            accesses = users_manager.get_accesses_for_wb_cabinets(semaphore)
            async for access in accesses:
                cabinet_id = access.wb_cabinet.id
                if cabinet_id not in wb_cabinet_tasks:
                    task = asyncio.create_task(
                        self._manager.update_keyword_stat(access,
                                                          need_update_model,
                                                          adv_update_tasks,
                                                          semaphore))
                    wb_cabinet_tasks[cabinet_id] = task

                else:
                    if wb_cabinet_tasks[cabinet_id].done():
                        logger.info(f'Задача обновления статистики ключей завершена для кабинета {cabinet_id}')
                        if wb_cabinet_tasks[cabinet_id].exception():
                            logger.error(
                                f'Ошибка обновления статистики ключей: '
                                f'{wb_cabinet_tasks[cabinet_id].exception()},'
                                f' для кабинета {cabinet_id}'
                            )

                        del wb_cabinet_tasks[cabinet_id]
            await asyncio.sleep(0)


    async def run_update_vectors(self, need_update_model:asyncio.Event,
                                 update_model_on_new_features:asyncio.Event):

        while True:
            await asyncio.gather(
                self.update_cards_in_graph(),
                self._manager.update_wb_adv_phrase_in_db(need_update_model),
            )
            await self._manager.update_vectors_exec_mode()
            update_model_on_new_features.set()
            need_update_model.set()
            await asyncio.sleep(0)


    async def run_update_minus_keywords_on_wb(self, semaphore: asyncio.Semaphore):
        await self._manager\
            .update_keywords_in_advs(semaphore)


    async def run_update_model(self, update_model_on_new_features, need_update_model:asyncio.Event):
        while True:
            logger.debug('Старт цикла обновления модели')
            # await need_update_model.wait()
            logger.debug('need_update_model.wait пройден')
            await self._manager.update_model(update_model_on_new_features)
            logger.debug('Цикл обновления модели завершен')
            await asyncio.sleep(1)
            logger.debug('Установка clear для need_update_model')
            need_update_model.clear()
            await asyncio.sleep(1)

    async def update_cards_in_graph(self):
        try:
            await self._manager.update_cards_in_graph()
            logger.debug('Карточки обновлены')
        except Exception as exc:
            logger.error(f'Ошибка обновления карточек в neo4j {exc}')






    async def update_min_ctr_in_global_wb_category_settings(self):
        while True:
            try:
                await self._manager.update_min_ctr_in_global_wb_category_settings()
            except Exception as e:
                logger.error(f'Ошибка обновления минимальных цен {e}')
            # await asyncio.sleep(60)

    async def update_all_data_in_db(self):
        tasks = {}
        while True:
            try:
                await self._manager.update_all_data_in_db_run(tasks=tasks)
            except Exception as exc:
                logger.error(f'Ошибка обновления данных в базе {exc}', exc_info=True)
                await asyncio.sleep(0)


    async def demo_subscribe(self):
        while True:
            await self._manager.check_accesses()
            await asyncio.sleep(60*60)

    async def shop_subscribe_control(self):
        await self._manager.shop_subscribe_control()

    async def clear_data_for_expired_wb_cabinets(self):
        while True:
            try:
                await self._manager.clear_expired_data()
            except Exception as e:
                logger.error(f'Ошибка очистки данных для просроченных кабинетов {e}', exc_info=True)
                await asyncio.sleep(0)

    async def process_payment_for_advs(self):
        while True:
            hours = datetime.datetime.now().hour
            if 12 < hours < 18:
                try:
                    await self._manager.process_payment_for_advs()
                except Exception as e:
                    logger.error(f'Ошибка обработки платежей {e}', exc_info=True)
            await asyncio.sleep(60*60)

    async def write_positions_to_db(self):
        while True:
            try:
                await parser.add_wb_positions_from_queue_to_db()
            except Exception as e:
                logger.error(f'Ошибка добавления позиций в базу {e}', exc_info=True)
            await asyncio.sleep(0)

    async def parser_all_white_phrase(self, semaphore: asyncio.Semaphore):
       await parser.parser_all_white_phrase(semaphore)


    async def reset_out_positions_in_redis(self):
        while True:
            try:
                await parser.reset_from_redis_positions_of_out_index()
            except Exception as e:
                logger.error(f'Ошибка сброса позиций в redis {e}', exc_info=True)

            await asyncio.sleep(10)


    async def keywords_parsing_process(self,semaphore: asyncio.Semaphore):
        while True:
            try:
                await self.__keywords_parsing_process(semaphore)
            except:
                logger.error('Ошибка процесса парсинга ключей', exc_info=True)
                await asyncio.sleep(0)

    async def __keywords_parsing_process(self, semaphore: asyncio.Semaphore):
        await asyncio.gather(
                   self. parser_all_white_phrase(semaphore),
                   # self.write_positions_to_db(),
                   self.payment_for_parsing_keyword(),
               return_exceptions=True)

    async def payment_for_parsing_keyword(self):
        while True:
            hours = datetime.datetime.now().hour
            if 12 < hours < 18:
                try:
                    await self._manager.process_payment_for_parsing()
                except Exception as e:
                    logger.error(f'Ошибка обработки платежей {e}', exc_info=True)
            await asyncio.sleep(60 * 60)





