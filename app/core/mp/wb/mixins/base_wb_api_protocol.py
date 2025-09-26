from typing import Protocol


class BaseWBApiProtocol(Protocol):
    adapter_manager: AdapterManager
    shop_id: str
