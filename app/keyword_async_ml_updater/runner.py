
from app.session_maker import get_async_session_maker
import typing
from app.keyword_async_ml_updater.data_managers import DataGetter
from .manager import Manager
import logging
import asyncio
from .users_manager import users_manager
sm = get_async_session_maker()

logger = logging.getLogger(__name__)

fit_logger = logging.getLogger('fit_logger')



class Runner:
    def __init__(self):
        self._manager = Manager()
        self._data_getter = DataGetter()

    def run(self, debug_mode: bool):
        logger.debug('Запуск цикла обновления ключей')
        asyncio.run(self.main_loop(),
                    debug=debug_mode
                    )

    async def main_loop(self):
        update_model_on_new_features = asyncio.Event()
        need_update_model = asyncio.Event()
        need_update_model.set()
        predicted = asyncio.Event()
        predicted.set()
        await asyncio.gather(
            self.run_update_keyword_stat(need_update_model),
            self.run_update_vectors(need_update_model, update_model_on_new_features, predicted),
            self.run_update_model(update_model_on_new_features, need_update_model),
            self.run_update_predict_ctr(update_model_on_new_features, predicted),
            self.run_update_keywords_on_wb(),
            self.update_min_ctr_in_global_wb_category_settings(),
            return_exceptions=False
            )

    async def run_update_predict_ctr(self,update_model_on_new_features: asyncio.Event, predicted: asyncio.Event):
        while True:
             await self._manager.update_predict_ctr(update_model_on_new_features, predicted)
             await asyncio.sleep(1)

    async def run_update_keyword_stat(self, need_update_model: asyncio.Event):
        tasks = {}
        while True:
            wb_user_cabinets = await users_manager.fetch_super_wb_user_cabinets()
            for super_wb_user_cabinet in wb_user_cabinets:
                cabinet_id = super_wb_user_cabinet.id
                if cabinet_id not in tasks:
                    task = asyncio.create_task(
                        self._manager.update_keyword_stat(super_wb_user_cabinet, need_update_model))
                    tasks[cabinet_id] = task

                else:
                    if tasks[cabinet_id].done():
                        logger.info(f'Задача обновления статистики ключей завершена для кабинета {cabinet_id}')
                        if tasks[cabinet_id].exception():
                            logger.error(f'Ошибка обновления статистики ключей: {tasks[cabinet_id].exception()}')

                        del tasks[cabinet_id]
                await asyncio.sleep(1)


    async def run_update_vectors(self, need_update_model:asyncio.Event,
                                 update_model_on_new_features:asyncio.Event, predicted:asyncio.Event):
        while True:
            await self._manager.update_wb_adv_phrase_in_db()
            await self._manager.update_vectors_exec_mode(update_model_on_new_features, predicted)
            need_update_model.set()
            await asyncio.sleep(1)

    async def run_update_keywords_on_wb(self):
        while True:
            await self._manager\
                .update_keywords_in_advs()
            await asyncio.sleep(1)


    async def run_update_model(self, update_model_on_new_features, need_update_model:asyncio.Event):
        while True:
            fit_logger.debug('Старт цикла обновления модели')
            await need_update_model.wait()
            fit_logger.debug('need_update_model.wait пройден')
            await self._manager.update_model(update_model_on_new_features)
            fit_logger.debug('Цикл обновления модели завершен')
            await asyncio.sleep(1)
            fit_logger.debug('Установка clear для need_update_model')
            need_update_model.clear()
            await asyncio.sleep(1)

    async def update_cards_in_graph(self):
        while True:
            await self._manager.update_cards_in_graph()
            logger.debug('Карточки обновлены')
            await asyncio.sleep(60)

    async def update_min_ctr_in_global_wb_category_settings(self):
        while True:
            await self._manager.update_min_ctr_in_global_wb_category_settings()
            await asyncio.sleep(1)



