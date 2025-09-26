import httpx


class HTTPXClientWrapper:
    def __init__(self, client: httpx.AsyncClient, headers: dict):
        self._client = client
        self._headers = headers

    async def request(self, **kwargs):
        headers = dict(kwargs.pop("headers", {}))
        headers = {**self._headers, **headers}
        kwargs["headers"] = headers
        return await self._client.request(**kwargs)

    def __get_attr__(self, item):
        return getattr(self._client, item)
