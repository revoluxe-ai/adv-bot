from typing import Sequence

from app.modules.wb_adv_updater import data_manager


async def get_all_adv_ids() -> list[str]:
    all_shop_ids = await data_manager.get_all_shop_ids()
    return all_shop_ids


async def get_all_shop_ids() -> list[str]:
    return await data_manager.get_all_shop_ids()


async def get_all_active_shop_ids_with_active_advs() -> list[int]:
    return await data_manager.get_all_active_shop_ids_with_active_advs()


async def get_active_adv_ids(shop_id) -> Sequence[int]:
    return await data_manager.get_active_adv_ids_for_shop(shop_id)
