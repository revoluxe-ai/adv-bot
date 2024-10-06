from app.modules.wb_adv_updater import data_manager


async def get_all_adv_ids():
    all_shop_ids = await data_manager.get_all_shop_ids()
    return all_shop_ids


async def get_all_shop_ids():
    return await data_manager.get_all_shop_ids()


async def get_active_adv_ids(shop_id):
    return await data_manager.get_active_adv_ids_for_shop(shop_id)
