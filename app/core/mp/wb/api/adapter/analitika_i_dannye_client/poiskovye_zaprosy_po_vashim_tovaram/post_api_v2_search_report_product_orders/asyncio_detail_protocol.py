from typing import Protocol, Any
from app.core.mp.wb.api import AuthenticatedCastClient
from app.core.mp.wb.api.generated.analitika_i_dannye_client.models import ProductOrdersRequest, ErrorObject400, \
    ErrorObject403
from app.core.mp.wb.api.generated.marketing_i_prodvizhenie_client.types import Response




class AsyncioDetailedProtocol(Protocol):
    def __call__(self, client: AuthenticatedCastClient, body: ProductOrdersRequest) \
            -> Response[ErrorObject400 | ErrorObject403 | Any]:
        ...