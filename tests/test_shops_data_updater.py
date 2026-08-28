"""Live-PG тесты выборки AdvSetting по wb_cabinet_id в ShopDataUpdater.

Accepted API после rebase: ``ShopDataUpdater.get_adv_setting_by_wb_cabinet``
фильтрует только по ``wb_cabinet_id`` (без ``bot_active`` и без обязательного
``_search_adv_id``). Caller ``update_advs_data`` сам опционально добавляет
``search_adv_id`` при сборке списка adv_ids.

Требуют ``destructive_local``: используют fixture ``async_session``.
"""

from typing import Sequence, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.common_slaves.wildberries.shops_data_updater import (
    ShopDataUpdater,
    load_existing_advs_in_session,
)
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


async def test_load_existing_advs_in_session_reads_matching_adv_rows(
    async_session: AsyncSession,
):
    """Child seam читает существующие AdvSetting из live PG-сессии."""
    wb_cabinet = cast(WBCabinet, WBCabinetFactory.build())
    other_cabinet = cast(WBCabinet, WBCabinetFactory.build())

    matching = cast(
        AdvSetting,
        AdvSettingFactory.build(
            wb_cabinet=wb_cabinet,
            wb_cabinet_id=wb_cabinet.id,
            adv_id=4_200_001,
            bot_active=True,
            _search_adv_id=2,
        ),
    )
    other_setting = cast(
        AdvSetting,
        AdvSettingFactory.build(
            wb_cabinet=other_cabinet,
            wb_cabinet_id=other_cabinet.id,
            adv_id=4_200_002,
            bot_active=True,
            _search_adv_id=3,
        ),
    )
    try:
        async_session.add_all([wb_cabinet, other_cabinet, matching, other_setting])
        await async_session.flush()
        # Capture before expire: expired instance attrs trigger MissingGreenlet.
        matching_adv_id = matching.adv_id
        matching_pk = matching.id
        async_session.expire_all()

        adv_settings = await load_existing_advs_in_session(
            async_session,
            [matching_adv_id, 9_999_999],
        )
        assert len(adv_settings) == 1
        assert adv_settings[0].id == matching_pk
    finally:
        await async_session.rollback()
