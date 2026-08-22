"""Telegram-хендлеры шаблонов чёрного списка (NRF) фраз.

Ordinary ``RelevantPhraseManager.update_black_phrases`` — Forbidden under
A/B Hold ``PENDING_SETUP`` / ``ACTIVE`` (``is_ab_hold_structural_freeze``).
Gate стоит до membership write в ``waiting_for_black_phrases`` и
``reset_black_phrases`` (peer: ``add_white_phrases`` / PBH-011).
Keyword-set / NRF-template change path — WARM_UP ``keyword_edit_open`` only.

PG seams: parent открывает ``sm(read_only=True)`` и передаёт session в
``load_adv_setting_in_session`` (PURE_READ для freeze-check / export).
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
from app.modules.relevant_phrase_manager.not_relevante_template import NotRelevantTemplate
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    is_ab_hold_structural_freeze,
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


def _black_phrases_from_message(text: str) -> list[str]:
    """Разбивает текст сообщения на непустые строки фраз."""
    return [line.strip() for line in text.split("\n") if line.strip()]


def _exit_test_keyboard(adv_setting_id: int) -> InlineKeyboardBuilder:
    """Клавиатура выхода из режима теста шаблонов чёрного списка."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Назад к шаблонам",
            callback_data=callbacks.ExitBlackPhrasesTest(
                adv_setting_id=adv_setting_id
            ).pack(),
        )
    )
    return builder


@router.callback_query(callbacks.AddBlackPhrasesTemplates.filter())
async def add_white_phrases(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.AddBlackPhrasesTemplates,
    state: FSMContext,
) -> None:
    """Открывает FSM ожидания строк шаблонов чёрного списка."""
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddBlackPhrasesTemplates.waiting_for_black_phrases)
    await messages.WaitingForBlackPhrases(
        bot,
        callback.from_user.id,
    )(adv_setting_id)


@router.message(StateFilter(states.AddBlackPhrasesTemplates.waiting_for_black_phrases))
async def waiting_for_black_phrases(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    """Сохраняет шаблоны чёрного списка; под A/B Hold structural freeze — отказ без write."""
    text = message.text
    if not text:
        return None
    keywords = _black_phrases_from_message(text)
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    async with sm(read_only=True) as session:
        adv = await load_adv_setting_in_session(session, adv_setting_id)
    if adv is None:
        return None
    if is_ab_hold_structural_freeze(adv.card_ab_hold_mode):
        await message.answer(AB_HOLD_ADD_PHRASES_BLOCKED_MSG)
        return None

    rel_manager = RelevantPhraseManager(adv)
    await rel_manager.update_black_phrases(keywords)
    assert message.from_user
    user_id = message.from_user.id
    await messages.WaitingForBlackPhrases(bot, user_id)(adv_setting_id)
    return None


@router.callback_query(callbacks.TestBlackPhrasesTemplates.filter())
async def test_black_phrases_start(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.TestBlackPhrasesTemplates,
    state: FSMContext,
) -> None:
    """Запускает FSM проверки фраз по текущим сохранённым шаблонам (read-only)."""
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddBlackPhrasesTemplates.waiting_for_black_phrases_test)
    assert callback.from_user
    prompt = (
        "Отправьте список фраз для проверки — по одной строке. "
        "Бот отметит каждую как релевантную или нерелевантную (НРФ) "
        "по текущим сохранённым шаблонам черного списка."
    )
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=prompt,
        reply_markup=_exit_test_keyboard(adv_setting_id).as_markup(),
    )


@router.callback_query(callbacks.ExitBlackPhrasesTest.filter())
async def exit_black_phrases_test(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.ExitBlackPhrasesTest,
    state: FSMContext,
) -> None:
    """Возвращает из теста шаблонов в экран ожидания строк чёрного списка."""
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddBlackPhrasesTemplates.waiting_for_black_phrases)
    assert callback.from_user
    await messages.WaitingForBlackPhrases(bot, callback.from_user.id)(adv_setting_id)


@router.message(StateFilter(states.AddBlackPhrasesTemplates.waiting_for_black_phrases_test))
async def waiting_for_black_phrases_test(
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
    rules = await rel_manager.get_relevant_template_data()
    templator = NotRelevantTemplate(rules)

    lines_out: list[str] = []
    for line in _black_phrases_from_message(text):
        rel = templator.is_relevant(line)
        mark = "релевантна" if rel else "НРФ"
        sym = "✓" if rel else "✗"
        lines_out.append(f"{sym} {mark}: {line}")

    if not lines_out:
        return None

    header = "Результат по текущим шаблонам:\n"
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


@router.callback_query(callbacks.ResetBlackPhrases.filter())
async def reset_black_phrases(
    callback: CallbackQuery, bot: Bot, callback_data: callbacks.ResetBlackPhrases
) -> None:
    """Сбрасывает шаблоны чёрного списка; под A/B Hold structural freeze — отказ без write."""
    adv_setting_original_id = callback_data.adv_setting_id
    async with sm(read_only=True) as session:
        adv = await load_adv_setting_in_session(session, adv_setting_original_id)
        if not adv:
            raise
    if is_ab_hold_structural_freeze(adv.card_ab_hold_mode):
        assert callback.from_user
        await bot.send_message(
            callback.from_user.id,
            AB_HOLD_RESET_PHRASES_BLOCKED_MSG,
        )
        return
    manager = RelevantPhraseManager(adv)
    await manager.update_black_phrases([])
    await messages.WaitingForBlackPhrases(bot, callback.from_user.id)(
        callback_data.adv_setting_id
    )


@router.callback_query(callbacks.ExportBlackPhrases.filter())
async def export_black_phrases(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.ExportBlackPhrases,
) -> None:
    """Выгружает текущие шаблоны чёрного списка в txt (read-only)."""
    adv_setting_id = callback_data.adv_setting_id
    async with sm(read_only=True) as session:
        adv = await load_adv_setting_in_session(session, adv_setting_id)
    if adv is None:
        if isinstance(callback.message, Message):
            await callback.message.answer("Кампания не найдена.")
        return

    rel_manager = RelevantPhraseManager(adv)
    phrases = await rel_manager.get_relevant_template_data() or []
    payload = phrases_to_txt_bytes(phrases)
    document = BufferedInputFile(payload, filename="black_phrases.txt")
    assert callback.from_user
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=document,
        caption="Выгрузка черного списка фраз",
    )
