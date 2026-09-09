"""Mock-only handoff proofs for `app/client_bot/user_interface/handlers/start/start.py`."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.client_bot.user_interface.handlers.start.start as start_module

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _SessionMakerMock:
    """Async context manager double that records `read_only=` calls."""

    def __init__(self, session: object) -> None:
        self.session = session

    def __call__(self, read_only: bool = False) -> "_SessionMakerMock":
        return self

    async def __aenter__(self) -> object:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.mark.asyncio
async def test_show_shops_list_hands_read_session_to_loader() -> None:
    """`show_shops_list` opens `sm(read_only=True)` and delegates the load."""
    session = MagicMock(name="show_shops_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    loader = AsyncMock(
        return_value=SimpleNamespace(passed_gate=True, wb_user_cabinets=[])
    )
    page_call = AsyncMock()
    page_ctor = MagicMock(return_value=page_call)

    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=101),
        message=SimpleNamespace(chat=SimpleNamespace(id=202)),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.clear = AsyncMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_user_with_wb_cabinets_in_session", loader),
        patch.object(
            start_module,
            "get_shop_ids_with_complete_token_status",
            AsyncMock(return_value=set()),
        ),
        patch.object(start_module, "ShopsListPage", page_ctor),
    ):
        await start_module.show_shops_list(callback, bot, state)

    loader.assert_awaited_once_with(session, 101)
    sm_mock.assert_called_with(read_only=True)
    page_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_cabinet_name_hands_read_session_to_loader() -> None:
    """`process_cabinet_name` reuses the shared user loader under read-only PG."""
    session = MagicMock(name="cabinet_name_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    loader = AsyncMock(
        return_value=SimpleNamespace(
            wb_user_cabinets=[],
        )
    )
    add_new_token_call = AsyncMock()
    add_new_token_ctor = MagicMock(return_value=add_new_token_call)

    message = SimpleNamespace(
        text="New cabinet",
        chat=SimpleNamespace(id=303),
        from_user=SimpleNamespace(id=404),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_user_with_wb_cabinets_in_session", loader),
        patch.object(start_module.messages, "AddNewTokenGet", add_new_token_ctor),
    ):
        await start_module.process_cabinet_name(message, bot, state)

    loader.assert_awaited_once_with(session, 404)
    sm_mock.assert_called_with(read_only=True)
    state.update_data.assert_awaited_once_with(cabinet_name="New cabinet")
    add_new_token_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_cabinet_api_hands_write_session_to_loaders() -> None:
    """`process_cabinet_api` opens a write session and hands it to PG loaders."""
    session = MagicMock(name="cabinet_api_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    user_id_loader = AsyncMock(return_value=1)
    existing_token = SimpleNamespace(user_id=1)
    existing_token_loader = AsyncMock(return_value=existing_token)
    open_existing_cabinet = AsyncMock(return_value=True)
    shop_id = "shop-101"
    validation_result = SimpleNamespace(
        is_valid_jwt=True,
        is_personal=True,
        is_read_only=False,
        is_expired=False,
        can_be_used_for_free=True,
        missing_required=set(),
        shop_id=shop_id,
    )
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=validation_result)
    validator_ctor = MagicMock(return_value=validator)

    message = SimpleNamespace(
        text="x" * 32,
        chat=SimpleNamespace(id=505),
        from_user=SimpleNamespace(id=606),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"cabinet_name": "Cabinet"})
    state.clear = AsyncMock()
    client_session = MagicMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_user_id_in_session", user_id_loader),
        patch.object(
            start_module,
            "_load_existing_wb_token_in_session",
            existing_token_loader,
        ),
        patch.object(
            start_module,
            "_open_existing_user_cabinet_by_shop_id",
            open_existing_cabinet,
        ),
        patch.object(start_module, "TokenPermissionsValidator", validator_ctor),
        patch.object(start_module.messages, "ShopUpdateInfo", MagicMock(return_value=AsyncMock())),
    ):
        await start_module.process_cabinet_api(message, bot, state, client_session)

    assert len(sm_mock.call_args_list) == 2
    assert all(call.kwargs.get("read_only") is False for call in sm_mock.call_args_list)
    user_id_loader.assert_awaited_once_with(session, 606)
    existing_token_loader.assert_awaited_once_with(session, "x" * 32, shop_id)
    open_existing_cabinet.assert_awaited_once_with(
        bot=bot,
        chat_id=505,
        state=state,
        user_id=1,
        shop_id="shop-101",
    )
    bot.send_message.assert_awaited_once_with(505, "Этот токен уже есть в системе.")
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_app_token_hands_read_session_to_cabinet_loader() -> None:
    """`add_app_token` opens `sm(read_only=True)` and loads a single cabinet."""
    session = MagicMock(name="add_token_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    cabinet = SimpleNamespace(name="Cabinet", wb_cabinet=SimpleNamespace())
    loader = AsyncMock(return_value=cabinet)
    add_token_call = AsyncMock()
    add_token_ctor = MagicMock(return_value=add_token_call)

    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=707)),
        from_user=SimpleNamespace(id=808),
    )
    callback_data = SimpleNamespace(wb_user_cabinet_original_id=77)
    bot = AsyncMock()
    state = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.get_state = AsyncMock(return_value="AddNewToken.token")

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_wb_user_cabinet_in_session", loader),
        patch.object(start_module.messages, "AddNewTokenGet", add_token_ctor),
    ):
        await start_module.add_app_token(callback, callback_data, bot, state)

    loader.assert_awaited_once_with(session, 77)
    sm_mock.assert_called_with(read_only=True)
    state.update_data.assert_awaited()
    add_token_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_toggle_cabinet_active_hands_read_session_to_owner_loader() -> None:
    """`toggle_cabinet_active_handler` loads the owner cabinet in read-only mode."""
    session = MagicMock(name="toggle_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    wb_cabinet = SimpleNamespace(shop_id="shop-909", active=True)
    cabinet = SimpleNamespace(wb_cabinet=wb_cabinet)
    loader = AsyncMock(return_value=cabinet)
    deactivate = AsyncMock(return_value=False)

    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=909)),
        from_user=SimpleNamespace(id=1001),
    )
    callback_data = SimpleNamespace(wb_user_cabinet_original_id=88)
    bot = AsyncMock()
    state = AsyncMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(
            start_module,
            "_load_wb_user_cabinet_for_owner_in_session",
            loader,
        ),
        patch.object(
            start_module,
            "deactivate_cabinet_atomic_with_user_trackers",
            deactivate,
        ),
    ):
        await start_module.toggle_cabinet_active_handler(
            callback, callback_data, bot, state
        )

    loader.assert_awaited_once_with(session, 88, 1001)
    sm_mock.assert_called_with(read_only=True)
    deactivate.assert_awaited_once()
    bot.send_message.assert_awaited_once_with(909, "Не удалось деактивировать магазин.")


@pytest.mark.asyncio
async def test_select_shop_hands_read_session_to_adv_loader() -> None:
    """`select_shop` delegates the AdvSetting load to a read-only session."""
    session = MagicMock(name="select_shop_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    loader = AsyncMock(return_value=[SimpleNamespace(name="adv-a")])
    adv_call = AsyncMock()
    adv_ctor = MagicMock(return_value=adv_call)

    callback = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=1111)))
    callback_data = SimpleNamespace(
        wb_user_cabinet_original_id=222,
        page=2,
        reset_filter=False,
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.update_data = AsyncMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(
            start_module,
            "_load_adv_settings_for_wb_user_cabinet_in_session",
            loader,
        ),
        patch.object(start_module.messages, "AdvCompanyChoicing", adv_ctor),
    ):
        await start_module.select_shop(callback, callback_data, bot, state)

    loader.assert_awaited_once_with(session, 222)
    sm_mock.assert_called_with(read_only=True)
    adv_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_cabinet_api_existing_shop_loads_advs_by_user_cabinet_id() -> None:
    """Existing WBCabinet path must load advs by WBUserCabinet.id, not WBCabinet.id."""
    session = MagicMock(name="cabinet_api_existing_shop_session")
    session.commit = AsyncMock()
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    wb_cabinet = SimpleNamespace(id=100, active=True)
    wb_user_cabinet = SimpleNamespace(id=500)
    user_id_loader = AsyncMock(return_value=1)
    existing_token_loader = AsyncMock(return_value=None)
    load_wb_cabinet = AsyncMock(return_value=wb_cabinet)
    load_user_cabinet = AsyncMock(return_value=None)
    ensure_binding = AsyncMock(return_value=wb_user_cabinet)
    adv_loader = AsyncMock(return_value=[SimpleNamespace(name="adv-1")])
    adv_call = AsyncMock()
    adv_ctor = MagicMock(return_value=adv_call)
    shop_id = "shop-existing"
    validation_result = SimpleNamespace(
        is_valid_jwt=True,
        is_personal=True,
        is_read_only=False,
        is_expired=False,
        can_be_used_for_free=True,
        missing_required=set(),
        shop_id=shop_id,
    )
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=validation_result)

    message = SimpleNamespace(
        text="z" * 32,
        chat=SimpleNamespace(id=707),
        from_user=SimpleNamespace(id=808),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"cabinet_name": "Cabinet"})
    client_session = MagicMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_user_id_in_session", user_id_loader),
        patch.object(
            start_module,
            "_load_existing_wb_token_in_session",
            existing_token_loader,
        ),
        patch.object(start_module, "persist_wb_token_in_session", AsyncMock()),
        patch.object(
            start_module,
            "_load_wb_cabinet_by_shop_id_in_session",
            load_wb_cabinet,
        ),
        patch.object(
            start_module,
            "_load_user_cabinet_for_user_in_session",
            load_user_cabinet,
        ),
        patch.object(
            start_module,
            "ensure_wb_user_cabinet_binding_in_session",
            ensure_binding,
        ),
        patch.object(
            start_module,
            "_load_adv_settings_for_wb_user_cabinet_in_session",
            adv_loader,
        ),
        patch.object(
            start_module,
            "TokenPermissionsValidator",
            MagicMock(return_value=validator),
        ),
        patch.object(
            start_module.messages,
            "ShopUpdateInfo",
            MagicMock(return_value=AsyncMock()),
        ),
        patch.object(start_module.messages, "AdvCompanyChoicing", adv_ctor),
    ):
        await start_module.process_cabinet_api(message, bot, state, client_session)

    adv_loader.assert_awaited_once_with(session, 500)
    adv_ctor.assert_called_once_with(bot, 707, 500, [adv_loader.return_value[0]], state)
    adv_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_cabinet_api_strips_whitespace_before_validate_and_wb_token() -> None:
    """Surrounding whitespace must not reach validator or WBToken.api_key."""
    session = MagicMock(name="cabinet_api_strip_session")
    session.commit = AsyncMock()
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    raw_token = "q" * 32
    wb_cabinet = SimpleNamespace(id=100, active=True)
    wb_user_cabinet = SimpleNamespace(id=500)
    user_id_loader = AsyncMock(return_value=1)
    existing_token_loader = AsyncMock(return_value=None)
    load_wb_cabinet = AsyncMock(return_value=wb_cabinet)
    ensure_binding = AsyncMock(return_value=wb_user_cabinet)
    adv_loader = AsyncMock(return_value=[])
    shop_id = "shop-strip-cabinet"
    validation_result = SimpleNamespace(
        is_valid_jwt=True,
        is_personal=True,
        is_read_only=False,
        is_expired=False,
        can_be_used_for_free=True,
        missing_required=set(),
        shop_id=shop_id,
    )
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=validation_result)
    persist_token = AsyncMock()

    message = SimpleNamespace(
        text=f"  {raw_token}  ",
        chat=SimpleNamespace(id=707),
        from_user=SimpleNamespace(id=808),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"cabinet_name": "Cabinet"})
    client_session = MagicMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_user_id_in_session", user_id_loader),
        patch.object(
            start_module,
            "_load_existing_wb_token_in_session",
            existing_token_loader,
        ),
        patch.object(start_module, "persist_wb_token_in_session", persist_token),
        patch.object(
            start_module,
            "_load_wb_cabinet_by_shop_id_in_session",
            load_wb_cabinet,
        ),
        patch.object(
            start_module,
            "_load_user_cabinet_for_user_in_session",
            AsyncMock(return_value=None),
        ),
        patch.object(
            start_module,
            "ensure_wb_user_cabinet_binding_in_session",
            ensure_binding,
        ),
        patch.object(
            start_module,
            "_load_adv_settings_for_wb_user_cabinet_in_session",
            adv_loader,
        ),
        patch.object(
            start_module,
            "TokenPermissionsValidator",
            MagicMock(return_value=validator),
        ),
        patch.object(
            start_module.messages,
            "ShopUpdateInfo",
            MagicMock(return_value=AsyncMock()),
        ),
        patch.object(
            start_module.messages,
            "AdvCompanyChoicing",
            MagicMock(return_value=AsyncMock()),
        ),
    ):
        await start_module.process_cabinet_api(message, bot, state, client_session)

    validator.validate.assert_awaited_once_with(raw_token, mode="claims_only")
    existing_token_loader.assert_awaited_once_with(session, raw_token, shop_id)
    saved_token = persist_token.await_args.args[1]
    assert saved_token.api_key == raw_token


async def test_token_acceptable_for_persist_allows_any_scopes() -> None:
    """Persist gate must not reject tokens with partial scopes or read-only."""
    validation_result = SimpleNamespace(
        is_valid_jwt=True,
        is_expired=False,
        shop_id="shop-partial",
    )
    assert start_module._token_acceptable_for_persist(validation_result) is None


async def test_token_acceptable_for_persist_rejects_expired() -> None:
    validation_result = SimpleNamespace(
        is_valid_jwt=True,
        is_expired=True,
        shop_id="shop-expired",
    )
    rejection = start_module._token_acceptable_for_persist(validation_result)
    assert rejection is not None
    assert "истёк" in rejection.lower()


@pytest.mark.asyncio
async def test_process_cabinet_api_accepts_token_without_full_scopes() -> None:
    """Registration must persist tokens even when required WB scopes are missing."""
    session = MagicMock(name="cabinet_api_partial_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    user_id_loader = AsyncMock(return_value=1)
    existing_token_loader = AsyncMock(return_value=None)
    persist_token = AsyncMock()
    shop_id = "shop-partial"
    validation_result = SimpleNamespace(
        is_valid_jwt=True,
        is_read_only=True,
        is_expired=False,
        shop_id=shop_id,
    )
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=validation_result)

    message = SimpleNamespace(
        text="p" * 32,
        chat=SimpleNamespace(id=909),
        from_user=SimpleNamespace(id=1010),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"cabinet_name": "Cabinet"})
    client_session = MagicMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_user_id_in_session", user_id_loader),
        patch.object(
            start_module,
            "_load_existing_wb_token_in_session",
            existing_token_loader,
        ),
        patch.object(start_module, "persist_wb_token_in_session", persist_token),
        patch.object(
            start_module,
            "_load_wb_cabinet_by_shop_id_in_session",
            AsyncMock(return_value=None),
        ),
        patch.object(
            start_module,
            "create_wb_cabinet_and_user_binding_in_session",
            AsyncMock(
                return_value=(
                    SimpleNamespace(id=1, shop_id=shop_id),
                    SimpleNamespace(id=2, name="Cab"),
                )
            ),
        ),
        patch.object(
            start_module,
            "_load_user_cabinets_for_user_in_session",
            AsyncMock(return_value=[]),
        ),
        patch.object(
            start_module,
            "TokenPermissionsValidator",
            MagicMock(return_value=validator),
        ),
        patch.object(
            start_module.messages,
            "ShopUpdateInfo",
            MagicMock(return_value=AsyncMock()),
        ),
        patch.object(
            start_module.messages,
            "ShopAddedSuccess",
            MagicMock(return_value=AsyncMock()),
        ),
        patch.object(start_module, "ShopChoice", MagicMock(return_value=AsyncMock())),
        patch.object(
            start_module,
            "get_shop_ids_with_complete_token_status",
            AsyncMock(return_value=set()),
        ),
    ):
        await start_module.process_cabinet_api(message, bot, state, client_session)

    persist_token.assert_awaited_once()
