import asyncio

from sqlalchemy import select

from app.utils.db.session_maker import get_async_session_maker as sm

from .redis_manager import RedisShopManager
from ...common_slaves.wildberries.models.wb_cabinet import WBCabinet
from ...shop_id_filters import apply_shop_id_filters


async def update_active_shop_ids(redis_manager: RedisShopManager) -> None:
    # Получение списка магазинов с активными настройками
    stmt = select(WBCabinet.shop_id).where(WBCabinet.active)
    stmt = apply_shop_id_filters(stmt, WBCabinet.shop_id)
    async with sm() as session:
        result = await session.execute(stmt)
        all_needs_for_run_shop_ids = list(result.scalars().all())

    if not all_needs_for_run_shop_ids:
        return

    shop_ids: list[str] = list(all_needs_for_run_shop_ids)

    await redis_manager.update_active_shops(shop_ids)


async def run_shop_ids_update() -> None:
    redis_manager = RedisShopManager()
    while True:
        await update_active_shop_ids(redis_manager)
        await asyncio.sleep(15)
