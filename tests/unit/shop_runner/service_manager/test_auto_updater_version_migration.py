"""Unit tests for AutoUpdater V1→V2 runtime migration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager.services.auto_updater_version_migration import (
    migrate_v1_auto_updaters_to_v2,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

pytestmark = pytest.mark.unit


def _make_adv(*, automatic_version: int, adv_setting_id: int = 1) -> ComplexAdv:
    adv_setting = MagicMock(spec=AdvSetting)
    adv_setting.id = adv_setting_id
    adv_setting.automatic_version = automatic_version

    async def _get_keywords(_: ComplexAdv, cache_only: bool = False):
        return []

    return ComplexAdv(
        shop_id="shop-migration",
        adv_setting=adv_setting,
        search_adv=None,
        get_keywords_func=_get_keywords,
    )


@pytest.mark.asyncio
async def test_migrate_v1_no_op_when_no_v1_advs() -> None:
    advs = [_make_adv(automatic_version=2), _make_adv(automatic_version=3, adv_setting_id=2)]

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_version_migration.sm"
    ) as sm_mock:
        migrated = await migrate_v1_auto_updaters_to_v2(advs)

    assert migrated == 0
    sm_mock.assert_not_called()
    assert advs[0].auto_updater_version == 2
    assert advs[1].auto_updater_version == 3


@pytest.mark.asyncio
async def test_migrate_v1_updates_db_and_in_memory() -> None:
    adv = _make_adv(automatic_version=1)
    execute_result = MagicMock()
    execute_result.rowcount = 1
    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_version_migration.sm",
        return_value=session_cm,
    ):
        migrated = await migrate_v1_auto_updaters_to_v2([adv])

    assert migrated == 1
    assert adv.auto_updater_version == 2
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_migrate_v1_only_affects_v1_in_mixed_list() -> None:
    adv_v1 = _make_adv(automatic_version=1, adv_setting_id=10)
    adv_v2 = _make_adv(automatic_version=2, adv_setting_id=11)
    adv_v3 = _make_adv(automatic_version=3, adv_setting_id=12)
    execute_result = MagicMock()
    execute_result.rowcount = 1
    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_version_migration.sm",
        return_value=session_cm,
    ):
        migrated = await migrate_v1_auto_updaters_to_v2([adv_v1, adv_v2, adv_v3])

    assert migrated == 1
    assert adv_v1.auto_updater_version == 2
    assert adv_v2.auto_updater_version == 2
    assert adv_v3.auto_updater_version == 3
