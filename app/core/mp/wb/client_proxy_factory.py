class ClientProxyFactory:
    def __init__(self):
        self._clients: dict[str, object] = {}  # Было: ClientProxy

    def get_client(self, base_url) -> object:  # Было: ClientProxy
        if base_url not in self._clients:
            # self._clients[base_url] = ClientProxy(base_url=base_url)
            raise NotImplementedError("ClientProxy не реализован. Замените на актуальный клиент.")
        return self._clients[base_url]

    async def close_all_clients(self):
        for client in self._clients.values():
            # await client.aclose()
            pass
        self._clients.clear()
