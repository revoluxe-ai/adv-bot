"""Tests for CPM target place workbook export/import and upload flow."""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import const
from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers import cpm_builder
from app.client_bot.user_interface.services.cpm_target_place_workbook import (
    TargetPlaceImportSummary,
    apply_target_place_workbook,
    build_target_place_workbook,
    read_target_place_workbook,
    write_target_place_workbook_rows,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User
from tests.helpers.telegram_message_asserts import (
    assert_caption_within_telegram_limit,
    assert_html_is_telegram_safe,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]

_WORKBOOK_OWNER_TELEGRAM_ID = 42_001


class _MockSessionMaker:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        pass


class _FakeState:
    def __init__(self, data: dict[str, int] | None = None) -> None:
        self.data: dict[str, int] = dict(data or {})
        self.state_calls: list[object] = []

    async def update_data(self, **kwargs: int) -> None:
        self.data.update(kwargs)

    async def get_data(self) -> dict[str, int]:
        return dict(self.data)

    async def set_state(self, state: object = None) -> None:
        self.state_calls.append(state)

    async def clear(self) -> None:
        self.data.clear()


async def _create_adv_with_keywords(
    session: AsyncSession,
    *,
    auto_update_target_place: bool = False,
    owner_telegram_id: int = _WORKBOOK_OWNER_TELEGRAM_ID,
) -> tuple[AdvSetting, list[KeywordSetting], AdvSetting]:
    user = User(
        user_telegram_id=owner_telegram_id,
        username=f"workbook_owner_{owner_telegram_id}",
        passed_gate=True,
    )
    session.add(user)
    await session.flush()
    cabinet = WBCabinet(
        shop_id=f"shop_{datetime.now().timestamp()}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        expiration_time=datetime.now() + timedelta(days=7),
    )
    adv = AdvSetting(
        adv_id=int(datetime.now().timestamp() * 1000000) % 2_000_000_000,
        name="adv_target_places",
        wb_cabinet=cabinet,
        active_status="started",
        bot_active=False,
        bidder_active=False,
        max_place=9,
        max_cpm=333,
        auto_update_target_place=auto_update_target_place,
    )
    other_adv = AdvSetting(
        adv_id=(int(datetime.now().timestamp() * 1000000) % 2_000_000_000) + 1,
        name="other_adv",
        wb_cabinet=cabinet,
        active_status="started",
        bot_active=True,
        bidder_active=True,
        max_place=15,
        max_cpm=777,
    )
    wb_user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet=cabinet,
        name="workbook_test_shop",
    )
    session.add_all([cabinet, wb_user_cabinet, adv, other_adv])
    await session.flush()
    keywords = [
        KeywordSetting(
            text="alpha",
            adv_setting_id=adv.id,
            hard_status=const.AUTO_MODE,
            target_place=3,
        ),
        KeywordSetting(
            text="beta",
            adv_setting_id=adv.id,
            hard_status=const.WHITE_LIST,
            target_place=5,
        ),
        KeywordSetting(
            text="blacklisted",
            adv_setting_id=adv.id,
            hard_status=const.BLACK_LIST,
            target_place=8,
        ),
        KeywordSetting(
            text="foreign",
            adv_setting_id=other_adv.id,
            hard_status=const.AUTO_MODE,
            target_place=21,
        ),
    ]
    session.add_all(keywords)
    await session.commit()
    return adv, keywords, other_adv


async def _fetch_adv(session: AsyncSession, adv_id: int) -> AdvSetting:
    session.expire_all()
    result = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
    return result.scalar_one()


