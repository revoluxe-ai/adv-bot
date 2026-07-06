import logging

from aiogram import Bot, F, Router, types
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.utils.db.session_maker import get_async_session_maker

from ..views import callbacks, messages

sm = get_async_session_maker

router = Router()
logger = logging.getLogger(__name__)


async def _show_strategy_menu(bot: Bot, chat_id: int, adv_setting_original_id: int) -> None:
    async with sm(read_only=True) as session:
        adv_setting = await session.get(AdvSetting, adv_setting_original_id)
        if adv_setting is None:
            await bot.send_message(chat_id, "РК не найдена.")
            return
    await messages.StrategyMenuMessage(bot, chat_id, adv_setting)()


@router.callback_query(callbacks.StrategyMenu.filter(F.action == "open"))
async def open_strategy_menu(
    callback: types.CallbackQuery,
    callback_data: callbacks.StrategyMenu,
    bot: Bot,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    await _show_strategy_menu(bot, callback.message.chat.id, callback_data.adv_setting_original_id)


@router.callback_query(callbacks.StrategyMenu.filter(F.action == "toggle_auto"))
async def toggle_auto_strategy(
    callback: types.CallbackQuery,
    callback_data: callbacks.StrategyMenu,
    bot: Bot,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    adv_setting_original_id = callback_data.adv_setting_original_id

    async with sm(read_only=False) as session:
        adv_setting = await session.get(AdvSetting, adv_setting_original_id)
        if adv_setting is None:
            await bot.send_message(callback.message.chat.id, "РК не найдена.")
            return
        # None is treated as auto-enabled (True); only False is manual
        current_is_auto = adv_setting.auto_update_strategy is not False
        adv_setting.auto_update_strategy = not current_is_auto
        await session.commit()

    await _show_strategy_menu(bot, callback.message.chat.id, adv_setting_original_id)


@router.callback_query(callbacks.StrategyMenu.filter(F.action == "set_strategy"))
async def set_manual_strategy(
    callback: types.CallbackQuery,
    callback_data: callbacks.StrategyMenu,
    bot: Bot,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    adv_setting_original_id = callback_data.adv_setting_original_id
    strategy_value = callback_data.strategy

    if strategy_value is None:
        await bot.send_message(callback.message.chat.id, "Не передана стратегия.")
        return

    async with sm(read_only=False) as session:
        adv_setting = await session.get(AdvSetting, adv_setting_original_id)
        if adv_setting is None:
            await bot.send_message(callback.message.chat.id, "РК не найдена.")
            return

        # None means auto-enabled (same as True); only False is manual
        #TODO: Тут надо совместить текущую логику с дефолтом в CompexAdv
        auto_update_strategy = getattr(adv_setting, "auto_update_strategy", True) is not False
        if auto_update_strategy:
            await bot.send_message(
                callback.message.chat.id,
                "Сначала отключите авто-выбор стратегии, затем выберите стратегию вручную.",
            )
            return

        try:
            strategy = Strategy(strategy_value)
        except ValueError:
            await bot.send_message(callback.message.chat.id, "Передана неизвестная стратегия.")
            return

        # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
        adv_setting.strategy = strategy
        await session.commit()

    await _show_strategy_menu(bot, callback.message.chat.id, adv_setting_original_id)


# TODO(legacy-remove): Устаревший flow strategy_setting работает через target_ctr_mode.
# После полной миграции интерфейса на StrategyMenu удалить legacy callbacks.StrategySetting.
@router.callback_query(callbacks.StrategySetting.filter(F.action == "turn_on_min_ctr"))
async def turn_on_min_ctr(
    callback: types.CallbackQuery,
    bot: Bot,
    callback_data: callbacks.StrategySetting,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        adv_setting = await session.scalar(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        if adv_setting is None:
            await bot.send_message(callback.message.chat.id, "РК не найдена.")
            return
        adv_setting.target_ctr_mode = False
        await session.commit()

    await bot.send_message(
        callback.message.chat.id,
        "Legacy-настройка target_ctr_mode обновлена. Используйте новый экран «Стратегия РК».",
    )


# TODO(legacy-remove): Удалить вместе с legacy callbacks.StrategySetting.
@router.callback_query(callbacks.StrategySetting.filter(F.action == "on_target_ctr"))
async def on_target_ctr(
    callback: types.CallbackQuery,
    bot: Bot,
    callback_data: callbacks.StrategySetting,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        adv_setting = await session.scalar(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        if adv_setting is None:
            await bot.send_message(callback.message.chat.id, "РК не найдена.")
            return
        adv_setting.target_ctr_mode = True
        await session.commit()

    await bot.send_message(
        callback.message.chat.id,
        "Legacy-настройка target_ctr_mode обновлена. Используйте новый экран «Стратегия РК».",
    )


# TODO(legacy-remove): Удалить вместе с legacy callbacks.StrategySetting.
@router.callback_query(callbacks.StrategySetting.filter(F.action == "turn_on_forward_mode"))
async def turn_on_forward_mode(
    callback: types.CallbackQuery,
    bot: Bot,
    callback_data: callbacks.StrategySetting,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        adv_setting = await session.scalar(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        if adv_setting is None:
            await bot.send_message(callback.message.chat.id, "РК не найдена.")
            return
        adv_setting.target_ctr_mode_strategy = "forward"
        await session.commit()

    await bot.send_message(
        callback.message.chat.id,
        "Legacy-настройка target_ctr_mode_strategy обновлена. Используйте новый экран «Стратегия РК».",
    )


# TODO(legacy-remove): Удалить вместе с legacy callbacks.StrategySetting.
@router.callback_query(callbacks.StrategySetting.filter(F.action == "turn_on_keep_mode"))
async def turn_on_keep_mode(
    callback: types.CallbackQuery,
    bot: Bot,
    callback_data: callbacks.StrategySetting,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    adv_original_id = callback_data.adv_setting_original_id
    async with sm(read_only=False) as session:
        adv_setting = await session.scalar(select(AdvSetting).where(AdvSetting.id == adv_original_id))
        if adv_setting is None:
            await bot.send_message(callback.message.chat.id, "РК не найдена.")
            return
        adv_setting.target_ctr_mode_strategy = "keep"
        await session.commit()

    await bot.send_message(
        callback.message.chat.id,
        "Legacy-настройка target_ctr_mode_strategy обновлена. Используйте новый экран «Стратегия РК».",
    )


# TODO(legacy-remove): Удалить fallback-обработчик legacy callbacks.StrategySetting.
@router.callback_query(callbacks.StrategySetting.filter())
async def strategy_setting_legacy_fallback(
    callback: types.CallbackQuery,
    bot: Bot,
    callback_data: callbacks.StrategySetting,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    await bot.send_message(
        callback.message.chat.id,
        "Legacy-меню стратегии устарело. Используйте кнопку «Стратегия РК» в настройках кампании.",
    )
    await _show_strategy_menu(bot, callback.message.chat.id, callback_data.adv_setting_original_id)
