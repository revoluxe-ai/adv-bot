from app.core.mp.wb.generated.promotion.v1.client.client import AuthenticatedClient
from ...base_auth_client import BaseAuthClient


class AdapterAuthClient(BaseAuthClient, AuthenticatedClient):
    pass
