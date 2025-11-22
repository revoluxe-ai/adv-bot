from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess


class WBApiAccessManager:
    def __init__(self, shop_id: str, wb_access: WBCabinetAccess):
        self._access = wb_access
