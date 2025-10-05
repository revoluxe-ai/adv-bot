import grpc  # type: ignore

from predict_ctr_service.grpc_service.predict_ctr_service_pb2 import PredictCtrRequest
from predict_ctr_service.grpc_service.predict_ctr_service_pb2_grpc import CtrServiceStub


class PredictCTRClient:
    """Минимальный async gRPC клиент для PredictCTRService, для тестов в tests/.

    Использование:
        client = PredictCTRClient()
        await client.connect()
        result = await client.predict([123], ["text"])
        await client.close()

    Или через async context manager:
        async with PredictCTRClient() as client:
            res = await client.predict(...)
    """

    def __init__(self, host: str = "localhost", port: int = 50053) -> None:
        self._target = f"{host}:{port}"
        self._channel: grpc.aio.Channel | None = None
        self._stub: CtrServiceStub | None = None

    async def connect(self) -> None:
        if self._channel is not None:
            return
        self._channel = grpc.aio.insecure_channel(self._target)
        # ensure channel is ready
        await self._channel.channel_ready()
        self._stub = CtrServiceStub(self._channel)

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None

    async def __aenter__(self) -> "PredictCTRClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def predict(self, nmids: list[int], phrases: list[str]) -> dict[str, float] | None:
        """Запрос предсказаний: возвращает словарь phrase->ctr или None при ошибке."""
        if self._stub is None:
            await self.connect()
        assert self._stub is not None
        request = PredictCtrRequest(nmids=nmids, phrases=phrases)
        response = await self._stub.PredictCtr(request)
        # response.predictions — map<string, double>
        try:
            return dict(response.predictions)
        except Exception:
            return response.predictions

