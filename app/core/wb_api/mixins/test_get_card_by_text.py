import pytest

from app.core.wb_api.base import BaseAPI
from app.core.wb_api.mixins.content import ContentMixin


class TestWBApi(BaseAPI, ContentMixin):
    pass


@pytest.mark.asyncio
async def test_get_card_by_text(access_mock):
    wb_api = TestWBApi(access_mock)
    test_nmid = 111111
    await wb_api.get_card_by_text(test_nmid)
