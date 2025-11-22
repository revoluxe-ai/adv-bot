from abc import ABC
from app.core.mp.wb.api.api_client import AuthenticatedCastClient


class AbcMethod(ABC):
    def __init__(self, client: AuthenticatedCastClient):
        self._client = client
