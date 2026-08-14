"""Integration tests for CPM bidder setup flow."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers import cpm_builder
from app.client_bot.user_interface.views.messages.messages import CPMSetting
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.wb_adv_updater.modules.bidder.tg_bot_handlers import on_off_controller

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


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


def _callback(chat_id: int = 100) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)))


def _message(text: str, chat_id: int = 100) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        answer=AsyncMock(),
    )


async def _create_adv_with_keywords(
    session: AsyncSession,
    *,
    max_place: int | None,
    max_cpm: int | None,
    bidder_active: bool = False,
    bot_active: bool = False,
    auto_update_target_place: bool = False,
    keyword_places: list[int | None] | None = None,
) -> tuple[int, list[KeywordSetting]]:
    wb_cabinet = WBCabinet(
        shop_id=f"shop_{datetime.now().timestamp()}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        expiration_time=datetime.now() + timedelta(days=7),
    )
    adv = AdvSetting(
        adv_id=int(datetime.now().timestamp() * 1000000) % 2_000_000_000,
        name="adv_cpm",
        wb_cabinet=wb_cabinet,
        active_status="started",
        bot_active=bot_active,
        bidder_active=bidder_active,
        max_place=max_place,
        max_cpm=max_cpm,
        auto_update_target_place=auto_update_target_place,
    )
    session.add_all([wb_cabinet, adv])
    await session.flush()
    adv_id = adv.id
    keywords = [
        KeywordSetting(
            text=f"kw_{index}",
            adv_setting_id=adv_id,
            target_place=place,
        )
        for index, place in enumerate(keyword_places or [None, None], start=1)
    ]
    session.add_all(keywords)
    await session.commit()
    return adv_id, keywords


async def _get_adv(session: AsyncSession, adv_id: int) -> AdvSetting:
    session.expire_all()
    result = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
    return result.scalar_one()


async def _get_keyword_places(session: AsyncSession, adv_id: int) -> list[int | None]:
    session.expire_all()
    result = await session.execute(
        select(KeywordSetting.target_place).where(KeywordSetting.adv_setting_id == adv_id)
    )
    return list(result.scalars())


def _button_texts(markup: object) -> list[str]:
    inline_keyboard = getattr(markup, "inline_keyboard")
    return [button.text for row in inline_keyboard for button in row]


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_set_auto_cpm_enables_immediately_when_settings_exist(
    async_session: AsyncSession,
) -> None:
    adv_id, _ = await _create_adv_with_keywords(
        async_session, max_place=5, max_cpm=120, bidder_active=False
    )
    state = _FakeState()
    bot = AsyncMock()
    callback_data = SimpleNamespace(adv_original_id=adv_id)
    cpm_page = AsyncMock()
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.modules.wb_adv_updater.modules.bidder.tg_bot_handlers.on_off_controller.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.views.messages.CPMSetting",
        MagicMock(return_value=cpm_page),
    ):
        await on_off_controller.get_min_position(_callback(), callback_data, bot, state)

    updated = await _get_adv(async_session, adv_id)
    assert updated.bidder_active is True
    assert state.state_calls == []
    cpm_page.assert_awaited_once_with(adv_id)


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_set_auto_cpm_requests_target_place_only_when_max_place_missing(
    async_session: AsyncSession,
) -> None:
    adv_id, _ = await _create_adv_with_keywords(
        async_session, max_place=0, max_cpm=250, bidder_active=False
    )
    state = _FakeState()
    bot = AsyncMock()
    callback_data = SimpleNamespace(adv_original_id=adv_id)
    target_prompt = AsyncMock()
    cpm_page = AsyncMock()
    max_prompt = AsyncMock()
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.modules.wb_adv_updater.modules.bidder.tg_bot_handlers.on_off_controller.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.views.messages.AutoCPMSettingGetMinPosition",
        MagicMock(return_value=target_prompt),
    ):
        await on_off_controller.get_min_position(_callback(), callback_data, bot, state)

    assert state.state_calls[-1] == states.CPMSetting.waiting_for_min_position
    target_prompt.assert_awaited_once_with(adv_id)

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.messages.CPMSetting",
        MagicMock(return_value=cpm_page),
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.messages.AutoCPMSettingGetMaxCPM",
        MagicMock(return_value=max_prompt),
    ):
        await cpm_builder.get_max_cpm(_message("7"), bot, state)

    updated = await _get_adv(async_session, adv_id)
    assert updated.max_place == 7
    assert updated.max_cpm == 250
    assert updated.bidder_active is True
    assert await _get_keyword_places(async_session, adv_id) == [7, 7]
    assert state.state_calls[-1] is None
    max_prompt.assert_not_awaited()
    cpm_page.assert_awaited_once_with(adv_id)


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_set_auto_cpm_requests_max_cpm_only_when_it_is_missing(
    async_session: AsyncSession,
) -> None:
    adv_id, _ = await _create_adv_with_keywords(
        async_session, max_place=8, max_cpm=None, bidder_active=False
    )
    state = _FakeState()
    bot = AsyncMock()
    callback_data = SimpleNamespace(adv_original_id=adv_id)
    max_prompt = AsyncMock()
    cpm_page = AsyncMock()
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.modules.wb_adv_updater.modules.bidder.tg_bot_handlers.on_off_controller.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.views.messages.AutoCPMSettingGetMaxCPM",
        MagicMock(return_value=max_prompt),
    ):
        await on_off_controller.get_min_position(_callback(), callback_data, bot, state)

    assert state.state_calls[-1] == states.CPMSetting.waiting_for_max_cpm
    max_prompt.assert_awaited_once_with()

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.messages.CPMSetting",
        MagicMock(return_value=cpm_page),
    ):
        await cpm_builder.set_max_cpm(_message("321"), bot, state)

    updated = await _get_adv(async_session, adv_id)
    assert updated.max_place == 8
    assert updated.max_cpm == 321
    assert updated.bidder_active is True
    cpm_page.assert_awaited_once_with(adv_id)
    assert state.state_calls[-1] is None


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_set_auto_cpm_requests_both_values_when_both_missing(
    async_session: AsyncSession,
) -> None:
    adv_id, _ = await _create_adv_with_keywords(
        async_session, max_place=0, max_cpm=None, bidder_active=False
    )
    state = _FakeState()
    bot = AsyncMock()
    callback_data = SimpleNamespace(adv_original_id=adv_id)
    target_prompt = AsyncMock()
    max_prompt = AsyncMock()
    cpm_page = AsyncMock()
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.modules.wb_adv_updater.modules.bidder.tg_bot_handlers.on_off_controller.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.views.messages.AutoCPMSettingGetMinPosition",
        MagicMock(return_value=target_prompt),
    ):
        await on_off_controller.get_min_position(_callback(), callback_data, bot, state)

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.messages.AutoCPMSettingGetMaxCPM",
        MagicMock(return_value=max_prompt),
    ):
        await cpm_builder.get_max_cpm(_message("11"), bot, state)

    assert state.state_calls[-1] == states.CPMSetting.waiting_for_max_cpm
    max_prompt.assert_awaited_once_with()
    assert await _get_keyword_places(async_session, adv_id) == [11, 11]

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.messages.CPMSetting",
        MagicMock(return_value=cpm_page),
    ):
        await cpm_builder.set_max_cpm(_message("444"), bot, state)

    updated = await _get_adv(async_session, adv_id)
    assert updated.max_place == 11
    assert updated.max_cpm == 444
    assert updated.bidder_active is True
    assert state.state_calls[-1] is None
    cpm_page.assert_awaited_once_with(adv_id)


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_change_target_position_updates_campaign_and_keywords_only(
    async_session: AsyncSession,
) -> None:
    adv_id, _ = await _create_adv_with_keywords(
        async_session, max_place=5, max_cpm=100, bidder_active=False, bot_active=False
    )
    state = _FakeState({"last_adv_original_id": adv_id})
    bot = AsyncMock()
    cpm_page = AsyncMock()
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.messages.CPMSetting",
        MagicMock(return_value=cpm_page),
    ):
        await cpm_builder.set_max_position_message(_message("13"), bot, state)

    updated = await _get_adv(async_session, adv_id)
    assert updated.max_place == 13
    assert updated.bot_active is False
    assert await _get_keyword_places(async_session, adv_id) == [13, 13]
    cpm_page.assert_awaited_once_with(adv_id)


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_change_manual_max_cpm_does_not_touch_bot_active(
    async_session: AsyncSession,
) -> None:
    adv_id, _ = await _create_adv_with_keywords(
        async_session, max_place=6, max_cpm=200, bidder_active=False, bot_active=False
    )
    state = _FakeState({"last_adv_original_id": adv_id})
    bot = AsyncMock()
    cpm_page = AsyncMock()
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.messages.CPMSetting",
        MagicMock(return_value=cpm_page),
    ):
        await cpm_builder.set_manual_cpm_message(_message("555"), bot, state)

    updated = await _get_adv(async_session, adv_id)
    assert updated.max_cpm == 555
    assert updated.bot_active is False
    cpm_page.assert_awaited_once_with(adv_id)


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_change_target_position_is_blocked_when_auto_target_place_enabled(
    async_session: AsyncSession,
) -> None:
    adv_id, _ = await _create_adv_with_keywords(
        async_session,
        max_place=5,
        max_cpm=100,
        auto_update_target_place=True,
        keyword_places=[2, 3],
    )
    state = _FakeState({"last_adv_original_id": adv_id})
    bot = AsyncMock()
    cpm_page = AsyncMock()
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.client_bot.user_interface.handlers.cpm_builder.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.cpm_builder.messages.CPMSetting",
        MagicMock(return_value=cpm_page),
    ):
        await cpm_builder.set_max_position_message(_message("13"), bot, state)

    updated = await _get_adv(async_session, adv_id)
    assert updated.max_place == 5
    assert await _get_keyword_places(async_session, adv_id) == [2, 3]
    cpm_page.assert_not_awaited()
    assert state.state_calls[-1] is None


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_off_auto_cpm_disables_bidder_and_reloads_menu(
    async_session: AsyncSession,
) -> None:
    """WRITE parent→child seam: off_auto_cpm clears bidder_active and reloads UI."""
    adv_id, _ = await _create_adv_with_keywords(
        async_session, max_place=5, max_cpm=120, bidder_active=True
    )
    state = _FakeState()
    bot = AsyncMock()
    callback_data = SimpleNamespace(adv_original_id=adv_id)
    cpm_page = AsyncMock()
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.modules.wb_adv_updater.modules.bidder.tg_bot_handlers.on_off_controller.sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.views.messages.CPMSetting",
        MagicMock(return_value=cpm_page),
    ):
        await on_off_controller.off_auto_cpm(_callback(), callback_data, bot, state)

    updated = await _get_adv(async_session, adv_id)
    assert updated.bidder_active is False
    cpm_page.assert_awaited_once_with(adv_id)


def test_cpm_setting_keyboard_shows_edit_buttons_when_bidder_is_disabled() -> None:
    view = CPMSetting.__new__(CPMSetting)
    view.adv_setting = SimpleNamespace(
        id=77,
        bidder_active=False,
        bidder_for_auto=False,
        bidder_step=None,
        auto_update_target_place=False,
    )

    button_texts = _button_texts(view.keyboard)

    assert "Изменить Максимальную ставку" in button_texts
    assert "Изменить целевую позицию" in button_texts
    assert "Скачать шаблон целевых позиций" in button_texts
    assert "Загрузить целевые позиции из файла" in button_texts


def test_cpm_setting_keyboard_hides_target_place_tools_when_auto_update_enabled() -> None:
    view = CPMSetting.__new__(CPMSetting)
    view.adv_setting = SimpleNamespace(
        id=77,
        bidder_active=False,
        bidder_for_auto=False,
        bidder_step=None,
        auto_update_target_place=True,
    )

    button_texts = _button_texts(view.keyboard)

    assert "Изменить Максимальную ставку" in button_texts
    assert "Изменить целевую позицию" not in button_texts
    assert "Скачать шаблон целевых позиций" not in button_texts
    assert "Загрузить целевые позиции из файла" not in button_texts
