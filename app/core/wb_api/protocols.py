"""
Протокол для работы с  WB API

"""

from typing import Protocol, runtime_checkable, Any

from ...modules.common_slaves.wildberries.ABC_WB_API import Headers


@runtime_checkable
class WBAPIProtocol(Protocol):

    headers: Headers
    HOST: str
    api_call_state: dict[str, dict[str, Any]]
    shop_id: str
