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
# Вспомогательная функция для запуска асинхронной функции в отдельном процессе
def run_async_func_in_process(async_func, *args, **kwargs):
    print('Запускаем асинхронную функцию внутри отдельного цикла событий')
    loop = asyncio.app_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(async_func(*args, **kwargs))
    loop.close()
    return result

# Обёртка для синхронного вызова
def run_update_keywords_in_advs_sync(run_update_keywords_in_advs, event):
    print('Запускаем асинхронную функцию внутри отдельного цикла событий')
    return run_async_func_in_process(run_update_keywords_in_advs, event)


class Runner:
    def __init__(self):
        self._manager = Manager()
        self._data_getter = DataGetter()


    def run(self, debug_mode: bool):
        asyncio.run(self._main_loop(),
                    debug=debug_mode
                    )

    async def _main_loop(self):
        update_featers_block = asyncio.Event()
        update_featers_block.set()
        need_update_model = asyncio.Event()
        need_update_model.set()

        await asyncio.gather(
            # self.update_cards_in_graph(),
            # self.run_update_keyword_stat(need_update_model),
            # self.run_update_vectors(update_featers_block, need_update_model),
            # self.run_update_model(update_featers_block, need_update_model),
            self.run_update_predict_ctr(update_featers_block),
            # self.run_update_keywords_in_cabinets(saving_data_for_predictor, file_working),

            return_exceptions=False
            )

    async def run_update_predict_ctr(self, update_featers_block: asyncio.Event):
        await self._manager.update_predict_ctr(update_featers_block)










    async def run_update_keyword_stat(self,  need_update_model:asyncio.Event):
        tasks = {}
        while True:
            wb_user_cabinets = await users_manager.fetch_super_wb_user_cabinets()
            for super_wb_user_cabinet in wb_user_cabinets:
                cabinet_id = super_wb_user_cabinet.id
                if cabinet_id not in tasks:
                    tasks[cabinet_id] = \
                    asyncio.create_task(
                    self._manager.update_keyword_stat(super_wb_user_cabinet,
                     need_update_model))
                else:
                    if tasks[cabinet_id].done():
                        if tasks[cabinet_id].exception():
                            logger.error(f'Ошибка обновления статистики ключей: {tasks[cabinet_id].exception()}')




    async def run_update_vectors(self, update_featers_block: asyncio.Event,
                                  need_update_model:asyncio.Event):
        while True:
            await self._manager.update_wb_adv_phrase_in_db()
            await self._manager.update_vectors_exec_mode(update_featers_block)
            need_update_model.set()
            await asyncio.sleep(1)

    async def run_update_keywords_in_cabinets(self, saving_data_for_predictor, file_working: asyncio.Lock):
        while True:
            tasks: list[typing.Awaitable] = await self._manager\
                .update_keywords_in_advs(saving_data_for_predictor,
            file_working)
            tasks = [asyncio.create_task(task) for task in tasks]
            await asyncio.gather(*tasks)



    async def run_update_model(self, update_featers_block, need_update_model:asyncio.Event):
        while True:
            fit_logger.debug('Старт цикла обновления модели')
            await need_update_model.wait()
            fit_logger.debug('need_update_model.wait пройден')
            await self._manager.update_model(update_featers_block)
            fit_logger.debug('Цикл обновления модели завершен')
            await asyncio.sleep(1)
            fit_logger.debug('Установка clear для need_update_model')
            need_update_model.clear()

    async def update_cards_in_graph(self):
        while True:
            await self._manager.update_cards_in_graph()
            logger.debug('Карточки обновлены')
            await asyncio.sleep(60)




