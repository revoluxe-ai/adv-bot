import asyncio
import logging
from functools import wraps
from typing import Optional, Iterable
from datetime import datetime
from app.modules.full_stat_adv_updater import wb_data_getter
from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend.common_stat_manager import WBCommonStatManager
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm
from sqlalchemy import select
from .bidder.wb_api import WBApi as BidderWBApi
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
            await self._update_access()
            await self._update_advs_models()
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
                 all_api_keys: list[str]):
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

    @single_run()
    async def _update_access(self):
        access = await super_cabinet_manager.get_access_for_wb_cabinet(self.shop_id)
        if access:
            self.__access = access
        else:
            raise ApiForbiddenError(f'Нет доступов для Shop ID {self.shop_id}')

    @single_run()
    async def _update_advs_models(self):
        if not self.__access:
            await self._update_access()
        shop_id = self.shop_id
        stmt = select(AdvSetting)\
        .join(AdvSetting.wb_cabinet)\
        .filter(WBCabinet.shop_id == shop_id,
                AdvSetting.bot_active == True)
        async with sm() as session:
            result = await session.execute(stmt)
            adv: list[AdvSetting] = result.scalars().all()
        self._adv_settings = adv
        assert hasattr(self, '_adv_settings')

    @update_data()
    async def __update_cpm_bid(self):
        assert hasattr(self, '_adv_settings')
        adv_settings = self._adv_settings
        adv_settings = list(filter(lambda adv: adv.bot_active == True, adv_settings))
        if self._adv_settings == []:
            logger.debug(f'Модели не обновлены для магазина {self.shop_id}')
            self.__first_bidder_update_time = datetime.now()
            return
        wb_api = BidderWBApi(self.__access)
        try:
            logger.debug(f'Обновляю ставки для магазина {self.shop_id}')
            await asyncio.gather(*[self.__run_bidder_process_for_adv(adv, wb_api, self.shop_id) for adv in adv_settings])
            logger.debug(f'Все ставки обновлены для магазина {self.shop_id}')
        except ApiForbiddenError:
            raise ApiForbiddenError('Нет доступов для выполнения задачи')

    @update_data()
    async def __run_bidder_process_for_adv(self, adv_setting: AdvSetting, wb_api: BidderWBApi, shop_id: str):
        await run_bidder_process_for_adv(adv_setting, wb_api, shop_id)
        # await redis_manager.set_last_bid_update(adv_setting.adv_id)
        if self.__first_bidder_update_time is None:
            self.__first_bidder_update_time = datetime.now()


    async def _update_cpm_bid(self):
        max_pause = 60*3 + 60
        while True:
            try:
                self.__first_bidder_update_time = None
                logger.debug(f'Обновляю ставку для магазина {self.shop_id}')
                await self.__update_cpm_bid()
                logger.debug(f'Ставка обновлена для магазина {self.shop_id}')
                first_update_time = self.__first_bidder_update_time
                if not first_update_time:
                    first_update_time = datetime.now()
                pause = max_pause - (datetime.now() - first_update_time).seconds
                pause = max(1, pause)
                await asyncio.sleep(pause)
            except ApiForbiddenError:
                logger.error(f'Нет прав для обновления ставки у магазина {self.shop_id}, обновляю токены')
                await asyncio.sleep(1)
                await self._update_access()
            except Exception as e:
                logger.error(f'Ошибка {e} обновления ставки для {self.shop_id}', exc_info=True)
                await asyncio.sleep(1)

    async def update_cpm_run(self):
        while True:
           try:
               await self._update_cpm_bid()
           except Exception as e:
                logger.error(f'Ошибка {e} обновления ставки для {self.shop_id}', exc_info=True)
                await asyncio.sleep(1)

    @update_data()
    async def __update_common_sale_stat(self):
        all_nmids = [adv.nmids[0] for adv in self._adv_settings if adv.bot_active == True]
        wb_stat_manager =  WBCommonStatManager(self.__access)
        await wb_stat_manager.update_common_statistic(all_nmids)


    async def update_common_sale_stat(self):
        while True:
            try:
               await self.__update_common_sale_stat()
            except Exception:
                logger.error('Ошибка обновления общей статистики', exc_info=True)
            finally:
                await asyncio.sleep(60*15)

    async def _update_full_stat_in_click_house(self, stats: Iterable[FullAdvStat]):
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
                logger.error('Нет доступов для обновления общей статистики', exc_info=True)
                await self._update_access()
                access = self.__access
                wb_api = CommonWBApi(access)
            except Exception:
                logger.error('Ошибка обновления полной статистики обновления', exc_info=True)
            finally:
                await asyncio.sleep(60 * 15)


    async def _run(self):
        await self._update_access()
        await asyncio.gather(
            self.update_cpm_run(),
            # self.update_common_sale_stat(),
            # self.update_full_adv_stat(),
        )


    async def run(self):
        await self._run()

    # async def _update_full_stat_in_redis(self, full_stats: Iterable[FullAdvStat]):
    #     await redis_manager.set_full_stat_adv(full_stats)

