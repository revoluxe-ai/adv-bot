from typing import Any, Protocol

from app.core.mp.wb.api import AuthenticatedCastClient
from app.core.mp.wb.api.generated.analitika_i_dannye_client.models import ProductHistoryRequest
from app.core.mp.wb.api.generated.analitika_i_dannye_client.types import Response


class AsyncioDetailedProtocol(Protocol):
    def __call__(
        self,
        client: AuthenticatedCastClient,
        body: ProductHistoryRequest,
    ) -> Response[Any]: ...


