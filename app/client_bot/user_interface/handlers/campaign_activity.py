import logging

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

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


def _limit_attr_name(campaign_type: AdvType) -> str:
    if campaign_type == AdvType.SEARCH:
        return "search_auto_budget_daily_limit"
    elif campaign_type == AdvType.AUTO:
        return "auto_budget_daily_limit"
    else:
        raise ValueError("Invalid campaign type")


def _get_limit_value(adv_setting: AdvSetting, campaign_type: AdvType) -> int:
    value = getattr(adv_setting, _limit_attr_name(campaign_type))
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
    if callback.message is None:
        raise ValueError("Нет сообщения")
    adv_setting = await _load_adv_setting(callback_data.adv_setting_original_id)
    await messages.CampaignActivityMenu(
        callback.bot, callback.message.chat.id, adv_setting
    )()


@router.callback_query(callbacks.ManageCampaignActivity.filter(F.action == "open"))
async def open_activity_target(
    callback: types.CallbackQuery,
    callback_data: callbacks.ManageCampaignActivity,
):
    if callback.message is None:
        raise ValueError("Нет сообщения")
    if not callback_data.campaign_type:
        return
    adv_setting = await _load_adv_setting(callback_data.adv_setting_original_id)
    current_limit = _get_limit_value(adv_setting, callback_data.campaign_type)
    await messages.CampaignActivityTargetMenu(
        callback.bot,
        callback.message.chat.id,
        adv_setting,
        callback_data.campaign_type,
        current_limit,
    )()


@router.callback_query(callbacks.ManageCampaignActivity.filter(F.action == "change"))
async def start_limit_change(
    callback: types.CallbackQuery,
    callback_data: callbacks.ManageCampaignActivity,
    state: FSMContext,
):
    if callback.message is None:
        raise ValueError("Нет сообщения")

    await state.update_data(
        adv_setting_id=callback_data.adv_setting_original_id,
        campaign_type=callback_data.campaign_type,
    )
    await state.set_state(states.CampaignActivity.waiting_for_new_limit)
    await messages.CampaignActivityChangeLimit(
        callback.bot, callback.message.chat.id, callback_data.campaign_type
    )()


@router.callback_query(callbacks.ManageCampaignActivity.filter(F.action == "turn_off"))
async def turn_off_limit(
    callback: types.CallbackQuery,
    callback_data: callbacks.ManageCampaignActivity,
):
    if callback.message is None:
        raise ValueError("Нет сообщения")
    if not callback_data.campaign_type:
        return
    async with sm(read_only=False) as session:
        adv_setting = await session.get(
            AdvSetting, callback_data.adv_setting_original_id
        )
        if not adv_setting:
            raise ValueError("AdvSetting not found")
        setattr(adv_setting, _limit_attr_name(callback_data.campaign_type), 0)
        await session.commit()
        await messages.CampaignActivityTargetMenu(
            callback.bot,
            callback.message.chat.id,
            adv_setting,
            callback_data.campaign_type,
            0,
        )()


@router.message(StateFilter(states.CampaignActivity.waiting_for_new_limit))
async def set_new_limit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    adv_setting_id = data.get("adv_setting_id")
    campaign_type_value = data.get("campaign_type")
    if not adv_setting_id or not campaign_type_value:
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")
        await state.clear()
        return


    campaign_type = AdvType(campaign_type_value)

    try:
        limit = int(message.text.replace(",", ".").strip())
    except (ValueError, AttributeError):
        limit = 0

    if limit <= 0:
        await messages.CampaignActivityChangeLimit(
            message.bot, message.chat.id, campaign_type
        )()
        return

    async with sm(read_only=False) as session:
        adv_setting = await session.get(AdvSetting, adv_setting_id)
        if not adv_setting:
            await message.answer("РК не найдена.")
            await state.clear()
            return
        setattr(adv_setting, _limit_attr_name(campaign_type), limit)
        await session.commit()
        await state.clear()
        await messages.CampaignActivityTargetMenu(
            message.bot,
            message.chat.id,
            adv_setting,
            campaign_type,
            limit,
        )()
