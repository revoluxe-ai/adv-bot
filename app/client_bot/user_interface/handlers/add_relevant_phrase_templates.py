"""Telegram-хендлеры шаблонов релевантных фраз.

Ordinary ``dm_update_relevant_phrases_templates`` /
``dm_reset_relevant_phrases_templates`` — Forbidden under A/B Hold
``PENDING_SETUP`` / ``ACTIVE`` (``is_ab_hold_structural_freeze``).
Gate стоит до membership write в ``waiting_for_relevant_phrase_templates`` и
``reset_relevant_phrase_templates`` (peer: ``add_black_phrases`` / PBH-012,
``add_white_phrases`` / PBH-011). Keyword-set / template change path —
WARM_UP ``keyword_edit_open`` only.

PG seams: parent открывает ``sm(read_only=True)`` и передаёт session в
``load_adv_setting_in_session`` (PURE_READ для freeze-check / preview / export).
"""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import const
from app.client_bot.telegram_message_split import split_telegram_plain_text
from app.client_bot.user_interface import states
from app.client_bot.user_interface.utils.phrases_txt import phrases_to_txt_bytes
from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.relevant_phrase_manager import RelevantPhraseManager
from app.modules.relevant_phrase_manager.relevant_phrase_template import (
    RelevantPhraseTemplate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    is_ab_hold_structural_freeze,
)
from app.modules.wb_adv_updater.data_manager import (
    reset_relevant_phrases_templates as dm_reset_relevant_phrases_templates,
)
from app.modules.wb_adv_updater.data_manager import (
    update_relevant_phrases_templates as dm_update_relevant_phrases_templates,
)
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()

AB_HOLD_ADD_PHRASES_BLOCKED_MSG = (
    "Кампания в режиме A/B Hold — добавление фраз запрещено. "
    "Чтобы изменить состав фраз, выключите A/B Hold на экране режима."
)

AB_HOLD_RESET_PHRASES_BLOCKED_MSG = (
    "Кампания в режиме A/B Hold — статус ключей заморожен. "
    "Чтобы сбросить список, выключите A/B Hold на экране режима."
)


async def load_adv_setting_in_session(
    session: AsyncSession,
    adv_setting_id: int,
) -> AdvSetting | None:
    """PURE_READ: загрузить AdvSetting по PK для freeze-gate / preview / export.

    Args:
        session: injectable async session (caller: ``sm(read_only=True)``).
        adv_setting_id: PK ``AdvSetting.id``.

    Returns:
        AdvSetting или ``None``, если кампания не найдена.
    """
    return await session.get(AdvSetting, adv_setting_id)


def _templates_from_message(text: str) -> list[str]:
    """Разбивает текст сообщения на непустые строки шаблонов."""
    return [line.strip() for line in text.split("\n") if line.strip()]


