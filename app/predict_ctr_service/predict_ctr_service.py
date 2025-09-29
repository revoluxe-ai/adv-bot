__all__ = ["PredictCTRService"]


import asyncio
import logging
import os
from typing import Any

import grpc

# from xgboost import XGBModel  # Теперь используем pipeline

from app.ml import fitter
from shared_lib.excs import NotLoadModelError, NotFoundItemFeaturesError
from ..grpc_service.predict_ctr_service_pb2 import PredictCtrResponse, PredictCtrRequest
from ..grpc_service.predict_ctr_service_pb2_grpc import (
    add_PredictCtrServiceServicer_to_server,
    CtrServiceServicer,
)
from ..model.model_utils import load_model, save_model
from ..predictor import Predictor

logger = logging.getLogger(__name__)
logger.debug("predict_ctr_service module imported")


class PredictCTRService(CtrServiceServicer):
    def __init__(self, host: str = "localhost", port: int = 50053) -> None:
        # Держим XGBRegressor модель в памяти
        self._model: Any | None = None
        self._host = host
        self._port = port
        self._disable_training = os.getenv("PREDICT_CTR_DISABLE_TRAINING", "0").lower() in {"1","true","yes","on"}
        # Legacy поведение: цикл обновления раз в 1 сек unless env переопределён
        self._refresh_seconds = int(os.getenv("PREDICT_CTR_REFRESH_SECONDS", "1"))
        logger.info(
            "Инициализация сервиса (legacy mode): host=%s port=%s disable_training=%s refresh=%s",
            self._host,
            self._port,
            self._disable_training,
            self._refresh_seconds,
        )
        logger.debug(f"PredictCTRService.__init__(host={host}, port={port})")

    async def _load_model(self) -> None:
        from ..model.model_utils import JOBLIB_PATH
        try:
            self._model = await asyncio.to_thread(load_model, str(JOBLIB_PATH))
            logger.debug("Модель успешно загружена из файла")
            if self._model is None:
                raise FileNotFoundError("Модель не загружена (None)")
            logger.info("Первичная загрузка модели завершена")
        except FileNotFoundError:
            logger.warning("Файл модели не найден. Инициализирую новую модель (DummyModel)")
            # Файла нет – создаем dummy модель через fitter
            try:
                new_model = await fitter.fit_and_get_new_model()
                if new_model is None:
                    raise NotLoadModelError("fit_and_get_new_model вернул None")
                await save_model(new_model)
                logger.debug("Dummy модель сохранена на диск")
                self._model = new_model
                logger.info("Новая модель инициализирована и сохранена (legacy первичный fit)")
            except Exception as exc:
                logger.error("Не удалось создать новую модель", exc_info=True)
                raise NotLoadModelError(str(exc))
        except Exception as exc:
            logger.error("Ошибка при загрузке модели", exc_info=True)
            raise NotLoadModelError(str(exc))

    async def _get_predict(self, nmids: list[int], texts: list[str]) -> dict[str, float]:
        logger.debug(f"_get_predict() called nmids={nmids} texts_count={len(texts)}")
        if self._model is None:
            logger.debug("_get_predict(): модель отсутствует, загружаю...")
            await self._load_model()
        predictor = Predictor(self._model)
        logger.debug("Predictor создан, запускаю predictor.predict()")
        predictions: dict[str, float] = await predictor.predict(nmids, texts)  # type: ignore[no-untyped-call]
        logger.debug(f"_get_predict() -> {len(predictions)} результатов")
        return predictions

    async def PredictCtr(self, request: PredictCtrRequest, context) -> PredictCtrResponse:  # type: ignore[override]
        logger.debug(f"PredictCtr gRPC call: nmids={list(request.nmids)} phrases_count={len(request.phrases)}")
        nmids = list(request.nmids)
        texts = list(request.phrases)
        try:
            predictions: dict[str, float] = await self._get_predict(nmids, texts)
            return PredictCtrResponse(predictions=predictions)
        except FileNotFoundError as exc:
            logger.debug("FileNotFoundError в PredictCtr")
            await context.abort(grpc.StatusCode.NOT_FOUND, f"Model file missing: {exc}")
        except NotLoadModelError as exc:
            logger.debug("NotLoadModelError в PredictCtr")
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
        except NotFoundItemFeaturesError as exc:
            logger.debug("NotFoundItemFeaturesError в PredictCtr")
            await context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
        except Exception as exc:
            logger.error("Unexpected error in PredictCtr", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, f"Unexpected error: {exc}")

    async def _serve(self) -> None:
        logger.debug("_serve() старт")
        server = grpc.aio.server()
        add_PredictCtrServiceServicer_to_server(self, server)  # type: ignore

        # Простая попытка бинда как в изначальном упрощённом варианте
        address = f"{self._host}:{self._port}"
        bind_result = server.add_insecure_port(address)
        if bind_result == 0:
            raise RuntimeError(f"Не удалось забиндить адрес {address}")
        logger.info("gRPC сервер слушает %s", address)

        try:
            await server.start()
            logger.debug("gRPC server started")
            logger.info(f"gRPC server running on {self._host}:{self._port}")
            await server.wait_for_termination()
            logger.debug("server.wait_for_termination() завершено")
        except KeyboardInterrupt:
            logger.debug("KeyboardInterrupt в _serve(), останавливаю сервер")
            await server.stop(grace=30)
        finally:
            logger.debug("Финальная остановка сервера (grace=0)")
            await server.stop(grace=0)

    async def _update_model_loop(self) -> None:
        logger.debug("_update_model_loop() старт")
        while True:
            try:
                logger.debug("_update_model_loop(): fit_and_get_new_model()")
                model = await fitter.fit_and_get_new_model()  # type: ignore[no-untyped-call]
                if model is not None:
                    await save_model(model)
                    logger.debug("_update_model_loop(): модель обновлена и сохранена")
                    self._model = model
                    logger.info("Модель переобучена (legacy cycle)")
                else:
                    logger.warning("_update_model_loop(): fit вернул None (модель не обновлена)")
            except Exception:
                 logger.error("Ошибка при обновлении модели", exc_info=True)
            logger.debug("_update_model_loop(): сон %s секунд", self._refresh_seconds)
            await asyncio.sleep(self._refresh_seconds)

    async def main(self) -> None:
        logger.debug(
            "PredictCTRService.main() -> старт; disable_training=%s", self._disable_training
        )
        tasks = [asyncio.create_task(self._serve(), name="serve_task")]
        if not self._disable_training:
            tasks.append(
                asyncio.create_task(self._update_model_loop(), name="training_loop")
            )
        else:
            logger.info("Цикл обучения отключен (PREDICT_CTR_DISABLE_TRAINING=1)")
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            if exc := task.exception():  # type: ignore
                logger.error("Task завершился с исключением", exc_info=exc)
        for task in pending:
            task.cancel()
        logger.debug("PredictCTRService.main() завершён")

    # Метаданные и расширенный функционал убраны для соответствия legacy
