import asyncio
import logging
from functools import wraps
from typing import Optional

from app.utils.db.session_maker import get_async_session_maker as sm
from sqlalchemy import select
from app.modules.shop_runner.bidder.wb_api import WBApi
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
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

    def __init__(self, shop_id: str):
        self.shop_id = shop_id
        self.__access: Optional[WBCabinetAccess] = None

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
        wb_cabinet_id: int = self.__access.wb_cabinet.id
        stmt = select(AdvSetting)\
        .join(AdvSetting.wb_cabinet)\
        .filter(AdvSetting.wb_cabinet_id == wb_cabinet_id,
                AdvSetting.bot_active == True)
        async with sm() as session:
            result = await session.execute(stmt)
            adv: list[AdvSetting] = result.scalars().all()
        self._adv_settings = adv
        assert hasattr(self, '_adv_settings')


    async def __update_cpm_bid(self):
        await self._update_advs_models()
        assert hasattr(self, '_adv_settings')
        adv_settings = self._adv_settings
        adv_settings = filter(lambda adv: adv.bidder_active == True, adv_settings)
        wb_api = WBApi(self.__access)
        try:
            await asyncio.gather(*[run_bidder_process_for_adv(adv, wb_api) for adv in adv_settings])
        except ApiForbiddenError:
            raise ApiForbiddenError('Нет доступов для выполнения задачи')


    async def _update_cpm_bid(self):
        while True:
            try:
                await self.__update_cpm_bid()
                await asyncio.sleep(3*60)
            except ApiForbiddenError:
                logger.error(f'Нет прав для обновления ставки у магазина {self.shop_id}, обновляю токены')
                await asyncio.sleep(10)
                await self._update_access()
            except Exception:
                logger.error(f'Ошибка обновления ставки для {self.shop_id}', exc_info=True)
                await asyncio.sleep(10)


    async def _run(self):
        await asyncio.gather(
            self._update_cpm_bid()
        )

    async def run(self):
        await self._update_access()
        await self._run()











