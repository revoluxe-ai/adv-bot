from typing import Union

from app.core.wb_api import exceptions
from app.modules.common_slaves.wildberries.models import WBToken, WBUserCabinet
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess



class Headers:
    def __init__(self, token: WBToken):
       self.current_token: WBToken = token
    @property
    def standart(self):
        return {'Authorization': self.current_token.api_key}



class InterfaceWBAPI:
    def __init__(self, wb_access: 'WBCabinetAccess'):
        tokens: list[WBToken] = wb_access.tokens
        self.access = wb_access
        wb_cabinet: Union[WBUserCabinet] = wb_access.wb_cabinet
        self.wb_cabinet = wb_cabinet
        assert wb_cabinet
        if not tokens:
            raise exceptions.ApiForbiddenError('Нет токенов для доступа к API',
                                               wb_user_cabinet=wb_access.wb_user_cabinet)
        tokens = sorted(tokens, key=lambda x: x.expires, reverse=True)
        self._free_tokens = tokens
        current_token = self._free_tokens.pop()
        self.headers = Headers(current_token)
        self._shop_id = current_token.shop_id

