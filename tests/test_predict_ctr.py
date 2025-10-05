import asyncio

import pytest
from unittest.mock import AsyncMock, patch

from predict_ctr_service import PredictCTRService
from tests.predict_ctr_client import PredictCTRClient


@pytest.mark.asyncio
async def test_predict_ctr_service_via_tests_client():
    """Запускаем сервер и вызываем его через тестовый клиент в tests/

    Мокируем Predictor.predict, чтобы не зависеть от Redis/ClickHouse и загрузки модели.
    """

    async def _fake_predict_generic(*args, **kwargs):
        # Последний позиционный аргумент ожидаем как список фраз
        phrases = args[-1] if args else kwargs.get("phrases", [])
        return {phrase: 0.1234 for phrase in phrases}

    # Патчим метод Predictor.predict в модуле predict_ctr_service.predictor
    with patch(
        "predict_ctr_service.predictor.Predictor.predict",
        new=AsyncMock(side_effect=_fake_predict_generic),
    ):
        service = PredictCTRService()
        serve_task = asyncio.create_task(service._serve())
        # Даем серверу время подняться
        await asyncio.sleep(0.5)

        client = PredictCTRClient()
        try:
            prediction = await client.predict([493134345], ["купальник сплошной женский с рукавами"])
            assert prediction is not None
            assert isinstance(prediction, dict)
            assert "купальник сплошной женский с рукавами" in prediction
        finally:
            # Закрываем клиент и останавливаем сервер (cancel task)
            try:
                await client.close()
            except Exception:
                pass
            serve_task.cancel()
            try:
                await serve_task
            except asyncio.CancelledError:
                pass
