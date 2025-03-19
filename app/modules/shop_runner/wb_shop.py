import asyncio
import logging
import typing
from collections import defaultdict
from functools import wraps
from typing import Optional, Iterable, List
from datetime import datetime
from app.core.wb_api import exceptions
from app.core.wb_api.ping_manager import PingManager
from app.modules.common_slaves.wildberries.api import AdvertApi
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.modules.shop_runner.modules.keywords_parser.keywords_parser import KeywordsParser
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.full_stat_adv_updater import wb_data_getter
from app.modules.shop_runner.wb_statistic_manager.backend.common_stat_manager import WBCommonStatManager
from app.modules.wb_adv_updater import data_manager
from app.settings import settings
from app.utils.db.session_maker import get_async_session_maker as sm
from sqlalchemy import select
from app.modules.common_slaves.wildberries.api import WBApi as CommonWBApi
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBToken
from app.modules.shop_runner.bidder.bidder_func import run_bidder_process_for_adv
from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.common_slaves.wildberries import super_cabinet_manager


logger = logging.getLogger(__name__)



def update_data():
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            await self._update_advs_models()
            await self._update_advs_keywords()
            result = await func(self, *args, **kwargs)
            return result
        return wrapper
    return decorator



def single_run():
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            event_name = func.__name__ + '_event'
            if not hasattr(self, event_name):
                event = asyncio.Event()
                event.set()
                setattr(self, event_name, event)

            event = getattr(self, event_name)

            if not event.is_set():
                await event.wait()
                return
            event.clear()
            try:
                result = await func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
                raise
            finally:
                event.set()
            return result

        return wrapper

    return decorator




