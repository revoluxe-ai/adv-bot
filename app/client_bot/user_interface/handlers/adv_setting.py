import logging
import aiogram
from aiogram import Bot, F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import Result, update
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.modules import balance_manager
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.modules.shop_menu.message import ShopMenu
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.client_bot.modules.default_settings import apply_defaults_to_adv_setting

from .. import states
from ..views import callbacks, messages

sm = get_async_session_maker

router = Router()


logger = logging.getLogger(__name__)

pricer = Pricer()


@router.callback_query(callbacks.ChoiceAdvPaginator.filter(F.reset_filter))
async def reset_filter(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.update_data(filter_advs=[])

    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        adv_settings = list(result.scalars().all())

    page = 1
    message = callback.message
    assert message
    await messages.AdvCompanyChoicing(
        bot,
        message.chat.id,
        wb_user_cabinet_original_id,
        adv_settings,
        state,
        page=page,
    )()

    return


@router.message(StateFilter(states.AdvCompanyCatalog.waiting_for_keywords_for_filter))
async def waiting_for_keywords_for_filter(
    message: types.Message, bot: Bot, state: FSMContext
):
    chat_id = message.chat.id
    if not (text := message.text):
        await message.answer('Не получен список ключей')
        return None
    filter_advs: list[str] = text.splitlines()
    filter_advs = [keyword.strip().lower() for keyword in filter_advs if keyword]
    await state.update_data(filter_advs=filter_advs)
    state_data = await state.get_data()
    wb_user_cabinet_original_id: int = state_data["last_wb_user_cabinet_original_id"]
    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = list(result.scalars().all())

    page = 1
    check_data = await state.get_data()
    logger.debug("check_data: %s", check_data)
    await messages.AdvCompanyChoicing(
        bot, chat_id, wb_user_cabinet_original_id, adv_settings, state, page=page
    )()
    return


@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def choice_adv_paginator(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
):
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id: int = callback.message.chat.id
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(
        state=states.AdvCompanyCatalog.waiting_for_keywords_for_filter
    )
    page = callback_data.page
    check_data = await state.get_data()
    logger.debug("check_data: %s", check_data)
    stmt = (
        select(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .join(WBCabinet.wb_user_cabinets)
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    async with sm() as session:
        result = await session.execute(stmt)
        adv_settings = list(result.scalars().all())
    await messages.AdvCompanyChoicing(
        bot, chat_id, wb_user_cabinet_original_id, adv_settings, state, page=page
    )()
    return


@router.callback_query(callbacks.Adv.filter())
async def adv_handler(
    callback: types.CallbackQuery,
    callback_data: callbacks.Adv,
    bot: aiogram.Bot,
    state: FSMContext,
):
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id = callback.message.chat.id
    await state.set_state()
    await messages.LongTimeOperation(bot, callback.message.chat.id)()
    adv_original_id = callback_data.adv_original_id
    await state.update_data(last_adv_original_id=adv_original_id)
    data = await state.get_data()

    try:
        wb_user_cabinet_original_id = data["last_wb_user_cabinet_original_id"]
    except KeyError:
        async with sm() as session:
            stmt = (
                select(WBUserCabinet)
                .join(WBUserCabinet.user)
                .join(WBUserCabinet.wb_cabinet)
                .join(WBCabinet.adv_settings)
                .filter(
                    User.user_telegram_id
                    == callback.from_user.id,  # Фильтрация по user_telegram_id
                    AdvSetting.id
                    == adv_original_id,  # Фильтрация по нужному AdvSetting
                )
            )
            result = await session.execute(stmt)
            wb_user_cabinet = result.scalar()  # Извлекаем первую строку
        wb_user_cabinet_original_id: int = wb_user_cabinet.id

    async with sm() as session:
        adv = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv = adv.scalar()

    if not adv:
        await bot.send_message(
            chat_id, "Кампания не найдена, попробуйте еще раз"
        )
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            .order_by(AdvSetting.name)
        )
        async with sm() as session:
            result = await session.execute(stmt)
            adv_settings: list[AdvSetting] = list(result.scalars().all())

        await messages.AdvCompanyChoicing(
            bot,
            chat_id,
            wb_user_cabinet_original_id,
            adv_settings,
            state,
        )()
        return

    async with sm() as session:
        wb_user_cabinet = await session.execute(
            select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet = wb_user_cabinet.scalar()


    await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == "on"))
async def turn_adv_on(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: callbacks.TurnBot,
    bot: aiogram.Bot,
) -> None:
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id = callback.message.chat.id

    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    adv_original_id = callback_data.adv_original_id
    async with sm(read_only=False) as session:
        session.begin()
        stmt = (
            select(WBUserCabinet)
            .join(WBUserCabinet.wb_cabinet)
            .options(selectinload(WBUserCabinet.wb_cabinet))
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result_for_wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = result_for_wb_user_cabinet.scalar()
        assert wb_user_cabinet
        stmt = (
            select(AdvSetting)
            .options(selectinload(AdvSetting.payments))
            .where(AdvSetting.id == adv_original_id)
        )
        result_for_adv_setting = await session.execute(stmt)
        adv: AdvSetting = result_for_adv_setting .scalar_one()
        wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet  # type: ignore[attr-defined]
        tariff_for_month: int | float = await pricer.get_price_for_day_for_shop(
            session, wb_cabinet.shop_id
        )
        price_for_adv_for_day = pricer.get_tariff_for_day(int(tariff_for_month))
        balance, bonus = await balance_manager.get_cabinet_balance_and_bonuses(
            wb_cabinet.id
        )
        sum_balance = balance + bonus
        if not sum_balance >= price_for_adv_for_day:
            await bot.send_message(callback.message.chat.id, "Недостаточно средств")
            await ShopMenu(
                bot, callback.message.chat.id, state, wb_user_cabinet_original_id
            )()
            return
        await bot.send_message(callback.message.chat.id, "Включаю бота")
        adv.bot_active = True
        apply_defaults_to_adv_setting(adv)
        await session.commit()
        wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
        await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
        await state.update_data(adv_original_id=adv.id)
        wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
        stmt = select(WBUserCabinet).where(
            WBUserCabinet.id == wb_user_cabinet_original_id
        )
        result: Result[tuple[WBUserCabinet]] = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = result.scalar_one()
        await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == "on_all"))
