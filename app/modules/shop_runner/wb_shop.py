import asyncio
import logging
from functools import wraps
from typing import Optional
from datetime import datetime
from app.utils.db.session_maker import get_async_session_maker as sm
from sqlalchemy import select
from app.modules.shop_runner.bidder.wb_api import WBApi
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBToken
from app.modules.shop_runner.bidder.bidder_func import run_bidder_process_for_adv
from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.common_slaves.wildberries import super_cabinet_manager

logger = logging.getLogger(__name__)


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


    async def __update_cpm_bid(self)-> datetime:
        logger.debug(f'Обновляю модели для магазина {self.shop_id}')
        await self._update_advs_models()
        logger.debug(f'Модели обновлены для магазина {self.shop_id}')
        assert hasattr(self, '_adv_settings')
        adv_settings = self._adv_settings
        adv_settings = filter(lambda adv: adv.bidder_active == True, adv_settings)
        wb_api = WBApi(self.__access)
        try:
            logger.debug(f'Обновляю ставки для магазина {self.shop_id}')
            await asyncio.gather(*[run_bidder_process_for_adv(adv, wb_api, self.shop_id) for adv in adv_settings])
            logger.debug(f'Все ставки обновлены для магазина {self.shop_id}')
        except ApiForbiddenError:
            raise ApiForbiddenError('Нет доступов для выполнения задачи')


    async def _update_cpm_bid(self):
        max_pause = 60*3 + 30
        while True:
            try:
                start_time = datetime.now()
                logger.debug(f'Обновляю ставку для магазина {self.shop_id}')
                await self.__update_cpm_bid()
                logger.debug(f'Ставка обновлена для магазина {self.shop_id}')
                pause = max_pause - (datetime.now() - start_time).seconds
                pause = max(1, pause)
                await asyncio.sleep(pause)
            except ApiForbiddenError:
                logger.error(f'Нет прав для обновления ставки у магазина {self.shop_id}, обновляю токены')
                await asyncio.sleep(1)
                await self._update_access()
            except Exception as e:
                logger.error(f'Ошибка {e} обновления ставки для {self.shop_id}', exc_info=True)
                await asyncio.sleep(1)


    async def _run(self):
       await self._update_cpm_bid()

    async def run(self):
        await self._update_access()
        await self._run()