def _exit_test_keyboard(adv_setting_id: int) -> InlineKeyboardBuilder:
    """Клавиатура выхода из режима теста шаблонов релевантных фраз."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Назад к шаблонам",
            callback_data=callbacks.ExitRelevantPhraseTemplatesTest(
                adv_setting_id=adv_setting_id
            ).pack(),
        )
    )
    return builder


@router.callback_query(callbacks.AddRelevantPhraseTemplates.filter())
async def add_relevant_phrase_templates_start(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.AddRelevantPhraseTemplates,
    state: FSMContext,
) -> None:
    """Открывает FSM ожидания строк шаблонов релевантных фраз."""
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(
        states.AddRelevantPhraseTemplatesGroup.waiting_for_relevant_phrase_templates
    )
    assert callback.from_user
    await messages.WaitingForRelevantPhraseTemplates(
        bot,
        callback.from_user.id,
    )(adv_setting_id)


@router.message(
    StateFilter(
        states.AddRelevantPhraseTemplatesGroup.waiting_for_relevant_phrase_templates
    )
)
async def waiting_for_relevant_phrase_templates(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    """Сохраняет шаблоны релевантных фраз; под A/B Hold structural freeze — отказ без write."""
    text = message.text
    if not text:
        return None
    keywords = _templates_from_message(text)
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    async with sm(read_only=True) as session:
        adv = await load_adv_setting_in_session(session, adv_setting_id)
    if adv is None:
        return None
    if is_ab_hold_structural_freeze(adv.card_ab_hold_mode):
        await message.answer(AB_HOLD_ADD_PHRASES_BLOCKED_MSG)
        return None

    await dm_update_relevant_phrases_templates(adv_setting_id, keywords)
    assert message.from_user
    await messages.WaitingForRelevantPhraseTemplates(bot, message.from_user.id)(
        adv_setting_id
    )
    return None


@router.callback_query(callbacks.TestRelevantPhraseTemplates.filter())
async def test_relevant_phrase_templates_start(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.TestRelevantPhraseTemplates,
    state: FSMContext,
) -> None:
    """Запускает FSM проверки фраз по текущим сохранённым шаблонам (read-only)."""
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(
        states.AddRelevantPhraseTemplatesGroup.waiting_for_relevant_phrase_templates_test
    )
    assert callback.from_user
    prompt = (
        "Отправьте список фраз для проверки — по одной строке. "
        "Бот отметит, подходит ли каждая под текущие сохранённые шаблоны "
        "релевантных фраз."
    )
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=prompt,
        reply_markup=_exit_test_keyboard(adv_setting_id).as_markup(),
    )


@router.callback_query(callbacks.ExitRelevantPhraseTemplatesTest.filter())
async def exit_relevant_phrase_templates_test(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.ExitRelevantPhraseTemplatesTest,
    state: FSMContext,
) -> None:
    """Возвращает из теста шаблонов в экран ожидания строк релевантных фраз."""
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(
        states.AddRelevantPhraseTemplatesGroup.waiting_for_relevant_phrase_templates
    )
    assert callback.from_user
    await messages.WaitingForRelevantPhraseTemplates(bot, callback.from_user.id)(
        adv_setting_id
    )


@router.message(
    StateFilter(
        states.AddRelevantPhraseTemplatesGroup.waiting_for_relevant_phrase_templates_test
    )
)
async def waiting_for_relevant_phrase_templates_test(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    """Проверяет фразы по шаблонам без записи membership (read-only preview)."""
    text = message.text
    if not text:
        return None
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    async with sm(read_only=True) as session:
        adv = await load_adv_setting_in_session(session, adv_setting_id)
    if adv is None:
        return None

    rel_manager = RelevantPhraseManager(adv)
    rules = await rel_manager.get_relevant_phrases_template_data()
    templator = RelevantPhraseTemplate(rules)

    lines_out: list[str] = []
    for line in _templates_from_message(text):
        matches = templator.matches(line)
        mark = "подходит под шаблон" if matches else "не подходит"
        sym = "✓" if matches else "✗"
        lines_out.append(f"{sym} {mark}: {line}")

    if not lines_out:
        return None

    header = "Результат по текущим шаблонам релевантных фраз:\n"
    body = "\n".join(lines_out)
    full = header + body
    assert message.from_user
    chat_id = message.from_user.id
    markup = _exit_test_keyboard(adv_setting_id).as_markup()
    chunks = split_telegram_plain_text(full, const.MAX_MESSAGE_LENGTH)
    for idx, chunk in enumerate(chunks):
        is_last = idx == len(chunks) - 1
        await bot.send_message(
            chat_id=chat_id,
            text=chunk,
            reply_markup=markup if is_last else None,
        )
    return None


@router.callback_query(callbacks.ResetRelevantPhraseTemplates.filter())
async def reset_relevant_phrase_templates(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.ResetRelevantPhraseTemplates,
) -> None:
    """Сбрасывает шаблоны релевантных фраз; под A/B Hold structural freeze — отказ без write."""
    adv_setting_original_id = callback_data.adv_setting_id
    async with sm(read_only=True) as session:
        adv = await load_adv_setting_in_session(session, adv_setting_original_id)
    if adv is None:
        if isinstance(callback.message, Message):
            await callback.message.answer("Кампания не найдена.")
        return
    if is_ab_hold_structural_freeze(adv.card_ab_hold_mode):
        assert callback.from_user
        await bot.send_message(
            callback.from_user.id,
            AB_HOLD_RESET_PHRASES_BLOCKED_MSG,
        )
        return
    await dm_reset_relevant_phrases_templates(adv_setting_original_id)
    assert callback.from_user
    await messages.WaitingForRelevantPhraseTemplates(bot, callback.from_user.id)(
        callback_data.adv_setting_id
    )


@router.callback_query(callbacks.ExportRelevantPhraseTemplates.filter())
async def export_relevant_phrase_templates(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.ExportRelevantPhraseTemplates,
) -> None:
    """Выгружает текущие шаблоны релевантных фраз в txt (read-only)."""
    adv_setting_id = callback_data.adv_setting_id
    async with sm(read_only=True) as session:
        adv = await load_adv_setting_in_session(session, adv_setting_id)
    if adv is None:
        if isinstance(callback.message, Message):
            await callback.message.answer("Кампания не найдена.")
        return

    rel_manager = RelevantPhraseManager(adv)
    phrases = await rel_manager.get_relevant_phrases_template_data() or []
    payload = phrases_to_txt_bytes(phrases)
    document = BufferedInputFile(payload, filename="relevant_phrase_templates.txt")
    assert callback.from_user
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=document,
        caption="Выгрузка шаблонов релевантных фраз",
    )
