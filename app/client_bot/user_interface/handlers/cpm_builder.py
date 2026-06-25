"""Telegram handlers for CPM bidder settings flow."""

import io

import aiogram
from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.client_bot.user_interface.services.cpm_target_place_workbook import (
    TargetPlaceImportSummary,
    apply_target_place_workbook,
    build_target_place_workbook,
)
from app.client_bot.user_interface.utils import (
    get_auto_target_place_manual_change_locked_text,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.utils.db.session_maker import get_async_session_maker

from .. import states
from ..views import callbacks, messages
from . import start

sm = get_async_session_maker

router = Router()


async def _set_all_keywords_target_place(
    session: AsyncSession, adv_original_id: int, target_place: int
) -> None:
    """Synchronize campaign target place to all keywords of the campaign."""
    result = await session.execute(
        select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_original_id)
    )
    for keyword_setting in result.scalars():
        keyword_setting.target_place = target_place


def _format_target_place_import_summary(summary: TargetPlaceImportSummary) -> str:
    """Build compact user-facing import summary with first errors only."""
    lines = [
        "Готово. Импорт целевых позиций завершён.",
        "меняется только target_place.",
        "пустые ячейки бот пропустит.",
        f"Строк обработано: {summary.processed_rows}",
        f"Обновлено target_place: {summary.updated_rows}",
        f"Пропущено пустых target_place: {summary.skipped_empty_rows}",
        f"Не найдено: {summary.not_found_rows}",
        f"Ошибок валидации: {summary.validation_error_rows}",
    ]
    if summary.errors:
        lines.append("")
        lines.append("Первые ошибки:")
        lines.extend(summary.errors[:5])
    return "\n".join(lines)


async def _load_adv_setting(
    session: AsyncSession, adv_original_id: int
) -> AdvSetting | None:
    """Load campaign settings by id using the current session maker."""
    return await session.get(AdvSetting, adv_original_id)


@router.callback_query(
    callbacks.CPMSettingMenu.filter(F.action == "to_cpm_setting_page")  # noqa
)
async def to_page_for_cpm_setting(
    callback: types.CallbackQuery,
    callback_data: callbacks.CPMSettingMenu,
    bot: aiogram.Bot,
) -> None:
    """Open CPM settings page for the selected campaign."""
    if callback.message is None:
        return
    adv_original_id = callback_data.adv_original_id
    await messages.CPMSetting(bot, callback.message.chat.id)(adv_original_id)


