import logging
from typing import Optional, Awaitable

import grpc
from dependency_injector.wiring import Provide, inject

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.models import PredictCTRMode
from app.modules.grpcs.predict_ctr_service.predict_ctr_client.predict_ctr_client import (
    PredictCTRClient,
)
from app.settings import settings
from .di import PredictCTRManagerContainer
from .redis_manager import PredictCTRRedisManager

logger = logging.getLogger(__name__)


class PredictCTRUpdateManager:
    """Менеджер для обновления прогнозов CTR"""

    def __init__(
        self,
    ) -> None:
        self._grpc_client: Optional[PredictCTRClient] = None

    async def _get_grpc_client(self) -> PredictCTRClient:
        """Получить gRPC клиент для predict_ctr сервиса"""
        if self._grpc_client is None:
            self._grpc_client = PredictCTRClient(
                host=settings.PREDICT_CTR_HOST,
                port=settings.PREDICT_CTR_PORT,
            )
            await self._grpc_client.connect()
        return self._grpc_client

    async def update_predict_ctr(
        self, adv: AdvSetting, keywords_coro: Awaitable[list[CalculatedKeyword]]
    ) -> None:
        keywords = await keywords_coro

        if not keywords:
            logger.debug(f"Нет ключевых слов для кампании {adv.adv_id}")
            return
        try:
            # Подготавливаем данные для gRPC запроса
            nmids = adv.nmids
            phrases = [keyword.text for keyword in keywords]

            logger.debug(
                f"Обрабатываем кампанию {adv.adv_id} с {len(nmids)} артикулами и {len(phrases)} ключами"
            )

            # Выполняем gRPC запрос
            grpc_client = await self._get_grpc_client()
            predictions = await self._make_grpc_request(grpc_client, nmids, phrases)

            if predictions is None:
                logger.warning(
                    f"Получен None от gRPC сервиса для кампании {adv.adv_id}"
                )
                return

            if not predictions:
                logger.warning(
                    f"Получен пустой словарь прогнозов от gRPC сервиса для кампании {adv.adv_id}"
                )
                return

            # Записываем результаты в Redis
            await self._save_predictions_to_redis(adv, predictions)

        except grpc.RpcError as e:
            await self._handle_grpc_error(e, adv.adv_id)
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при обработке кампании {adv.adv_id}: {e}",
                exc_info=True,
            )

    async def _make_grpc_request(
        self, grpc_client: PredictCTRClient, nmids: list[int], phrases: list[str]
    ) -> dict[str, float] | None:
        """Выполнить gRPC запрос для получения прогнозов"""
        try:
            return await grpc_client.predict(nmids, phrases)
        except grpc.RpcError as e:
            # Переподнимаем для обработки в основном методе
            raise e
        except Exception as e:
            logger.error(f"Ошибка выполнения gRPC запроса: {e}")
            return None

    @inject
    async def _save_predictions_to_redis(
        self,
        adv: AdvSetting,
        predictions: dict[str, float],
        redis_manager: PredictCTRRedisManager = Provide[
            PredictCTRManagerContainer.redis_manager
        ],
    ) -> None:
        """Сохранить прогнозы в Redis через pipeline"""
        try:
            pipeline = redis_manager._client.write_pipeline()
            saved_count = 0
            skipped_count = 0

            for key, predict_ctr in predictions.items():
                # Пропускаем None значения
                if predict_ctr is None:
                    logger.debug(
                        f"Пропускаем None прогноз для ключа '{key}' в кампании {adv.adv_id}"
                    )
                    skipped_count += 1
                    continue
                logger.debug(
                    f"Сохраняем predictions для ключа '{key} значение: {predict_ctr}"
                )
                # Записываем через метод из миксина
                await redis_manager.set_predict_ctr_with_pipeline_by_v2(
                    pipeline, adv, key, predict_ctr
                )

                saved_count += 1

            # Выполняем все операции одной командой, если есть что сохранять
            if saved_count > 0:
                await pipeline.execute()

            logger.debug(
                f"Сохранено {saved_count} прогнозов CTR для кампании {adv.adv_id}"
                f"{f', пропущено {skipped_count}' if skipped_count > 0 else ''}"
            )

        except Exception as e:
            logger.error(
                f"Ошибка сохранения прогнозов в Redis для кампании {adv.adv_id}: {e}",
                exc_info=True,
            )
            # Не прерываем процесс, продолжаем с другими кампаниями

    async def _handle_grpc_error(self, error: grpc.RpcError, adv_id: int) -> None:
        """Обработать ошибки gRPC"""
        if error.code() == grpc.StatusCode.INVALID_ARGUMENT:
            logger.error(f"Неверные аргументы для кампании {adv_id}: {error.details()}")
        elif error.code() in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.INTERNAL]:
            logger.error(
                f"Сервис недоступен или внутренняя ошибка для кампании {adv_id}: "
                f"код={error.code()}, детали={error.details()}"
            )
        else:
            logger.error(
                f"gRPC ошибка для кампании {adv_id}: код={error.code()}, "
                f"детали={error.details()}",
                exc_info=True,
            )

    async def close(self) -> None:
        """Закрыть соединения"""
        if self._grpc_client:
            await self._grpc_client.close()
            self._grpc_client = None
