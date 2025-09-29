from .client_proxy import ClientProxy


class ClientProxyFactory:

    def __init__(self):
        self._clients: dict[str, ClientProxy] = {}

    def get_client(self, base_url) -> ClientProxy:
        if base_url not in self._clients:
            self._clients[base_url] = ClientProxy(base_url=base_url)
        return self._clients[base_url]

    async def close_all_clients(self):
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
