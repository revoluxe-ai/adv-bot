"""Хендлеры меню «Управление активностью РК»: лимиты расхода бюджета.

Меню редактирует два вида лимитов на ``AdvSetting``:

- ``daily`` — суточный лимит расхода (руб/сутки, календарный день MSK);
- ``total`` — абсолютный (lifetime) лимит суммарного расхода за всё время.

Оба вида подчиняются одному флагу ``use_common_budget``: при включённом общем
бюджете действует один лимит на обе РК, иначе — свой лимит у Авто и Аукциона.
Применяет лимиты shop-runner (``AutoAdvActiveControlService`` — пауза,
``AutoBudgetService`` — блокировка автопополнений).
"""
import logging

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from app.client_bot.user_interface.services.total_spend_snapshot import (
    load_total_spend_snapshot,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.shared.domains.wb.enums import (
    AdvType,
)
from app.utils.db.session_maker import get_async_session_maker

from .. import states
from ..views import callbacks, messages

logger = logging.getLogger(__name__)

router = Router()
sm = get_async_session_maker

_DAILY_LIMIT_ATTRS: dict[AdvType | None, str] = {
    None: "common_budget_daily_limit",
    AdvType.SEARCH: "search_auto_budget_daily_limit",
    AdvType.AUTO: "auto_budget_daily_limit",
}

_TOTAL_LIMIT_ATTRS: dict[AdvType | None, str] = {
    None: "common_budget_total_limit",
    AdvType.SEARCH: "search_auto_budget_total_limit",
    AdvType.AUTO: "auto_budget_total_limit",
}


def _limit_attr_name(campaign_type: AdvType | None, scope: str) -> str:
    """Имя колонки ``AdvSetting`` по виду лимита и цели.

    Args:
        campaign_type: ``None`` — общий лимит на обе РК, иначе нога РК.
        scope: ``"daily"`` или ``"total"``.

    Raises:
        ValueError: неизвестный ``scope`` или ``campaign_type``.
    """
    if scope == "total":
        attrs = _TOTAL_LIMIT_ATTRS
    elif scope == "daily":
        attrs = _DAILY_LIMIT_ATTRS
    else:
        raise ValueError(f"Invalid limit scope: {scope}")
    try:
        return attrs[campaign_type]
    except KeyError:
        raise ValueError("Invalid campaign type") from None


def _get_limit_value(
    adv_setting: AdvSetting, campaign_type: AdvType | None, scope: str
) -> int:
    """Текущее значение лимита.

    Для суточного ``0`` — лимит выключен (пауза РК). Для абсолютного ``0`` —
    лимита нет (РК не ограничивается и не паузится по абсолютному расходу).
    """
    value = getattr(adv_setting, _limit_attr_name(campaign_type, scope), 0)
    return value or 0


async def _load_adv_setting(adv_setting_id: int) -> AdvSetting:
    async with sm() as session:
        adv_setting = await session.get(AdvSetting, adv_setting_id)
        if not adv_setting:
            raise ValueError(f"AdvSetting with id {adv_setting_id} not found")
        return adv_setting


@router.callback_query(callbacks.ManageCampaignActivity.filter(F.action == "menu"))
async def show_activity_menu(
    callback: types.CallbackQuery,
    callback_data: callbacks.ManageCampaignActivity,
):
    """Показать меню активности РК со сводкой суточных и абсолютных лимитов."""
    if callback.message is None:
        raise ValueError("Нет сообщения")
    adv_setting = await _load_adv_setting(callback_data.adv_setting_original_id)
    total_spend = await load_total_spend_snapshot(adv_setting)
    await messages.CampaignActivityMenu(
        callback.bot, callback.message.chat.id, adv_setting, total_spend=total_spend
    )()


@router.callback_query(callbacks.ManageCampaignActivity.filter(F.action == "open"))
async def open_activity_target(
    callback: types.CallbackQuery,
    callback_data: callbacks.ManageCampaignActivity,
):
    """Экран конкретного лимита (вид лимита — в ``callback_data.scope``)."""
    if callback.message is None:
        raise ValueError("Нет сообщения")
    adv_setting = await _load_adv_setting(callback_data.adv_setting_original_id)
    campaign_type = callback_data.campaign_type
    scope = callback_data.scope
    current_limit = _get_limit_value(adv_setting, campaign_type, scope)
    total_spend = await load_total_spend_snapshot(adv_setting)
    await messages.CampaignActivityTargetMenu(
        callback.bot,
        callback.message.chat.id,
        adv_setting,
        campaign_type,
        current_limit,
        scope,
        total_spend=total_spend,
    )()


@router.callback_query(callbacks.ManageCampaignActivity.filter(F.action == "change"))
async def start_limit_change(
    callback: types.CallbackQuery,
    callback_data: callbacks.ManageCampaignActivity,
    state: FSMContext,
):
    """Запросить новое значение лимита и перейти в соответствующее состояние."""
    if callback.message is None:
        raise ValueError("Нет сообщения")

    scope = callback_data.scope
    await state.update_data(
        adv_setting_id=callback_data.adv_setting_original_id,
        campaign_type=callback_data.campaign_type,
        scope=scope,
    )
    await state.set_state(
        states.CampaignActivity.waiting_for_new_total_limit
        if scope == "total"
        else states.CampaignActivity.waiting_for_new_limit
    )
    total_spend = None
    if scope == "total":
        adv_setting = await _load_adv_setting(callback_data.adv_setting_original_id)
        total_spend = await load_total_spend_snapshot(adv_setting)
    await messages.CampaignActivityChangeLimit(
        callback.bot,
        callback.message.chat.id,
        callback_data.campaign_type,
        scope,
        total_spend=total_spend,
    )()


@router.callback_query(callbacks.ManageCampaignActivity.filter(F.action == "turn_off"))
async def turn_off_limit(
    callback: types.CallbackQuery,
    callback_data: callbacks.ManageCampaignActivity,
):
    """Записать ``0`` в выбранный лимит и вернуть экран лимита.

    Суточный ``0`` — выключить (пауза). Абсолютный ``0`` — убрать лимит
    (ограничения по абсолютному расходу нет).
    """
    if callback.message is None:
        raise ValueError("Нет сообщения")
    campaign_type = callback_data.campaign_type
    scope = callback_data.scope
    async with sm(read_only=False) as session:
        adv_setting = await session.get(
            AdvSetting, callback_data.adv_setting_original_id
        )
        if not adv_setting:
            raise ValueError("AdvSetting not found")
        setattr(adv_setting, _limit_attr_name(campaign_type, scope), 0)
        await session.commit()
        total_spend = await load_total_spend_snapshot(adv_setting)
        await messages.CampaignActivityTargetMenu(
            callback.bot,
            callback.message.chat.id,
            adv_setting,
            campaign_type,
            0,
            scope,
            total_spend=total_spend,
        )()


@router.message(
    StateFilter(
        states.CampaignActivity.waiting_for_new_limit,
        states.CampaignActivity.waiting_for_new_total_limit,
    )
)
async def set_new_limit(message: types.Message, state: FSMContext):
    """Сохранить введённый лимит; вид лимита берётся из данных FSM."""
    data = await state.get_data()
    adv_setting_id = data.get("adv_setting_id")
    campaign_type_value = data.get("campaign_type")
    scope = data.get("scope") or "daily"
    if adv_setting_id is None:
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")
        await state.clear()
        return

    campaign_type: AdvType | None = (
        AdvType(campaign_type_value) if campaign_type_value is not None else None
    )

    try:
        limit = int(message.text.replace(",", ".").strip())
    except (ValueError, AttributeError):
        limit = 0

    if limit <= 0:
        total_spend = None
        if scope == "total":
            adv_for_spend = await _load_adv_setting(adv_setting_id)
            total_spend = await load_total_spend_snapshot(adv_for_spend)
        await messages.CampaignActivityChangeLimit(
            message.bot,
            message.chat.id,
            campaign_type,
            scope,
            total_spend=total_spend,
        )()
        return

    async with sm(read_only=False) as session:
        adv_setting = await session.get(AdvSetting, adv_setting_id)
        if not adv_setting:
            await message.answer("РК не найдена.")
            await state.clear()
            return
        setattr(adv_setting, _limit_attr_name(campaign_type, scope), limit)
        await session.commit()
        await state.clear()
        total_spend = await load_total_spend_snapshot(adv_setting)
        await messages.CampaignActivityTargetMenu(
            message.bot,
            message.chat.id,
            adv_setting,
            campaign_type,
            limit,
            scope,
            total_spend=total_spend,
        )()