@router.message(StateFilter(states.CPMSetting.waiting_for_min_position))
async def get_max_cpm(
    message: types.Message, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Persist target place and request max CPM only when it is still missing."""
    text = message.text or ""
    if "/start" in text:
        await state.set_state(state=None)
        await start.start_registration(message, bot, state)
        return
    if not text.isdigit():
        await message.answer("Введите целое положительное число")
        return
    min_position = int(text)
    if min_position < 1:
        await message.answer("Введите целое положительное число от 1 и выше")
        return

    state_data = await state.get_data()
    adv_original_id = state_data["last_adv_original_id"]
    async with sm(read_only=False) as session:
        adv = await _load_adv_setting(session, adv_original_id)
        if adv is None:
            await state.set_state(state=None)
            raise RuntimeError('Не удалось найти РК')
        if adv.auto_update_target_place:
            await state.set_state(state=None)
            await message.answer(get_auto_target_place_manual_change_locked_text())
            return
        adv.max_place = min_position
        has_max_cpm = adv.max_cpm is not None and adv.max_cpm > 0
        if has_max_cpm:
            adv.bidder_active = True
        await _set_all_keywords_target_place(session, adv_original_id, min_position)
        await session.commit()

    if has_max_cpm:
        await messages.CPMSetting(bot, message.chat.id)(adv_original_id)
        await state.set_state(state=None)
        return

    await state.update_data(min_position=min_position)
    await state.set_state(states.CPMSetting.waiting_for_max_cpm)
    await messages.AutoCPMSettingGetMaxCPM(bot, message.chat.id)()


@router.message(StateFilter(states.CPMSetting.waiting_for_max_cpm))
async def set_max_cpm(
    message: types.Message, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Persist max CPM and enable bidder, keeping any prior target place value."""
    data = await state.get_data()
    text = message.text or ""
    if "/start" in text:
        await state.set_state(state=None)
        await start.start_registration(message, bot, state)
        return
    if not text.isdigit():
        await message.answer("Введите целое положительное число")
        return
    max_cpm = int(text)
    if max_cpm < 1:
        await message.answer("Введите целое положительное число от 1 и выше")
        return

    adv_original_id = data["last_adv_original_id"]
    async with sm(read_only=False) as session:
        adv = await _load_adv_setting(session, adv_original_id)
        if adv is None:
            await state.set_state(state=None)
            raise RuntimeError('Не удалось найти РК')
        min_position = data.get("min_position")
        if min_position is not None:
            adv.max_place = min_position
        adv.max_cpm = max_cpm
        adv.bidder_active = True
        await session.commit()
        await messages.CPMSetting(bot, message.chat.id)(adv_original_id)
    await state.set_state(state=None)


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == "set_manual_cpm"))  # noqa
async def set_manual_cpm(
    callback: types.CallbackQuery,
    callback_data: callbacks.CPMSettingMenu,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Request manual max CPM value for the selected campaign."""
    if callback.message is None:
        return
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    await state.set_state(states.CPMSetting.waiting_for_manual_cpm)
    await messages.ManualCPMSetting(bot, callback.message.chat.id)()


@router.message(StateFilter(states.CPMSetting.waiting_for_manual_cpm))
async def set_manual_cpm_message(
    message: types.Message, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Save manual max CPM without touching bidder or bot activity flags."""
    text = message.text or ""
    if "/start" in text:
        await state.set_state(state=None)
        await start.start_registration(message, bot, state)
        return
    if not text.isdigit():
        await message.answer("Введите целое положительное число")
        return
    manual_cpm = int(text)
    if manual_cpm < 1:
        await message.answer("Введите целое положительное число от 1 и выше")
        return
    state_data = await state.get_data()
    adv_original_id = state_data["last_adv_original_id"]

    async with sm(read_only=False) as session:
        adv = await _load_adv_setting(session, adv_original_id)
        if adv is None:
            await state.set_state(state=None)
            raise RuntimeError("Не удалось найти кампанию для настройки.")

        adv.max_cpm = manual_cpm
        await session.commit()
    _ = await bot.send_message(message.chat.id, f"CPM успешно установлен ({manual_cpm}) р.")
    await messages.CPMSetting(bot, message.chat.id)(adv_original_id)
    await state.set_state(state=None)


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == "set_max_position"))  # noqa
async def set_max_position(
    callback: types.CallbackQuery,
    callback_data: callbacks.CPMSettingMenu,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Request a new shared target place for the selected campaign."""
    if callback.message is None:
        return
    adv_original_id = callback_data.adv_original_id
    async with sm(read_only=True) as session:
        adv = await _load_adv_setting(session, adv_original_id)

    if adv is None:
        await state.set_state(state=None)
        raise RuntimeError(
            "Не удалось найти кампанию для настройки.",
        )


    if adv.auto_update_target_place:
        await state.set_state(state=None)
        await bot.send_message(
            callback.message.chat.id,
            get_auto_target_place_manual_change_locked_text(),
        )
        return
    await state.update_data(last_adv_original_id=adv_original_id)
    await state.set_state(states.CPMSetting.waiting_for_max_position)
    await messages.AutoCPMSettingGetMinPosition(bot, callback.message.chat.id)(
        adv_original_id
    )


@router.message(StateFilter(states.CPMSetting.waiting_for_max_position))
async def set_max_position_message(
    message: types.Message, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Save shared target place and propagate it to all campaign keywords."""
    text = message.text or ""
    if "/start" in text:
        await state.set_state(state=None)
        await start.start_registration(message, bot, state)
        return
    if not text.isdigit():
        await message.answer("Введите целое положительное число")
        return
    max_position = int(text)
    if max_position < 1:
        await message.answer("Введите целое положительное число от 1 и выше")
        return
    state_data = await state.get_data()
    adv_original_id = state_data["last_adv_original_id"]
    async with sm(read_only=False) as session:
        adv = await _load_adv_setting(session, adv_original_id)
        if adv is None:
            await state.set_state(state=None)
            raise RuntimeError("Не удалось найти кампанию для настройки.")

        if adv.auto_update_target_place:
            await state.set_state(state=None)
            await message.answer(get_auto_target_place_manual_change_locked_text())
            return
        adv.max_place = max_position
        await _set_all_keywords_target_place(session, adv_original_id, max_position)
        await session.commit()
        await messages.CPMSetting(bot, message.chat.id)(adv_original_id)
    await state.set_state(state=None)


@router.callback_query(
    callbacks.CPMSettingMenu.filter(F.action == "download_target_places_template")
)
async def download_target_places_template(
    callback: types.CallbackQuery,
    callback_data: callbacks.CPMSettingMenu,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Export xlsx template with editable target places for campaign keywords."""
    if callback.message is None:
        return
    adv_original_id = callback_data.adv_original_id
    async with sm(read_only=True) as session:
        adv = await _load_adv_setting(session, adv_original_id)
    if adv is None:
        await state.set_state(state=None)
        raise RuntimeError(
            "Не удалось найти кампанию для настройки.",
        )
    if adv.auto_update_target_place:
        await state.set_state(state=None)
        await bot.send_message(
            callback.message.chat.id,
            get_auto_target_place_manual_change_locked_text(),
        )
        return
    payload = await build_target_place_workbook(adv_original_id)
    await state.update_data(last_adv_original_id=adv_original_id)
    await bot.send_document(
        chat_id=callback.message.chat.id,
        document=BufferedInputFile(
            payload, filename=f"campaign_{adv_original_id}_target_places.xlsx"
        ),
        caption=(
            "Excel для целевых позиций по текущей РК.\n"
            "Скачайте Excel, заполните только целевые позиции, которые хотите изменить, "
            "и загрузите файл обратно.\n"
            "пустые ячейки бот пропустит.\n"
            "меняется только target_place."
        ),
    )


@router.callback_query(
    callbacks.CPMSettingMenu.filter(F.action == "upload_target_places_template")
)
async def upload_target_places_template_start(
    callback: types.CallbackQuery,
    callback_data: callbacks.CPMSettingMenu,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Switch FSM to workbook upload mode for campaign target places."""
    if callback.message is None:
        return
    adv_original_id = callback_data.adv_original_id
    async with sm(read_only=True) as session:
        adv = await _load_adv_setting(session, adv_original_id)
    if adv is None:
        await state.set_state(state=None)
        raise RuntimeError('Не удалось найти РК')

    if adv.auto_update_target_place:
        await state.set_state(state=None)
        await bot.send_message(
            callback.message.chat.id,
            get_auto_target_place_manual_change_locked_text(),
        )
        return
    await state.update_data(last_adv_original_id=adv_original_id)
    await state.set_state(states.CPMSetting.waiting_for_target_place_workbook)
    await bot.send_message(
        callback.message.chat.id,
        "Пришлите файл .xlsx с целевыми позициями.\n"
        "Скачайте Excel, заполните только целевые позиции, которые хотите изменить, "
        "и загрузите файл обратно.\n"
        "пустые ячейки бот пропустит.\n"
        "меняется только target_place.",
    )


@router.message(
    StateFilter(states.CPMSetting.waiting_for_target_place_workbook),
    F.document,
)
async def upload_target_places_template_file(
    message: types.Message, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Apply uploaded workbook to keyword target places of the current campaign."""
    if message.document is None:
        return
    file_name = message.document.file_name or ""
    if file_name and not file_name.lower().endswith(".xlsx"):
        await message.answer("Нужен файл в формате .xlsx")
        return

    state_data = await state.get_data()
    adv_original_id = state_data.get("last_adv_original_id")
    if adv_original_id is None:
        await state.clear()
        await message.answer(
            "Сессия истекла. Откройте управление ставкой и снова нажмите загрузку файла."
        )
        return
    async with sm(read_only=True) as session:
        adv = await _load_adv_setting(session, int(adv_original_id))
    if adv is None:
        await state.set_state(state=None)
        raise RuntimeError("Не удалось найти кампанию для настройки.")


    if adv.auto_update_target_place:
        await state.set_state(state=None)
        await message.answer(get_auto_target_place_manual_change_locked_text())
        return

    await message.answer("Файл получен, начинаю обработку целевых позиций…")
    payload = io.BytesIO()
    await bot.download(message.document, payload)
    try:
        summary = await apply_target_place_workbook(adv_original_id, payload.getvalue())
    except ValueError as exc:
        await message.answer(f"Не удалось обработать файл: {exc}")
        return

    await message.answer(_format_target_place_import_summary(summary))
    await messages.CPMSetting(bot, message.chat.id)(adv_original_id)
    await state.set_state(state=None)
