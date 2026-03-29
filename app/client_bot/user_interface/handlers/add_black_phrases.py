from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot import const
from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.relevant_phrase_manager import RelevantPhraseManager
from app.modules.relevant_phrase_manager.not_relevante_template import NotRelevantTemplate
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


def _black_phrases_from_message(text: str) -> list[str]:
    return [line.strip() for line in text.split("\n") if line.strip()]


def _exit_test_keyboard(adv_setting_id: int) -> InlineKeyboardBuilder:
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
    text = message.text
    if not text:
        return None
    keywords = _black_phrases_from_message(text)
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    async with sm(read_only=True) as session:
        adv: AdvSetting | None = await session.get(AdvSetting, adv_setting_id)
    if adv is None:
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
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddBlackPhrasesTemplates.waiting_for_black_phrases_test)
    assert callback.from_user
    prompt = (
        "⛔ ЧЁРНЫЙ СПИСОК\n\n"
        "Отправьте список фраз для проверки — по одной строке. "
        "Бот отметит каждую как релевантную или нерелевантную (НРФ) "
        "по текущим сохранённым шаблонам черного списка."
    )
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=prompt,
        reply_markup=_exit_test_keyboard(adv_setting_id).as_markup(),
    )
    await callback.answer()


@router.callback_query(callbacks.ExitBlackPhrasesTest.filter())
async def exit_black_phrases_test(
    callback: CallbackQuery,
    bot: Bot,
    callback_data: callbacks.ExitBlackPhrasesTest,
    state: FSMContext,
) -> None:
    adv_setting_id = callback_data.adv_setting_id
    await state.update_data(last_adv_setting_id=adv_setting_id)
    await state.set_state(states.AddBlackPhrasesTemplates.waiting_for_black_phrases)
    assert callback.from_user
    await messages.WaitingForBlackPhrases(bot, callback.from_user.id)(adv_setting_id)
    await callback.answer()


@router.message(StateFilter(states.AddBlackPhrasesTemplates.waiting_for_black_phrases_test))
async def waiting_for_black_phrases_test(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    text = message.text
    if not text:
        return None
    data = await state.get_data()
    adv_setting_id = data["last_adv_setting_id"]
    async with sm(read_only=True) as session:
        adv: AdvSetting | None = await session.get(AdvSetting, adv_setting_id)
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

    header = "⛔ ЧЁРНЫЙ СПИСОК\n\nРезультат по текущим шаблонам:\n"
    body = "\n".join(lines_out)
    full = header + body
    assert message.from_user
    chat_id = message.from_user.id
    markup = _exit_test_keyboard(adv_setting_id).as_markup()
    limit = const.MAX_MESSAGE_LENGTH
    if len(full) <= limit:
        await bot.send_message(chat_id=chat_id, text=full, reply_markup=markup)
    else:
        for i in range(0, len(full), limit):
            chunk = full[i : i + limit]
            is_last = i + limit >= len(full)
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
    adv_setting_original_id = callback_data.adv_setting_id
    async with sm(read_only=True) as session:
        adv: AdvSetting | None = await session.get(AdvSetting, adv_setting_original_id)
        if not adv:
            raise
    manager = RelevantPhraseManager(adv)
    await manager.update_black_phrases([])
    await messages.WaitingForBlackPhrases(bot, callback.from_user.id)(
        callback_data.adv_setting_id
    )
