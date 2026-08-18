"""Интеграционные тесты обработчиков настроек кампании на disposable PG."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import const
from app.client_bot.user_interface.handlers.adv_setting import (
    reset_shop_non_relevant_phrases,
    wb_update_minus_keywords,
)
from app.client_bot.user_interface.handlers.adv_setting.utils.keyword_updater import (
    update_keywords,
)
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


class _MockSessionMaker:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        pass


async def _create_user_and_shop(
    session: AsyncSession, *, user_telegram_id: int, shop_suffix: str
) -> tuple[WBUserCabinet, WBCabinet]:
    user = User(user_telegram_id=user_telegram_id, username=f"user_{shop_suffix}")
    wb_cabinet = WBCabinet(
        shop_id=f"shop_{shop_suffix}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        expiration_time=datetime.now() + timedelta(days=7),
    )
    session.add_all([user, wb_cabinet])
    await session.flush()
    wb_user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=wb_cabinet.id,
        name=f"cab_{shop_suffix}",
    )
    session.add(wb_user_cabinet)
    await session.flush()
    return wb_user_cabinet, wb_cabinet


async def _create_adv(
    session: AsyncSession,
    *,
    wb_cabinet: WBCabinet,
    suffix: str,
    automatic_version: int = 2,
) -> AdvSetting:
    adv = AdvSetting(
        adv_id=100000 + abs(hash(suffix)) % 900000,
        name=f"adv_{suffix}",
        wb_cabinet_id=wb_cabinet.id,
        active_status="started",
        bot_active=True,
        automatic_version=automatic_version,
    )
    session.add(adv)
    await session.flush()
    return adv


def _make_callback(chat_id: int = 777) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)))


async def _get_keyword_statuses(
    session: AsyncSession, keyword_ids: list[int]
) -> dict[int, int]:
    session.expire_all()
    result = await session.execute(
        select(KeywordSetting).where(KeywordSetting.id.in_(keyword_ids))
    )
    rows = result.scalars().all()
    return {row.id: row.hard_status for row in rows}


async def _get_keyword_rows(
    session: AsyncSession, keyword_ids: list[int]
) -> dict[int, KeywordSetting]:
    session.expire_all()
    result = await session.execute(
        select(KeywordSetting).where(KeywordSetting.id.in_(keyword_ids))
    )
    rows = result.scalars().all()
    return {row.id: row for row in rows}

@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_keywords_returns_rowcount_and_updates_v3_modes(
    async_session: AsyncSession,
) -> None:
    target_uc, target_cabinet = await _create_user_and_shop(
        async_session, user_telegram_id=500005, shop_suffix="updater_target"
    )
    _, other_cabinet = await _create_user_and_shop(
        async_session, user_telegram_id=500006, shop_suffix="updater_other"
    )
    non_v3_adv = await _create_adv(
        async_session,
        wb_cabinet=target_cabinet,
        suffix="updater_non_v3",
        automatic_version=2,
    )
    v3_adv = await _create_adv(
        async_session,
        wb_cabinet=target_cabinet,
        suffix="updater_v3",
        automatic_version=3,
    )
    other_adv = await _create_adv(
        async_session,
        wb_cabinet=other_cabinet,
        suffix="updater_other",
        automatic_version=3,
    )

    non_v3_black = KeywordSetting(
        text="target_non_v3_black",
        adv_setting_id=non_v3_adv.id,
        hard_status=const.BLACK_LIST,
        strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
    )
    v3_black = KeywordSetting(
        text="target_v3_black",
        adv_setting_id=v3_adv.id,
        hard_status=const.BLACK_LIST,
        strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
    )
    target_auto = KeywordSetting(
        text="target_already_auto",
        adv_setting_id=non_v3_adv.id,
        hard_status=const.AUTO_MODE,
        strategy_mode=KeywordStrategyMode.OPTIMUM,
    )
    other_black = KeywordSetting(
        text="other_cabinet_black",
        adv_setting_id=other_adv.id,
        hard_status=const.BLACK_LIST,
        strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
    )
    keywords = [non_v3_black, v3_black, target_auto, other_black]
    async_session.add_all(keywords)
    await async_session.commit()

    updated_count = await update_keywords(async_session, target_uc.id)

    rows = await _get_keyword_rows(async_session, [kw.id for kw in keywords])
    assert updated_count == 2
    assert rows[non_v3_black.id].hard_status == const.AUTO_MODE
    assert rows[non_v3_black.id].strategy_mode == KeywordStrategyMode.MAX_CONVERSION
    assert rows[v3_black.id].hard_status == const.AUTO_MODE
    assert rows[v3_black.id].strategy_mode == KeywordStrategyMode.OFF
    assert rows[target_auto.id].hard_status == const.AUTO_MODE
    assert rows[target_auto.id].strategy_mode == KeywordStrategyMode.OPTIMUM
    assert rows[other_black.id].hard_status == const.BLACK_LIST
    assert rows[other_black.id].strategy_mode == KeywordStrategyMode.MAX_CONVERSION


async def test_reset_shop_non_relevant_phrases_updates_only_target_shop(async_session: AsyncSession) -> None:
    target_uc, target_cabinet = await _create_user_and_shop(
        async_session, user_telegram_id=500001, shop_suffix="target"
    )
    target_uc_id = target_uc.id
    _, other_cabinet = await _create_user_and_shop(
        async_session, user_telegram_id=500002, shop_suffix="other"
    )
    target_adv_1 = await _create_adv(async_session, wb_cabinet=target_cabinet, suffix="t1")
    target_adv_2 = await _create_adv(async_session, wb_cabinet=target_cabinet, suffix="t2")
    other_adv = await _create_adv(async_session, wb_cabinet=other_cabinet, suffix="o1")

    keywords = [
        KeywordSetting(text="target_black_1", adv_setting_id=target_adv_1.id, hard_status=const.BLACK_LIST),
        KeywordSetting(text="target_auto", adv_setting_id=target_adv_1.id, hard_status=const.AUTO_MODE),
        KeywordSetting(text="target_black_2", adv_setting_id=target_adv_2.id, hard_status=const.BLACK_LIST),
        KeywordSetting(text="other_black", adv_setting_id=other_adv.id, hard_status=const.BLACK_LIST),
    ]
    async_session.add_all(keywords)
    await async_session.commit()

    bot = AsyncMock()
    state = MagicMock()
    callback = _make_callback(chat_id=9991)
    callback_data = callbacks.ResetShopNonRelevantPhrases(
        wb_user_cabinet_original_id=target_uc_id
    )
    mock_sm = _MockSessionMaker(async_session)

    shop_menu_instance = AsyncMock()
    # Patch where the handler looks up names (submodule), not the re-export package.
    with patch(
        "app.client_bot.user_interface.handlers.adv_setting.adv_setting.ShopMenu",
        MagicMock(return_value=shop_menu_instance),
    ) as shop_menu_cls, patch(
        "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
        mock_sm,
    ):
        await reset_shop_non_relevant_phrases(
            callback=callback,
            callback_data=callback_data,
            bot=bot,
            state=state,
        )

    statuses = await _get_keyword_statuses(async_session, [kw.id for kw in keywords])
    assert statuses[keywords[0].id] == const.AUTO_MODE
    assert statuses[keywords[1].id] == const.AUTO_MODE
    assert statuses[keywords[2].id] == const.AUTO_MODE
    assert statuses[keywords[3].id] == const.BLACK_LIST

    send_text = bot.send_message.await_args.args[1]
    assert "Сброшено НРФ: 2" in send_text
    shop_menu_cls.assert_called_once_with(bot, 9991, state, target_uc_id)
    shop_menu_instance.assert_awaited_once()


async def test_reset_shop_non_relevant_phrases_handles_empty_case(async_session: AsyncSession) -> None:
    target_uc, target_cabinet = await _create_user_and_shop(
        async_session, user_telegram_id=500003, shop_suffix="empty_target"
    )
    target_uc_id = target_uc.id
    _, other_cabinet = await _create_user_and_shop(
        async_session, user_telegram_id=500004, shop_suffix="empty_other"
    )
    target_adv = await _create_adv(async_session, wb_cabinet=target_cabinet, suffix="et")
    other_adv = await _create_adv(async_session, wb_cabinet=other_cabinet, suffix="eo")

    keywords = [
        KeywordSetting(text="target_auto_only", adv_setting_id=target_adv.id, hard_status=const.AUTO_MODE),
        KeywordSetting(text="other_black_only", adv_setting_id=other_adv.id, hard_status=const.BLACK_LIST),
    ]
    async_session.add_all(keywords)
    await async_session.commit()

    bot = AsyncMock()
    state = MagicMock()
    callback = _make_callback(chat_id=9992)
    callback_data = callbacks.ResetShopNonRelevantPhrases(
        wb_user_cabinet_original_id=target_uc_id
    )
    mock_sm = _MockSessionMaker(async_session)

    shop_menu_instance = AsyncMock()
    # Patch where the handler looks up names (submodule), not the re-export package.
    with patch(
        "app.client_bot.user_interface.handlers.adv_setting.adv_setting.ShopMenu",
        MagicMock(return_value=shop_menu_instance),
    ), patch(
        "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
        mock_sm,
    ):
        await reset_shop_non_relevant_phrases(
            callback=callback,
            callback_data=callback_data,
            bot=bot,
            state=state,
        )

    statuses = await _get_keyword_statuses(async_session, [kw.id for kw in keywords])
    assert statuses[keywords[0].id] == const.AUTO_MODE
    assert statuses[keywords[1].id] == const.BLACK_LIST
    assert "Сброшено НРФ: 0" in bot.send_message.await_args.args[1]


async def test_wb_update_minus_keywords_raises_runtime_error_when_complex_adv_missing(
    async_session: AsyncSession,
) -> None:
    target_uc, target_cabinet = await _create_user_and_shop(
        async_session, user_telegram_id=500005, shop_suffix="minus_missing"
    )
    adv = await _create_adv(async_session, wb_cabinet=target_cabinet, suffix="minus_missing")
    await async_session.commit()

    bot = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    callback = _make_callback(chat_id=9993)
    callback_data = callbacks.WBUpdate(
        action="update_minus_keywords",
        adv_setting_original_id=adv.id,
    )
    mock_sm = _MockSessionMaker(async_session)
    hub = SimpleNamespace(wb_data_manager=MagicMock(), wb_manager=MagicMock())
    factory = SimpleNamespace(get_wb_manager_hub=MagicMock(return_value=hub))
    container = SimpleNamespace(
        module_resources=SimpleNamespace(
            wb_manager_hub_factory_container=SimpleNamespace(
                wb_manager_hub_factory=MagicMock(return_value=factory)
            )
        ),
        redis_client_wrapper=MagicMock(return_value=MagicMock()),
    )
    wb_shop_data_manager = SimpleNamespace(get_complex_advs=AsyncMock(return_value=[]))
    di_context = AsyncMock()
    di_context.__aenter__.return_value = container
    di_context.__aexit__.return_value = None

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            mock_sm,
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.DIManager.create",
            AsyncMock(return_value=di_context),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.WBShopDataManager",
            MagicMock(return_value=wb_shop_data_manager),
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match=f"ComplexAdv not found for adv_setting_original_id={adv.id}",
        ):
            await wb_update_minus_keywords(
                callback=callback,
                callback_data=callback_data,
                bot=bot,
                state=state,
            )


async def test_wb_update_minus_keywords_keeps_soft_message_for_bot_inactive(
    async_session: AsyncSession,
) -> None:
    target_uc, target_cabinet = await _create_user_and_shop(
        async_session, user_telegram_id=500006, shop_suffix="minus_inactive"
    )
    adv = await _create_adv(async_session, wb_cabinet=target_cabinet, suffix="minus_inactive")
    await async_session.commit()

    bot = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    callback = _make_callback(chat_id=9994)
    callback_data = callbacks.WBUpdate(
        action="update_minus_keywords",
        adv_setting_original_id=adv.id,
    )
    mock_sm = _MockSessionMaker(async_session)
    hub = SimpleNamespace(wb_data_manager=MagicMock(), wb_manager=MagicMock())
    factory = SimpleNamespace(get_wb_manager_hub=MagicMock(return_value=hub))
    container = SimpleNamespace(
        module_resources=SimpleNamespace(
            wb_manager_hub_factory_container=SimpleNamespace(
                wb_manager_hub_factory=MagicMock(return_value=factory)
            )
        ),
        redis_client_wrapper=MagicMock(return_value=MagicMock()),
    )
    wb_shop_data_manager = SimpleNamespace(
        get_complex_advs=AsyncMock(
            return_value=[
                SimpleNamespace(
                    adv_setting_original_id=adv.id,
                    bot_active=False,
                )
            ]
        )
    )
    di_context = AsyncMock()
    di_context.__aenter__.return_value = container
    di_context.__aexit__.return_value = None

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            mock_sm,
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.DIManager.create",
            AsyncMock(return_value=di_context),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.WBShopDataManager",
            MagicMock(return_value=wb_shop_data_manager),
        ),
    ):
        await wb_update_minus_keywords(
            callback=callback,
            callback_data=callback_data,
            bot=bot,
            state=state,
        )

    sent_texts = [call.args[1] for call in bot.send_message.await_args_list]
    assert "Обновляю минус-слова…" in sent_texts
    assert any(
        "Включите бота для кампании, затем повторите обновление минус-слов."
        in text
        for text in sent_texts
    )
