"""Integration: ShopMenu tariff child + parent ``_load_all_data`` live-sm.

Authored under ``/opsx-close-external-gap``; do not run live without
``AUTHORIZE_ONE_LIVE_RUN`` + independent re-audit.
"""

from __future__ import annotations

import pytest

from app.modules.billing.pricer.pricer import Pricer, TariffMode
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_menu.message import ShopMenu

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


@pytest.mark.asyncio
async def test_load_tariff_details_in_session_reads_persisted_shop(
    async_session,
) -> None:
    """PURE_READ ShopMenu tariff child returns details for baseline shop."""
    cabinet = await async_session.get(WBCabinet, 1)
    assert cabinet is not None
    assert cabinet.shop_id == "test_shop_id"

    menu = object.__new__(ShopMenu)
    menu._pricer = Pricer()

    details = await ShopMenu._load_tariff_details_in_session(
        menu, async_session, cabinet.shop_id
    )
    assert details.mode in (TariffMode.AUTO, TariffMode.OLD)
    assert details.count >= 0
    # Re-read cabinet still present (read path did not mutate shop row).
    reread = await async_session.get(WBCabinet, cabinet.id)
    assert reread is not None
    assert reread.shop_id == cabinet.shop_id


@pytest.mark.asyncio
async def test_load_all_data_parent_live_sm_reads_cabinet_and_tariff(
    async_session,
    monkeypatch,
) -> None:
    """Parent ``ShopMenu._load_all_data`` loads cabinet+tariff via live sm.

    Redis/token-status side effects are stubbed; PG path uses real
    ``async_session`` through monkeypatched ``sm(read_only=True)``.
    """
    from datetime import datetime, timedelta
    from unittest.mock import AsyncMock

    import app.modules.shop_menu.message as shop_menu_mod
    from app.client_bot.ui_access import UiAccessMode
    from app.modules.common_slaves.wildberries.models import WBUserCabinet
    from app.modules.shop_menu.message import ShopMenu
    from app.utils.db.models import User

    class _LiveSessionMaker:
        def __init__(self, session) -> None:
            self.session = session
            self.last_read_only: bool | None = None

        def __call__(self, *, read_only: bool = False) -> "_LiveSessionMaker":
            self.last_read_only = read_only
            return self

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, *args: object) -> None:
            return None

    user = User(
        user_telegram_id=9_900_401,
        username="shop_menu_parent_live",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()

    cabinet = WBCabinet(
        shop_id=f"shop_menu_parent_{user.user_telegram_id}",
        active=True,
        demo=True,
        balance=10.0,
        bonus=1.0,
        expiration_time=datetime.utcnow() + timedelta(days=5),
    )
    async_session.add(cabinet)
    await async_session.flush()

    user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=cabinet.id,
        name="Parent Live Shop",
    )
    async_session.add(user_cabinet)
    await async_session.commit()

    live_sm = _LiveSessionMaker(async_session)
    monkeypatch.setattr(shop_menu_mod, "sm", live_sm)

    menu = object.__new__(ShopMenu)
    menu._user_telegram_id = user.user_telegram_id
    menu._state = AsyncMock()
    menu._state.update_data = AsyncMock()
    menu._wb_user_cabinet_original_id = user_cabinet.id
    menu._pricer = Pricer()
    menu._tariff_details = None
    menu._last_charge_at = None
    menu._billing_redis_manager = None
    menu._balance_snapshot_manager = None
    menu._ui_access_resolver = None
    menu._ui_access = UiAccessMode.FREE
    menu._token_status = None
    menu._token_status_loaded = False
    menu.get_shop_token_status = AsyncMock()  # type: ignore[method-assign]

    ok = await menu._load_all_data()
    assert ok is True
    assert live_sm.last_read_only is True
    assert menu._wb_cabinet is not None
    assert menu._wb_cabinet.id == cabinet.id
    assert menu._wb_user_cabinet.id == user_cabinet.id
    assert menu._tariff_details is not None
    assert menu._total_active_advs_count == menu._tariff_details.count

    reread = await async_session.get(WBUserCabinet, user_cabinet.id)
    assert reread is not None
    assert reread.name == "Parent Live Shop"
    menu._state.update_data.assert_awaited()