class WBShop:

    def __init__(self, shop_id: str,
                 wb_cabinet_original_id: int,
                 all_api_keys: list[str],
                 parsing_queue_dict: dict[str, list]):
        self._parsing_queue_dict = parsing_queue_dict
        self.shop_id = shop_id
        self._wb_cabinet_original_id = wb_cabinet_original_id
        tokens_objs = []
        for key in all_api_keys:
            token = WBToken()
            token.api_key = key
            tokens_objs.append(token)
        access = WBCabinetAccess(
            tokens=tokens_objs,
            wb_cabinet=None,
            wb_user_cabinet=None,
        )
        self.__access = access
        self.__first_bidder_update_time: Optional[datetime] = None
        self.__keywords_for_advs = defaultdict(list[CalculatedKeyword])

    @single_run()
    async def _update_advs_keywords(self):
        advs = self._adv_settings
        for adv in advs:
            keywords = await data_manager.get_good_bad_phrases(adv)
            self.__keywords_for_advs[adv.adv_id] = keywords
            await asyncio.sleep(0)


    @single_run()
    async def _update_access(self):
        access = await super_cabinet_manager.get_access_for_wb_cabinet(self.shop_id)
        if access:
            self.__access = access
            return access
        else:
            raise ApiForbiddenError(f'Нет доступов для Shop ID {self.shop_id}')

    @single_run()
    async def _update_advs_models(self):
        shop_id = self.shop_id
        stmt = select(AdvSetting)\
        .join(AdvSetting.wb_cabinet)\
        .filter(WBCabinet.shop_id == shop_id,
                AdvSetting.bot_active == True)
        async with sm() as session:
            result = await session.execute(stmt)
            advs: list[AdvSetting] = result.scalars().all()
        self._adv_settings = advs
        assert hasattr(self, '_adv_settings')

    @update_data()
    async def __update_cpm_bid(self,  wb_api: AdvertApi):
        assert hasattr(self, '_adv_settings')
        adv_settings = self._adv_settings
        adv_settings = list(filter(lambda adv: adv.bot_active == True, adv_settings))
        if self._adv_settings == []:
            logger.debug(f'Модели не обновлены для магазина {self.shop_id}')
            self.__first_bidder_update_time = datetime.now()
            return
        try:
            logger.debug(f'Обновляю ставки для магазина {self.shop_id}')
            await asyncio.gather(*[self.__run_bidder_process_for_adv(adv, wb_api, self.shop_id) for adv in adv_settings])
            logger.debug(f'Все ставки обновлены для магазина {self.shop_id}')
        except ApiForbiddenError:
            raise ApiForbiddenError('Нет доступов для выполнения задачи')

    @update_data()
    async def __run_bidder_process_for_adv(self, adv_setting: AdvSetting, wb_api: AdvertApi, shop_id: str):
        try:
            await run_bidder_process_for_adv(adv_setting, wb_api, shop_id)
            if self.__first_bidder_update_time is None:
                self.__first_bidder_update_time = datetime.now()
        except exceptions.ApiForbiddenError as exc:
            raise exc
        except Exception as exc:
            logger.error('Ошибка обновления ставок в РК', exc_info=True)
            raise exc

    async def _update_cpm_bid(self):
        max_pause = 60*3 + 60
        access = self.__access
        wb_api = AdvertApi(access)
        while True:
            try:
                self.__first_bidder_update_time = None
                logger.debug(f'Обновляю ставку для магазина {self.shop_id}')
                await self.__update_cpm_bid(wb_api)
                logger.debug(f'Ставка обновлена для магазина {self.shop_id}')
                first_update_time = self.__first_bidder_update_time
                if not first_update_time:
                    first_update_time = datetime.now()
                pause = max_pause - (datetime.now() - first_update_time).seconds
                pause = max(1, pause)
                await asyncio.sleep(pause)
            except ApiForbiddenError:
                logger.error(f'Нет прав для обновления ставки у магазина {self.shop_id}, обновляю токены')
                await asyncio.sleep(60*60)
                await self._update_access()
                access = self.__access
                wb_api = CommonWBApi(access)
            except Exception as e:
                logger.error(f'Ошибка {e} обновления ставки для {self.shop_id}', exc_info=True)
                await asyncio.sleep(60)



    async def update_cpm_run(self):
        while True:
            try:
                await self._update_cpm_bid()
            except Exception as exc:
                logger.error(f'Ошибка {exc} обновления ставок в магазине', exc_info=True)


    @update_data()
    async def __update_common_sale_stat(self, wb_stat_manager: WBCommonStatManager):
        all_nmids = [adv.nmids[0] for adv in self._adv_settings if adv.bot_active == True]
        await wb_stat_manager.update_common_statistic(all_nmids)


    async def update_common_sale_stat(self):
        access = self.__access
        ping_manager = PingManager(access)
        wb_stat_manager = WBCommonStatManager(access)
        while True:
            try:
               await ping_manager.ping_analytics_rights_and_connect()
               await self.__update_common_sale_stat(wb_stat_manager)
            except ApiForbiddenError:
                logger.error('Ошибка доступа, пауза час и  обновление доступов с повторной попыткой')
                await asyncio.sleep(60*60)
                await self._update_access()
                access = self.__access
                wb_stat_manager = WBCommonStatManager(access)
            except Exception:
                logger.error('Ошибка обновления общей статистики', exc_info=True)
            finally:
                await asyncio.sleep(60*15)


    @staticmethod
    async def _update_full_stat_in_click_house(stats: Iterable[FullAdvStat]):
        await full_wb_adv_stat.insert(stats)


    @update_data()
    async def _update_full_adv_stat(self, wb_api: CommonWBApi):
        auto_adv_ids = {adv.adv_id for adv in self._adv_settings}
        auction_adv_ids = {adv.search_adv_id for adv in self._adv_settings if adv.search_adv_id}
        all_adv_ids = auto_adv_ids | auction_adv_ids
        full_stats: list[FullAdvStat] = await wb_data_getter.get_full_adv_stat_for_adv_ids(wb_api,
                                                                                       all_adv_ids,
                                                                                       threshold_dates=30)
        if full_stats:
            await self._update_full_stat_in_click_house(full_stats)
            date_time = datetime.now()
            for stat in full_stats:
                await data_manager.set_last_full_stat_update(stat.advertId, date_time)

    @update_data()
    async def update_full_adv_stat(self):
        access = self.__access
        wb_api = CommonWBApi(access)
        while True:
            try:
                await self._update_full_adv_stat(wb_api)
            except ApiForbiddenError:
                logger.debug('Нет доступов для обновления общей статистики')
                await self._update_access()
                access = self.__access
                wb_api = CommonWBApi(access)
            except Exception:
                logger.error('Ошибка обновления полной статистики обновления', exc_info=True)
            finally:
                await asyncio.sleep(60 * 15)


    @staticmethod
    async def _update_adv_data_from_wb_to_pg(shop_data_updater: ShopDataUpdater):
        try:
            await shop_data_updater.update_advs_data()
        except ApiForbiddenError as exc:
            raise exc
        except Exception as exc:
            logger.error('Ошибка обновления данных', exc_info=True)
            raise exc

    @update_data()
    async def _update_cards_data_from_wb_to_pg(self, shop_data_updater: ShopDataUpdater):
        adv_ids = [adv.adv_id for adv in self._adv_settings]
        try:
            await shop_data_updater.update_cards_data()
        except ApiForbiddenError as exc:
            raise exc
        except Exception as exc:
            logger.error('Ошибка обновления данных', exc_info=True)
            raise exc



    async def update_advs_data_from_wb_to_pg(self):
        wb_access = self.__access
        shop_data_updater = ShopDataUpdater(wb_access)
        while True:
            try:
                await self._update_adv_data_from_wb_to_pg(shop_data_updater)
            except ApiForbiddenError:
                await self._update_access()
                wb_access = self.__access
                shop_data_updater = ShopDataUpdater(wb_access)
            except Exception:
                logger.error('Ошибка обновления данных', exc_info=True)
            finally:
                await asyncio.sleep(60*3)


    async def _run(self):
        await self._update_access()
        await asyncio.gather(
            self.update_advs_data_from_wb_to_pg(),
            self.update_cards_data_from_wb_to_pf(),
            self.update_cpm_run(),
            self.update_common_sale_stat(),
            self.update_full_adv_stat(),

        )

    async def run(self):
        await self._run()

    # async def _update_full_stat_in_redis(self, full_stats: Iterable[FullAdvStat]):
    #     await redis_manager.set_full_stat_adv(full_stats)
    async def update_cards_data_from_wb_to_pf(self):
        access = self.__access
        shop_data_updater = ShopDataUpdater(access)
        while True:
            try:
                await self._update_cards_data_from_wb_to_pg(shop_data_updater)
            except ApiForbiddenError:
                logger.debug('Нет доступов для обновления общей статистики')
                await self._update_access()
                access = self.__access
                shop_data_updater = ShopDataUpdater(access)
            except Exception:
                logger.error('Ошибка обновления полной статистики обновления', exc_info=True)
            finally:
                await asyncio.sleep(60 * 15)


    async def _parsing_keywords(self, adv: AdvSetting):
        keywords = await data_manager.get_good_bad_phrases(adv)
        parser = KeywordsParser(self._parsing_queue_dict, self.shop_id, adv, keywords)
        try:
           parser.create_tasks_for_keywords_parser()
        except Exception as exc:
            raise exc
        try:
           await parser.parsing_all_keywords()
        except Exception as exc:
            raise exc

    async def _parsing_keywords_update(self, adv: AdvSetting):
        try:
            await self._parsing_keywords(adv)
        except Exception as exc:
            logger.error('Ошибка парсинга фраз', exc_info=True)
            await asyncio.sleep(60)

    async def parsing_keywords_run(self):
        adv_parsing_update_tasks = {}
        while True:
            await self._update_advs_models()
            advs = self._adv_settings
            for adv in advs:
                adv_original_id = adv.id

                async def implement_pause(func: typing.Awaitable):
                    time_out = settings.TIME_OUT_FOR_PARSER
                    if not time_out:
                        time_out = 60 * 10
                    pause_after = settings.PAUSE_AFTER_PARSING
                    if not pause_after:
                        pause_after = 60*60
                    try:
                        await asyncio.wait_for(func, timeout=time_out)
                    except TimeoutError:
                        logger.debug(f'Истек срок проверки парсинга магазина {self.shop_id}')

                    await asyncio.sleep(pause_after)
                if not adv_original_id in adv_parsing_update_tasks:
                    new_adv_parsing_task = asyncio.create_task(implement_pause(self._parsing_keywords_update(adv)))
                    adv_parsing_update_tasks[adv_original_id] = new_adv_parsing_task
                else:
                    old_task = adv_parsing_update_tasks[adv_original_id]
                    if old_task.done():
                        if old_task.exception():
                            logger.error(f'Ошибка парсинга ключей', exc_info=True)
                    del adv_parsing_update_tasks[adv_original_id]
                await asyncio.sleep(1)

            await asyncio.sleep(60)






