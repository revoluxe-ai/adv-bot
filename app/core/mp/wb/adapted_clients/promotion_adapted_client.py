from ..generated.promotion.v1.client.client import AuthenticatedClient


class AdaptedClient(AuthenticatedClient):
    def __init__(self, httpx_client, token: str):


    async def request(self, method, url, **kwargs):






