import asyncio

import pytest

from . import PredictCTRService, PredictCTRClient


@pytest.mark.asyncio
async def test_predict_ctr_service():
    predict_ctr_service = PredictCTRService()
    asyncio.create_task(predict_ctr_service._serve())
    await asyncio.sleep(1)
    client = PredictCTRClient()
    nmids = [493134345]
    texts = ["купальник сплошной женский с рукавами"]
    prediction = await client.predict(nmids, texts)
    assert prediction
    assert isinstance(prediction, dict)
    assert "купальник сплошной женский с рукавами" in prediction
    print(prediction)
