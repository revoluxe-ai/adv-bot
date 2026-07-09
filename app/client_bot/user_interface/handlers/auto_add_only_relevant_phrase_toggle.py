from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select, update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.client_bot.user_interface.views.callbacks import (
    ChangeAutoAddOnlyRelevantPhraseStatus,
    ManageRelevantAndNonRelevantPhrases,
)
from app.client_bot.user_interface.views.messages.messages import (
    RelevantPhraseManagementMenuMessage,
)
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(ManageRelevantAndNonRelevantPhrases.filter())
async def open_relevant_phrase_management_menu(
    callback_query: CallbackQuery,
    callback_data: ManageRelevantAndNonRelevantPhrases,
    bot: Bot,
) -> None:
    adv_setting_id: int = callback_data.adv_setting_original_id

    async with sm(read_only=True) as session:
        stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
        adv: AdvSetting | None = (await session.execute(stmt)).scalar_one_or_none()

    if adv is None:
        if callback_query.message is not None:
            raise RuntimeError("РR не найдена")
        return

    assert callback_query.message is not None
    await RelevantPhraseManagementMenuMessage(
        bot,
        callback_query.message.chat.id,
        adv,
    )()


@router.callback_query(ChangeAutoAddOnlyRelevantPhraseStatus.filter())
async def toggle_auto_add_only_relevant_phrase(
    callback_query: CallbackQuery,
    callback_data: ChangeAutoAddOnlyRelevantPhraseStatus,
    bot: Bot,
) -> None:
    new_status: bool = callback_data.new_status
    adv_id: int = callback_data.adv_id

    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.adv_id == adv_id)
            .values({"auto_add_only_relevant_phrase": new_status})
        )
        await session.execute(stmt)
        await session.commit()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    status_str = (
        "Включено добавление только релевантных фраз"
        if new_status
        else "Выключено добавление только релевантных фраз"
    )

    await bot.send_message(chat_id, status_str)

    async with sm(read_only=True) as session:
        stmt = select(AdvSetting).where(AdvSetting.adv_id == adv_id)
        adv: AdvSetting | None = (await session.execute(stmt)).scalar_one_or_none()

    if adv is None:
        return

    assert callback_query.from_user
    await RelevantPhraseManagementMenuMessage(
        bot,
        chat_id,
        adv,
    )()
