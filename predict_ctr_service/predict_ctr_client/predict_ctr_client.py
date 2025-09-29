import grpc

from .predict_ctr_service.grpc_service.predict_ctr_service_pb2 import (
    PredictCtrRequest,
)
from app.modules.grpcs.predict_ctr_service.grpc_service.predict_ctr_service_pb2_grpc import (
    CtrServiceStub,
)


class PredictCTRClient:
    """Асинхронный клиент gRPC для сервиса прогнозирования CTR"""

    def __init__(self, host: str = "localhost", port: int = 50053):
        self._target = f"{host}:{port}"
        self._channel: grpc.aio.Channel | None = None
        self._stub: CtrServiceStub | None = None

    async def connect(self) -> None:
        """Создаёт канал и stub, если их ещё нет"""
        if self._channel is None:
            self._channel = grpc.aio.insecure_channel(self._target)
            self._stub = CtrServiceStub(self._channel)

    async def close(self) -> None:
        """Закрывает канал"""
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None

    async def predict(
        self, nmids: list[int], phrases: list[str]
    ) -> dict[str, float] | None:
        """
        Отправляет запрос на прогноз CTR
        """
        if self._stub is None:
            await self.connect()
        if self._stub is None or not hasattr(self._stub, "PredictCtr"):
            return None
        request = PredictCtrRequest(nmids=nmids, phrases=phrases)
        response = await self._stub.PredictCtr(request)
        if response:
            return dict(response.predictions)
        return None

    # Поддержка async with
    async def __aenter__(self) -> "PredictCTRClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        await self.close()
