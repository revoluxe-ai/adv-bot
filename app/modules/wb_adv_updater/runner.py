
from app.utils.redis_func_cache import set_config

from ...admin_bot.sender import sender_manager

set_config()
import asyncio
import logging

from app.modules.wb_adv_updater.data_managers import DataGetter
from app.utils.db.session_maker import get_async_session_maker

from ..common_slaves.wildberries import super_cabinet_manager as users_manager
from .manager import Manager

sm = get_async_session_maker()

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
        predicted = asyncio.Event()
        predicted.set()

        await asyncio.gather(
            self.shop_subscribe_control(),
            self.demo_subscribe(),
            self.run_update_keywords_on_wb(),
            self.update_cards_in_graph(),
            self.update_all_data_in_db(),
            self.update_min_ctr_in_global_wb_category_settings(),
            self.run_update_keyword_stat(need_update_model),
            self.run_update_vectors(need_update_model, update_model_on_new_features, predicted),
            self.run_update_model(update_model_on_new_features, need_update_model),
            self.run_update_predict_ctr(update_model_on_new_features, predicted),

            return_exceptions=False
            )

    async def run_update_predict_ctr(self,update_model_on_new_features: asyncio.Event, predicted: asyncio.Event):
        while True:
             logger.debug('Ожидание разрешения обновления ключей')
             await sender_manager.send_message_to_admin('Ожидание разрешения обновления ключей')
             await update_model_on_new_features.wait()
             logger.debug('Блокировка снята')
             await sender_manager.send_message_to_admin('Блокировка на обновление ключей снята')
             await self._manager.update_predict_ctr( predicted)
             await sender_manager.send_message_to_admin('Обновление ctr ключей завершено')
             await asyncio.sleep(1)


    async def run_update_keyword_stat(self, need_update_model: asyncio.Event):
        tasks = {}
        # not_first_runs = set()
        while True:
            accesses = users_manager.get_accesses_for_wb_cabinets()
            async for access in accesses:
                cabinet_id = access.wb_cabinet.id

                if cabinet_id not in tasks:
                    task = asyncio.create_task(
                        self._manager.update_keyword_stat(access, need_update_model))
                    tasks[cabinet_id] = task

                else:
                    if tasks[cabinet_id].done():
                        logger.info(f'Задача обновления статистики ключей завершена для кабинета {cabinet_id}')
                        if tasks[cabinet_id].exception():
                            logger.error(
                                f'Ошибка обновления статистики ключей: '
                                f'{tasks[cabinet_id].exception()},'
                                f' для кабинета {cabinet_id}'
                            )

                        del tasks[cabinet_id]
            await asyncio.sleep(0)


    async def run_update_vectors(self, need_update_model:asyncio.Event,
                                 update_model_on_new_features:asyncio.Event, predicted:asyncio.Event):

        await asyncio.gather(self._manager.update_wb_adv_phrase_in_db(need_update_model),
        self._manager.update_vectors_exec_mode(update_model_on_new_features, predicted, need_update_model))
        update_model_on_new_features.set()


    async def run_update_keywords_on_wb(self):
        await self._manager\
            .update_keywords_in_advs()
        await asyncio.sleep(1)


    async def run_update_model(self, update_model_on_new_features, need_update_model:asyncio.Event):
        while True:
            logger.debug('Старт цикла обновления модели')
            await sender_manager.send_message_to_admin('Ожидание разрешения на обновление модели')
            # await need_update_model.wait()
            logger.debug('need_update_model.wait пройден')
            await sender_manager.send_message_to_admin('Блокировка на обновление модели снята')
            await self._manager.update_model(update_model_on_new_features)
            logger.debug('Цикл обновления модели завершен')
            await sender_manager.send_message_to_admin('Обновление модели завершено')
            await asyncio.sleep(1)
            logger.debug('Установка clear для need_update_model')
            need_update_model.clear()
            await asyncio.sleep(1)

    async def update_cards_in_graph(self):
        while True:
            try:
                await self._manager.update_cards_in_graph()
                logger.debug('Карточки обновлены')
                await asyncio.sleep(1)
            except Exception as exc:
                logger.error(f'Ошибка обновления карточек в neo4j {exc}')
                await asyncio.sleep(1)

    async def update_min_ctr_in_global_wb_category_settings(self):
        while True:
            try:
                await self._manager.update_min_ctr_in_global_wb_category_settings()
            except Exception as e:
                logger.error(f'Ошибка обновления минимальных цен {e}')
            await asyncio.sleep(1)

    async def update_all_data_in_db(self):
        await self._manager.update_all_data_in_db_run()
        logger.debug("Данные в базе обновлены")
        await asyncio.sleep(1)

    async def demo_subscribe(self):
        while True:
            await self._manager.check_accesses()
            await asyncio.sleep(1)

    async def shop_subscribe_control(self):
        await self._manager.shop_subscribe_control()


