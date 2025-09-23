class SetHttpxSessionAndHeadersMixin:
    def __init__(self, *args, **kwargs):
        # Не создаём сессию!
        super().__init__(*args, **kwargs)
        self._async_client = None

    def set_async_httpx_client(self, async_client):
        self._async_client = async_client

    async def request(self, method, url, **kwargs):
        # Добавляем нужные заголовки (например, токен)
        headers = kwargs.pop("headers", {})
        if hasattr(self, "token") and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return await self._async_client.request(method, url, headers=headers, **kwargs)
