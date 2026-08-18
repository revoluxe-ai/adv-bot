"""Live PostgreSQL evidence for the refactored PG external-call seams.

Тесты вызывают production child-seams через реальную ``async_session`` и
проверяют persisted состояние повторным SQL-чтением. Live pytest намеренно
не запускается в рамках ``/opsx-close-external-gap``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers.set_common_bid_manual import (
    load_adv_setting_menu_entities_in_session,
)
from app.client_bot.user_interface.handlers.strategy_setting import (
    set_manual_strategy_in_session,
)
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.common_slaves.wildberries import wb_db_manager
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.utils.db.models import User

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


async def _create_cabinet(async_session: AsyncSession) -> WBCabinet:
    """Создать изолированный кабинет для PG seam-тестов."""
    cabinet = WBCabinet(
        shop_id=f"external_gap_{uuid.uuid4().hex}",
        active=True,
        expiration_time=datetime.utcnow() + timedelta(days=7),
        balance=0.0,
        bonus=0.0,
        demo=True,
    )
    async_session.add(cabinet)
    await async_session.flush()
    return cabinet


def _auction_adv(advert_id: int, *, name: str, cpm: int) -> AuctionAdv:
    """Сформировать минимальный payload, совместимый с ``AuctionAdv``."""
    return AuctionAdv(
        {
            "auction_multibids": [{"bid": cpm}],
            "status": 9,
            "advertId": advert_id,
            "type": 9,
            "autoParams": {
                "active": {"booster": False, "carousel": False, "recom": False},
                "subject": {"id": 1, "name": "subject"},
                "nms": [12345],
            },
            "unitedParams": [
                {
                    "searchCPM": cpm,
                    "subject": {"id": 1, "name": "subject"},
                    "nms": [12345],
                }
            ],
            "name": name,
            "dailyBudget": 1000,
            "startTime": "2025-01-01T00:00:00",
            "endTime": "2025-01-02T00:00:00",
            "createTime": "2025-01-01T00:00:00",
            "changeTime": "2025-01-01T00:00:00",
        }
    )


@pytest.mark.integration
async def test_strategy_child_writes_and_rereads_persisted_strategy(
    async_session: AsyncSession,
) -> None:
    """WRITE seam устанавливает ручную стратегию в реальной PG session."""
    cabinet = await _create_cabinet(async_session)
    adv_setting = AdvSetting(
        adv_id=uuid.uuid4().int % 1_000_000_000,
        name="strategy-seam",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        auto_update_strategy=False,
    )
    async_session.add(adv_setting)
    await async_session.flush()

    selected = await set_manual_strategy_in_session(
        async_session,
        adv_setting.id,
        Strategy.OPTIMUM.value,
    )
    await async_session.commit()

    persisted = await async_session.scalar(
        select(AdvSetting.strategy).where(AdvSetting.id == adv_setting.id)
    )
    assert selected is Strategy.OPTIMUM
    assert persisted is Strategy.OPTIMUM


@pytest.mark.integration
async def test_reload_menu_child_reads_both_entities_from_pg(
    async_session: AsyncSession,
) -> None:
    """PURE_READ reload seam возвращает cabinet и AdvSetting из PostgreSQL."""
    cabinet = await _create_cabinet(async_session)
    user = User(
        user_telegram_id=uuid.uuid4().int % 1_000_000_000,
        username=f"external_gap_{uuid.uuid4().hex}",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()
    user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=cabinet.id,
        name="reload-seam",
    )
    adv_setting = AdvSetting(
        adv_id=uuid.uuid4().int % 1_000_000_000,
        name="reload-seam-adv",
        wb_cabinet_id=cabinet.id,
        active_status="started",
    )
    async_session.add_all([user_cabinet, adv_setting])
    await async_session.flush()

    loaded_cabinet, loaded_adv = await load_adv_setting_menu_entities_in_session(
        async_session,
        user_cabinet.id,
        adv_setting.id,
    )

    assert loaded_cabinet is not None
    assert loaded_cabinet.id == user_cabinet.id
    assert loaded_adv is not None
    assert loaded_adv.id == adv_setting.id
    assert await async_session.scalar(
        select(AdvSetting.id).where(AdvSetting.id == adv_setting.id)
    ) == adv_setting.id


@pytest.mark.integration
async def test_wb_adv_writer_child_updates_persisted_row(
    async_session: AsyncSession,
) -> None:
    """WB adv writer child обновляет ORM-строку через переданную write-session."""
    cabinet = await _create_cabinet(async_session)
    advert_id = uuid.uuid4().int % 1_000_000_000
    adv_setting = AdvSetting(
        adv_id=advert_id,
        name="old-name",
        wb_cabinet_id=cabinet.id,
        active_status="paused",
    )
    async_session.add(adv_setting)
    await async_session.flush()

    await wb_db_manager._update_advs_in_session(  # noqa: SLF001
        async_session,
        [_auction_adv(advert_id, name="new-name", cpm=321)],
        cabinet.id,
    )
    await async_session.commit()

    persisted = await async_session.scalar(
        select(AdvSetting).where(AdvSetting.id == adv_setting.id)
    )
    assert persisted is not None
    assert persisted.name == "new-name"
    assert persisted.cpm == 321
