import typing
from abc import ABC
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
    headers: Headers

