"""Live-PG тесты выборки AdvSetting по wb_cabinet_id в ShopDataUpdater.

Accepted API после rebase: ``ShopDataUpdater.get_adv_setting_by_wb_cabinet``
фильтрует только по ``wb_cabinet_id`` (без ``bot_active`` и без обязательного
``_search_adv_id``). Caller ``update_advs_data`` сам опционально добавляет
``search_adv_id`` при сборке списка adv_ids.

Требуют ``destructive_local``: используют fixture ``async_session``.
"""

from typing import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from tests.factories import AdvSettingFactory, WBCabinetFactory

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


async def test_get_adv_setting_by_wb_cabinet_returns_all_cabinet_settings(
    async_session: AsyncSession,
):
    """Возвращает AdvSetting кабинета независимо от bot_active и _search_adv_id."""
    wb_cabinet = WBCabinetFactory.build()
    other_cabinet = WBCabinetFactory.build()

    with_search = AdvSettingFactory.build(
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=False,
        _search_adv_id=2,
    )
    without_search = AdvSettingFactory.build(
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=True,
        _search_adv_id=None,
    )
    other_setting = AdvSettingFactory.build(
        wb_cabinet=other_cabinet,
        wb_cabinet_id=other_cabinet.id,
        bot_active=True,
        _search_adv_id=3,
    )
    try:
        async_session.add_all([wb_cabinet, other_cabinet, with_search, without_search, other_setting])
        await async_session.flush()

        adv_settings: Sequence[AdvSetting] = (
            await ShopDataUpdater.get_adv_setting_by_wb_cabinet(
                async_session,
                wb_cabinet_id=wb_cabinet.id,
            )
        )
        result_ids = {adv.id for adv in adv_settings}
        assert with_search.id in result_ids
        assert without_search.id in result_ids
        assert other_setting.id not in result_ids
    finally:
        await async_session.rollback()
