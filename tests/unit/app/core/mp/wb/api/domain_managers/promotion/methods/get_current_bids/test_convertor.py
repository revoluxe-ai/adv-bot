"""Unit-тесты convertor normquery/get-bids: только search_adv_id."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.mp.wb.api.domain_managers.promotion.methods.get_current_bids.convertor import (
    dto_to_request,
)


@pytest.mark.unit
def test_dto_to_request_uses_search_adv_id_only() -> None:
    """Normquery cluster bids запрашиваются по search auction РК, не по auto adv_id."""
    search_adv = MagicMock()
    search_adv.adv_id = 29734515
    adv = MagicMock()
    adv.nmids = [10749810]
    adv.search_adv_id = 29734515
    adv.search_adv = search_adv
    adv.auto_adv_id = 32824944

    request = dto_to_request([adv])

    advert_ids = {item.advert_id for item in request.items}
    assert advert_ids == {29734515}
    assert 32824944 not in advert_ids


@pytest.mark.unit
def test_dto_to_request_skips_adv_without_search_campaign() -> None:
    adv = MagicMock()
    adv.nmids = [100]
    adv.search_adv_id = None
    adv.search_adv = None

    request = dto_to_request([adv])

    assert request.items == []