async def _fetch_keyword_places(session: AsyncSession, adv_id: int) -> dict[str, int | None]:
    session.expire_all()
    result = await session.execute(
        select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_id)
    )
    return {row.text: row.target_place for row in result.scalars()}


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_export_workbook_uses_current_campaign_keywords_and_skips_non_relevant(
    async_session: AsyncSession,
) -> None:
    adv, keywords, _ = await _create_adv_with_keywords(async_session)
    _ = keywords
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.client_bot.user_interface.services.cpm_target_place_workbook._sm",
        mock_sm,
    ):
        content = await build_target_place_workbook(adv.id)

    rows = read_target_place_workbook(content)

    assert list(rows[0].keys()) == [
        "keyword_id",
        "keyword",
        "current_target_place",
        "target_place",
    ]
    assert [row["keyword"] for row in rows] == ["alpha", "beta"]
    assert rows[0]["current_target_place"] == 3
    assert rows[1]["current_target_place"] == 5
    assert pd.isna(rows[0]["target_place"])
    assert all(row["keyword"] != keywords[2].text for row in rows)


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_import_workbook_updates_only_valid_rows_and_keeps_adv_flags(
    async_session: AsyncSession,
) -> None:
    adv, keywords, other_adv = await _create_adv_with_keywords(async_session)
    adv_id = adv.id
    other_adv_id = other_adv.id
    other_keyword_id = keywords[3].id
    rows = [
        {
            "keyword_id": keywords[0].id,
            "keyword": "alpha",
            "current_target_place": 3,
            "target_place": 11,
        },
        {
            "keyword_id": keywords[1].id,
            "keyword": "beta",
            "current_target_place": 5,
            "target_place": None,
        },
        {
            "keyword_id": keywords[1].id,
            "keyword": "beta",
            "current_target_place": 5,
            "target_place": "bad",
        },
        {
            "keyword_id": other_keyword_id,
            "keyword": "foreign",
            "current_target_place": 21,
            "target_place": 19,
        },
    ]
    content = write_target_place_workbook_rows(rows)
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.client_bot.user_interface.services.cpm_target_place_workbook._sm",
        mock_sm,
    ):
        summary = await apply_target_place_workbook(
            adv_id, content, telegram_user_id=_WORKBOOK_OWNER_TELEGRAM_ID
        )

    assert summary.processed_rows == 4
    assert summary.updated_rows == 1
    assert summary.skipped_empty_rows == 1
    assert summary.validation_error_rows == 1
    assert summary.not_found_rows == 1

    updated_adv = await _fetch_adv(async_session, adv_id)
    assert updated_adv.bidder_active is False
    assert updated_adv.bot_active is False
    assert updated_adv.max_place == 9
    assert updated_adv.max_cpm == 333

    keyword_places = await _fetch_keyword_places(async_session, adv_id)
    assert keyword_places["alpha"] == 11
    assert keyword_places["beta"] == 5
    assert keyword_places["blacklisted"] == 8

    untouched_other_adv = await _fetch_adv(async_session, other_adv_id)
    assert untouched_other_adv.bidder_active is True


@pytest.mark.asyncio
async def test_upload_target_places_start_sets_fsm_and_prompts_user() -> None:
    state = _FakeState()
    bot = AsyncMock()
    callback = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=77)))
    callback_data = SimpleNamespace(adv_original_id=123)

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder._load_adv_setting",
        AsyncMock(return_value=SimpleNamespace(auto_update_target_place=False)),
    ):
        await cpm_builder.upload_target_places_template_start(
            callback, callback_data, bot, state
        )

    assert state.data["last_adv_original_id"] == 123
    assert state.state_calls[-1] == states.CPMSetting.waiting_for_target_place_workbook
    bot.send_message.assert_awaited_once()
    prompt_text = bot.send_message.await_args.args[1]
    assert_message_within_telegram_limit(prompt_text)
    assert_html_is_telegram_safe(prompt_text)
    assert_message_contains_required_phrases(
        prompt_text,
        [
            "Excel",
            "пустые ячейки",
            "меняется только target_place",
        ],
    )
    assert_no_raw_technical_text(prompt_text)