async def turn_adv_on_all(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: callbacks.TurnBot,
    bot: aiogram.Bot,
):
    if callback.message is None:
        raise ValueError('Нет сообщения')

    chat_id = callback.message.chat.id
    await bot.send_message(callback.message.chat.id, "Включаю бота для всех кампаний (с дефолтами)")
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm(read_only=False) as session:
        # Получаем все кампании магазина через ORM
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()
        
        # Применяем дефолты через ORM для каждой кампании
        updated_count = 0
        for adv_setting in adv_settings:
            adv_setting.bot_active = True
            apply_defaults_to_adv_setting(adv_setting)
            updated_count += 1
        
        await session.commit()

    await bot.send_message(
        chat_id,
        f"Бот включен для {updated_count} кампаний, дефолтные настройки применены.",
    )

    chat_id = callback.message.chat.id
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == "off_all"))
async def turn_adv_off_all(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: callbacks.TurnBot,
    bot: aiogram.Bot,
):
    if callback.message is None:
        raise ValueError('Нет сообщения')

    chat_id = callback.message.chat.id

    await bot.send_message(callback.message.chat.id, "Отключаю бота от всех кампаний")
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm(read_only=False) as session:
        advs = await session.execute(
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        advs = advs.scalars().all()
        for adv_ in advs:
            adv_.bot_active = False
        await session.commit()
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return


@router.callback_query(callbacks.TurnBot.filter(F.action == "off"))
async def turn_adv_off(
    call: types.CallbackQuery, callback_data: callbacks.TurnBot, bot: aiogram.Bot
):
    if call.message is None:
        raise ValueError('Нет сообщения')

    chat_id = call.message.chat.id

    # data = await state.get_data()
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = (
            select(WBUserCabinet)
            .join(WBUserCabinet.wb_cabinet)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet = wb_user_cabinet.scalar()

    async with sm(read_only=False) as session:
        result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == callback_data.adv_original_id)
        )
        adv_setting: AdvSetting = result.scalar_one()
        adv_setting.bot_active = False
        await session.commit()

    await messages.AdvSettingMenu(
        bot,
        chat_id,
        wb_user_cabinet,
        adv_setting,
    )()


@router.callback_query(
    callbacks.ChangeAutoMinCTR.filter(F.action == "turn_on_auto_min_ctr")
)
async def turn_on_auto_min_ctr(
    callback: types.CallbackQuery, bot: Bot, callback_data: callbacks.ChangeAutoMinCTR
):
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id = callback.message.chat.id

    adv_setting_original_id = callback_data.adv_setting_original_id
    stmt = (
        update(AdvSetting)
        .where(AdvSetting.id == callback_data.adv_setting_original_id)
        .values({AdvSetting.new_auto_min_ctr_mode: True})
    )

    async with sm(read_only=False) as session:
        await session.execute(stmt)
        await session.commit()
    await messages.SettingMinCTR(bot, chat_id)(adv_setting_original_id)


@router.callback_query(callbacks.ApplyCampaignDefaults.filter())
async def apply_campaign_defaults(
    callback: types.CallbackQuery,
    callback_data: callbacks.ApplyCampaignDefaults,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id = callback.message.chat.id

    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv_setting: AdvSetting = result.scalar_one()

        # Применяем дефолты через ORM
        apply_defaults_to_adv_setting(adv_setting)
        await session.commit()

        await bot.send_message(
            chat_id, "Дефолтные настройки применены успешно!"
        )

        # Обновить меню кампании
        data = await state.get_data()
        wb_user_cabinet_original_id: int = data["last_wb_user_cabinet_original_id"]
        async with sm() as session_read:
            wb_user_cabinet = await session_read.execute(
                select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
            )
            wb_user_cabinet = wb_user_cabinet.scalar()

        await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()

    return


@router.callback_query(callbacks.ApplyDefaultsForShop.filter())
async def apply_defaults_for_shop(
    callback: types.CallbackQuery,
    callback_data: callbacks.ApplyDefaultsForShop,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    if callback.message is None:
        raise ValueError('Нет сообщения')
    chat_id: int = callback.message.chat.id

    async with sm(read_only=False) as session:
        # Получаем только активные кампании магазина через ORM
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            .where(AdvSetting.bot_active.is_(True))
        )
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()
        
        # Применяем дефолты через ORM для каждой активной кампании
        updated_count = 0
        for adv_setting in adv_settings:
            apply_defaults_to_adv_setting(adv_setting)
            updated_count += 1
        
        await session.commit()

    await bot.send_message(
        chat_id,
        f"Дефолтные настройки применены к {updated_count} активным кампаниям магазина.",
    )

    # Вернуть пользователя в меню магазина
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()

    return
