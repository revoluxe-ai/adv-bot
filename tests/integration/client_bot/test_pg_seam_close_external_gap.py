"""Integration coverage for phone / workbook / super_cabinet PG seams.

Живой ``async_session`` + re-read persisted state. Авторство под
``/opsx-close-external-gap``; live запуск только после AUTHORIZE_ONE_LIVE_RUN.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import jwt

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import const
from app.client_bot.middlewars.phone_required import (
    load_user_phone_gate_fields_in_session,
)
from app.client_bot.user_interface.handlers.phone_collection import (
    save_user_phone_in_session,
)
from app.client_bot.user_interface.services.cpm_target_place_workbook import (
    TargetPlaceImportSummary,
    apply_target_place_rows_in_session,
    load_keywords_for_target_place_workbook_in_session,
)
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.super_cabinet_manager import (
    find_common_access_token_in_session,
    load_wb_cabinet_access_in_session,
    resolve_wb_cabinet_id_by_shop_id_in_session,
)
from app.utils.db.models import User
from app.modules.common_slaves.wildberries.models import WBToken

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]

_FIXED_EXP = 1_900_000_000
_CPM_SEAM_OWNER_TELEGRAM_ID = 9_100_003


def _build_token(*, acc: int, for_field: str | None, t: bool) -> str:
    """Собрать детерминированный JWT для integration-token seam теста."""
    payload: dict[str, object] = {
        "id": "test",
        "s": 102,
        "sid": "shop_test",
        "exp": _FIXED_EXP,
        "acc": acc,
        "t": t,
    }
    if for_field is not None:
        payload["for"] = for_field
    return jwt.encode(payload, "secret", algorithm="HS256")


async def test_load_user_phone_gate_fields_in_session_reads(
    async_session: AsyncSession,
) -> None:
    """Child PURE_READ seam returns passed_gate/phone via injected session."""
    telegram_id = 9_100_001
    user = User(
        user_telegram_id=telegram_id,
        username="phone_gate_seam",
        passed_gate=True,
        phone="+79991112233",
    )
    async_session.add(user)
    await async_session.flush()

    loaded = await load_user_phone_gate_fields_in_session(async_session, telegram_id)
    assert loaded is not None
    assert loaded.passed_gate is True
    assert loaded.phone == "+79991112233"


async def test_save_user_phone_in_session_persists_and_rereads(
    async_session: AsyncSession,
) -> None:
    """Child WRITE seam stores phone; re-select confirms persistence."""
    telegram_id = 9_100_002
    user = User(
        user_telegram_id=telegram_id,
        username="phone_save_seam",
        passed_gate=True,
        phone=None,
    )
    async_session.add(user)
    await async_session.flush()

    updated = await save_user_phone_in_session(
        async_session, telegram_id, "+79990001122"
    )
    assert updated is not None
    assert updated.phone == "+79990001122"

    async_session.expire_all()
    reread = await async_session.scalar(
        select(User.phone).where(User.user_telegram_id == telegram_id)
    )
    assert reread == "+79990001122"


async def _create_adv_with_keywords(
    async_session: AsyncSession,
    *,
    telegram_user_id: int = _CPM_SEAM_OWNER_TELEGRAM_ID,
) -> tuple[AdvSetting, list[KeywordSetting]]:
    user = User(
        user_telegram_id=telegram_user_id,
        username=f"cpm_seam_owner_{telegram_user_id}",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()
    cabinet = WBCabinet(
        shop_id=f"cpm_seam_{uuid.uuid4().hex}",
        active=True,
        expiration_time=datetime.utcnow() + timedelta(days=7),
        balance=0.0,
        bonus=0.0,
        demo=True,
        expiration_alarm_days_pass=None,
    )
    async_session.add(cabinet)
    await async_session.flush()
    wb_user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=cabinet.id,
        name="cpm-seam-owner",
    )
    async_session.add(wb_user_cabinet)
    await async_session.flush()
    adv = AdvSetting(
        adv_id=555_001,
        name="cpm-seam",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=100,
    )
    async_session.add(adv)
    await async_session.flush()
    keywords = [
        KeywordSetting(
            adv_setting_id=adv.id,
            text="alpha",
            hard_status=const.WHITE_LIST,
            target_place=3,
        ),
        KeywordSetting(
            adv_setting_id=adv.id,
            text="beta",
            hard_status=const.WHITE_LIST,
            target_place=5,
        ),
    ]
    async_session.add_all(keywords)
    await async_session.flush()
    return adv, keywords


async def test_load_keywords_for_workbook_in_session(
    async_session: AsyncSession,
) -> None:
    """Export child loads non-blacklist keywords via injected session."""
    adv, keywords = await _create_adv_with_keywords(async_session)
    loaded = await load_keywords_for_target_place_workbook_in_session(
        async_session, adv.id
    )
    assert [k.text for k in loaded] == ["alpha", "beta"]
    assert loaded[0].target_place == keywords[0].target_place


async def test_apply_target_place_rows_in_session_persists(
    async_session: AsyncSession,
) -> None:
    """Import child updates target_place and re-read confirms."""
    adv, keywords = await _create_adv_with_keywords(async_session)
    adv_pk = adv.id
    keyword_pk = keywords[0].id
    summary = TargetPlaceImportSummary(processed_rows=1)
    rows = [
        {
            "keyword_id": keyword_pk,
            "keyword": "alpha",
            "target_place": 9,
        }
    ]
    summary = await apply_target_place_rows_in_session(
        async_session,
        adv_pk,
        rows,
        summary,
        telegram_user_id=_CPM_SEAM_OWNER_TELEGRAM_ID,
    )
    assert summary.updated_rows == 1

    # Capture PKs before expire: expired instance attrs trigger MissingGreenlet.
    async_session.expire_all()
    place = await async_session.scalar(
        select(KeywordSetting.target_place).where(KeywordSetting.id == keyword_pk)
    )
    assert place == 9


async def test_resolve_and_load_wb_cabinet_access_in_session(
    async_session: AsyncSession,
) -> None:
    """Super-cabinet children resolve id; empty tokens stay read-only (no deactivate)."""
    shop_id = f"sc_seam_{uuid.uuid4().hex}"
    cabinet = WBCabinet(
        shop_id=shop_id,
        active=True,
        expiration_time=datetime.utcnow() + timedelta(days=7),
        balance=0.0,
        bonus=0.0,
        demo=True,
        expiration_alarm_days_pass=None,
    )
    async_session.add(cabinet)
    await async_session.flush()
    cabinet_pk = cabinet.id

    resolved = await resolve_wb_cabinet_id_by_shop_id_in_session(async_session, shop_id)
    assert resolved == cabinet_pk

    outcome = await load_wb_cabinet_access_in_session(async_session, cabinet_pk)
    assert outcome == shop_id
    # Чтение без токенов не выключает кабинет: деактивация только в get_access.
    async_session.expire_all()
    active = await async_session.scalar(
        select(WBCabinet.active).where(WBCabinet.id == cabinet_pk)
    )
    assert active is True


async def test_find_common_access_token_in_session_reads_valid_personal_token(
    async_session: AsyncSession,
) -> None:
    """Child common-access seam streams WBToken rows from live session and filters them."""
    user = User(
        user_telegram_id=9_200_001,
        username="common_access_seam",
    )
    async_session.add(user)
    await async_session.flush()

    non_personal_token = WBToken(
        api_key=_build_token(acc=1, for_field=None, t=False),
        user_id=user.id,
        active=True,
        shop_id="shop-a",
    )
    personal_token = WBToken(
        api_key=_build_token(acc=3, for_field="self", t=False),
        user_id=user.id,
        active=True,
        shop_id="shop-a",
    )
    async_session.add_all([non_personal_token, personal_token])
    await async_session.flush()
    client_session = MagicMock()

    with patch.object(
        super_cabinet_manager.token_check_righter,
        "check_all_rights",
        new_callable=AsyncMock,
        return_value=True,
    ) as rights_mock:
        found = await find_common_access_token_in_session(async_session, client_session)

    assert found is not None
    assert found.id == personal_token.id
    assert found.api_key == personal_token.api_key
    assert rights_mock.await_count == 1