@pytest.mark.asyncio
async def test_upload_target_places_file_processes_document_and_sends_summary() -> None:
    state = _FakeState({"last_adv_original_id": 123})
    bot = AsyncMock()
    bot.download = AsyncMock(
        side_effect=lambda document, destination: destination.write(b"fake-workbook")
    )
    message = SimpleNamespace(
        document=SimpleNamespace(file_name="target_places.xlsx"),
        chat=SimpleNamespace(id=88),
        from_user=SimpleNamespace(id=_WORKBOOK_OWNER_TELEGRAM_ID),
        answer=AsyncMock(),
    )
    summary = TargetPlaceImportSummary(
        processed_rows=5,
        updated_rows=2,
        skipped_empty_rows=1,
        not_found_rows=1,
        validation_error_rows=1,
        errors=["Строка 6: target_place должно быть целым числом больше 0"],
    )
    cpm_page = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder._load_adv_setting",
        AsyncMock(return_value=SimpleNamespace(auto_update_target_place=False)),
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.apply_target_place_workbook",
        AsyncMock(return_value=summary),
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.messages.CPMSetting",
        MagicMock(return_value=cpm_page),
    ):
        await cpm_builder.upload_target_places_template_file(message, bot, state)

    assert message.answer.await_count == 2
    assert "начинаю обработку" in message.answer.await_args_list[0].args[0].lower()
    summary_text = message.answer.await_args_list[1].args[0]
    assert "Обновлено target_place: 2" in summary_text
    assert_message_within_telegram_limit(summary_text)
    assert_html_is_telegram_safe(summary_text)
    assert_message_contains_required_phrases(
        summary_text,
        [
            "меняется только target_place",
            "пустые ячейки",
        ],
    )
    assert_no_raw_technical_text(summary_text)
    cpm_page.assert_awaited_once_with(123)
    assert state.state_calls[-1] is None


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_download_target_place_template_caption_explains_excel_roundtrip() -> None:
    state = _FakeState()
    bot = AsyncMock()
    callback = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=77)))
    callback_data = SimpleNamespace(adv_original_id=123)

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder._load_adv_setting",
        AsyncMock(return_value=SimpleNamespace(auto_update_target_place=False)),
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.build_target_place_workbook",
        AsyncMock(return_value=b"xlsx"),
    ):
        await cpm_builder.download_target_places_template(
            callback, callback_data, bot, state
        )

    bot.send_document.assert_awaited_once()
    caption = bot.send_document.await_args.kwargs["caption"]
    assert_caption_within_telegram_limit(caption)
    assert_html_is_telegram_safe(caption)
    assert_message_contains_required_phrases(
        caption,
        [
            "Excel",
            "пустые ячейки",
            "меняется только target_place",
        ],
    )
    assert_no_raw_technical_text(caption)


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_download_target_place_template_is_blocked_when_auto_update_enabled(
    async_session: AsyncSession,
) -> None:
    adv, _, _ = await _create_adv_with_keywords(
        async_session, auto_update_target_place=True
    )
    state = _FakeState()
    bot = AsyncMock()
    callback = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=77)))
    callback_data = SimpleNamespace(adv_original_id=adv.id)
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder.sm",
        mock_sm,
    ):
        await cpm_builder.download_target_places_template(
            callback, callback_data, bot, state
        )

    bot.send_document.assert_not_awaited()
    bot.send_message.assert_awaited_once()


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_upload_target_places_file_is_blocked_when_auto_update_enabled(
    async_session: AsyncSession,
) -> None:
    adv, _, _ = await _create_adv_with_keywords(
        async_session, auto_update_target_place=True
    )
    state = _FakeState({"last_adv_original_id": adv.id})
    bot = AsyncMock()
    message = SimpleNamespace(
        document=SimpleNamespace(file_name="target_places.xlsx"),
        chat=SimpleNamespace(id=88),
        from_user=SimpleNamespace(id=_WORKBOOK_OWNER_TELEGRAM_ID),
        answer=AsyncMock(),
    )
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.apply_target_place_workbook",
        AsyncMock(),
    ) as apply_mock:
        await cpm_builder.upload_target_places_template_file(message, bot, state)

    apply_mock.assert_not_awaited()
    assert state.state_calls[-1] is None
    locked_text = message.answer.await_args.args[0]
    assert_message_within_telegram_limit(locked_text)
    assert_html_is_telegram_safe(locked_text)
    assert_message_contains_required_phrases(
        locked_text,
        [
            "автообновление target_place",
            "Max CPM остаётся доступным",
        ],
    )
    assert_no_raw_technical_text(locked_text)
