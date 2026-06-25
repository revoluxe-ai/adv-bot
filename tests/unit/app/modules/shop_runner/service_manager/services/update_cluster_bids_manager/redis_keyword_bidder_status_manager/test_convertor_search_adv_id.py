"""dto_to_redis_commands использует search_adv_id."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.convertor import (
    dto_to_redis_commands,
)


@pytest.mark.unit
def test_dto_to_redis_commands_uses_search_adv_id() -> None:
    adv = MagicMock()
    adv.adv_id = 32824944
    adv.search_adv_id = 29734515

    commands = dto_to_redis_commands(adv, ["крем"])

    assert len(commands) == 1
    assert commands[0].adv_id == 29734515


@pytest.mark.unit
def test_dto_to_redis_commands_skips_without_search_adv_id() -> None:
    adv = MagicMock()
    adv.search_adv_id = None

    assert dto_to_redis_commands(adv, ["крем"]) == []
