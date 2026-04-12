"""
Скрипт запускает авто- и аукционные кампании для всех `AdvSetting`, у которых `bot_active=True`
и `active_status != 'done'`. Для каждой кампании создается `ComplexAdv`, и через `WBModifier`
стартуются обе кампании (auto + auction), если они не в состоянии `started`.
"""

import asyncio
import logging

from sqlalchemy import select

from redis.asyncio import Redis

from app.configs.app_config import AppConfig
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

"""
Скрипт запускает авто- и аукционные кампании для всех `AdvSetting` с `bot_active=True`
и `active_status != 'done'`. Фильтрация по nmids не выполняется.
"""

async def _get_cabinet(shop_id) -> WBCabinet:
    stmt = (
        select(WBCabinet)
        .where(
            WBCabinet.shop_id == shop_id,
        )
    )
    async with sm() as session:
        result = await session.execute(stmt)
        return result.scalar_one()

SHOP_ID = ...

async def _get_complex_advs() -> list[ComplexAdv]:
    cabinet = await _get_cabinet(SHOP_ID)
    complex_advs: list[ComplexAdv] = []
    manager = WBShopDataManager(wb_cabinet=cabinet)
    complex_advs.extend(await manager.get_complex_advs(load_extras=False))
    return complex_advs


async def _start_campaigns(
    complex_advs: list[ComplexAdv],
    wb_modifier_factory: WBManagerHubFactory,
) -> None:
    if not complex_advs:
        logger.info("Нет подходящих рекламных кампаний для запуска")
        return
    grouped: dict[str, list[ComplexAdv]] = {}
    for adv in complex_advs:
        grouped.setdefault(adv.shop_id, []).append(adv)

    for shop_id, advs in grouped.items():
        wb_manager_hub = wb_modifier_factory.get_wb_manager_hub(shop_id)
        modifier = wb_manager_hub.wb_modifier
        for adv in advs:
            if not adv.auto_adv_active_status:
                logger.info("Старту auto-кампанию adv_id=%s shop_id=%s", adv.auto_adv_id, shop_id)
                try:
                    await modifier.start_auto_campaign(adv)
                except Exception:
                    logger.exception('Ошибка')
            if adv.search_adv and not adv.search_adv_active_status:
                logger.info("Старту search-кампанию adv_id=%s shop_id=%s", adv.auction_adv_id, shop_id)
                try:
                    await modifier.start_auction_campaign(adv)
                except Exception:
                    logger.exception('Ошибка')


RedisAsync = Redis


async def _async_main() -> None:
    app_config = AppConfig.create()
    redis_config = app_config.infrastructure.redis
    redis_client_raw: RedisAsync = Redis(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        decode_responses=True,
    )
    _ = await redis_client_raw.ping()
    redis_client_wrapper = RedisClient(redis_client=redis_client_raw)
    httpx_client_handler = HttpxClientHandler()
    _ = await httpx_client_handler.init()

    wb_manager_hub_factory = WBManagerHubFactory(
        httpx_client_handler=httpx_client_handler,
        redis_client_wrapper=redis_client_wrapper,
    )

    try:
        complex_advs: list[ComplexAdv] = await _get_complex_advs()
        complex_advs = [adv for adv in complex_advs if adv.bot_active]
        await _start_campaigns(complex_advs, wb_manager_hub_factory)
    finally:
        await httpx_client_handler.shutdown()
        await redis_client_raw.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
