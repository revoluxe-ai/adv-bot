from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.common_slaves.wildberries.api import WBApi, AdvertApi
from app.modules.common_slaves.wildberries.manager import WBManager




async def create_new_adv_company(company_name: str, nmids: set[int], access: WBCabinetAccess):
    wb_manager = WbManager(access)
    await advert_manager.create_new_company(company_name, nmids)



