__all__ = ["PredictCTRService"]


import asyncio
import logging

import grpc  # type: ignore

# from xgboost import XGBModel  # Теперь используем pipeline

from ..utils import fitter
from ..excs import NotLoadModelError, NotFoundItemFeaturesError
from ..grpc_service.predict_ctr_service_pb2 import PredictCtrResponse, PredictCtrRequest
from ..grpc_service.predict_ctr_service_pb2_grpc import (
    CtrServiceServicer,
    add_CtrServiceServicer_to_server,
)
from ..ml_model.model_utils import load_model, save_model
from ..predictor import Predictor

logger = logging.getLogger(__name__)


class PredictCTRService(CtrServiceServicer):
    def __init__(self, host: str = "localhost", port: int = 50053) -> None:
        # Держим XGBRegressor модель в памяти
        self._model = None
        self._host = host
        self._port = port

    async def _load_model(self) -> None:
        self._model = await load_model()
        if self._model is None:
            raise NotLoadModelError

    async def _get_predict(
        self, nmids: list[int], texts: list[str]
    ) -> dict[str, float]:
        if self._model is None:
            await self._load_model()
        predictor = Predictor(self._model)

        predictions: dict[str, float] = await predictor.predict(nmids, texts)

        return predictions

    async def PredictCtr(self, request: PredictCtrRequest, context):
        nmids = list(request.nmids)
        texts = list(request.phrases)
        try:
            predictions: dict[str, float] = await self._get_predict(nmids, texts)
            return PredictCtrResponse(predictions=predictions)
        except FileNotFoundError as exc:
            await context.abort(grpc.StatusCode.NOT_FOUND, f"Model file missing: {exc}")
        except NotLoadModelError as exc:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
        except NotFoundItemFeaturesError as exc:
            await context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
        except Exception as exc:
            logger.error("Unexpected error in PredictCtr", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, f"Unexpected error: {exc}")

    async def _serve(
        self,
    ) -> None:
        """
        Запуск gRPC сервера
        """
        server = grpc.aio.server()
        add_CtrServiceServicer_to_server(self, server)  # type: ignore
        server.add_insecure_port(f"{self._host}:{self._port}")
        try:
            await server.start()
            logger.info(f"gRPC server running on {self._host}:{self._port}")
            await server.wait_for_termination()
        except KeyboardInterrupt:
            await server.stop(grace=30)
        finally:
            await server.stop(grace=0)

    async def _update_model_loop(self) -> None:
        while True:
            try:
                model = await fitter.fit_and_get_new_model()
                await save_model(model)
                self._model = model
            except Exception as exc:
                raise exc
            await asyncio.sleep(1)

    async def main(self) -> None:
        await asyncio.gather(self._serve(), self._update_model_loop())
