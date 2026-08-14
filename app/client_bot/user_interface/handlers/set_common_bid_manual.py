
"""Ручная установка общей ставки в поисковой (аукционной) кампании.

Ordinary Telegram SetCommonBids / ``update_search_adv_common_cpm`` — Allowed OFF
only. При ``PENDING_SETUP`` / ``ACTIVE`` (``is_ab_hold_structural_freeze``)
ручное изменение общей ставки блокируется так же, как TP в keyword_settings.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, cast

from aiogram import Bot, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.client_bot import const
from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.messages.main_adv_setting_menu import AdvSettingMenu
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.di.wb_manager_hub import WBManagerHub, WBManagerHubFactory
from app.core.mp.wb.api.adapter.promotion_client.common_bids.command import (
    SetCommonBidsCommand,
    SetCommonBidsCommandItem,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.command import (
    SetNormqueryBidsCommandItem,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import is_ab_hold_structural_freeze

from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_cluster_bids_timestamp_manager import (
    RedisClusterBidsTimestampManager,

)
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_timestamp_manager import (
    RedisCommonBidTimestampManager,
)
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_value_manager import (
    RedisCommonBidValueManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.shared.domains.wb.utils.wb_campaign_meta import (
    wb_campaign_meta_known,
    wb_supports_normquery_minus_phrases,
)
from app.shared.domains.wb.enums import AdvType
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

router = Router()

MAX_BID_RUB = 3000

AB_HOLD_MANUAL_COMMON_BID_BLOCKED_MSG = (
    "Кампания в режиме A/B Hold — изменение общей ставки запрещено. "
    "Чтобы изменить ставку, выключите A/B Hold на экране режима."
)


@dataclass(frozen=True, slots=True)
class SearchBidApplyResult:
    """Summary of manual one-shot search bid updates."""

    updated_keywords: int
    total_keywords: int
    errors: tuple[str, ...]


async def load_adv_setting_menu_entities_in_session(
    session: AsyncSession,
    wb_user_cabinet_original_id: int,
    adv_setting_original_id: int,
) -> tuple[WBUserCabinet | None, AdvSetting | None]:
    """PURE_READ: cabinet + AdvSetting для reload меню через переданную session.

    Parent ``_reload_adv_setting_menu`` открывает ``sm(read_only=True)`` и
    передаёт session сюда. UI ``AdvSettingMenu`` вызывается снаружи.

    Args:
        session: SQLAlchemy AsyncSession (PURE_READ).
        wb_user_cabinet_original_id: PK ``WBUserCabinet.id``.
        adv_setting_original_id: PK ``AdvSetting.id``.

    Returns:
        Пара ``(wb_user_cabinet, adv_setting)``; любой элемент может быть ``None``.
    """
    wb_user_cabinet_result = await session.execute(
        select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    wb_user_cabinet = wb_user_cabinet_result.scalar_one_or_none()

    adv_result = await session.execute(
        select(AdvSetting)
        .options(joinedload(AdvSetting.wb_cabinet))
        .where(AdvSetting.id == adv_setting_original_id)
    )
    adv_setting_reload = adv_result.scalar_one_or_none()
    return wb_user_cabinet, adv_setting_reload


async def _reload_adv_setting_menu(
    bot: Bot,
    chat_id: int,
    wb_user_cabinet_original_id: int,
    adv_setting_original_id: int,
) -> None:
    """Перезагрузить меню настроек кампании."""
    async with sm(read_only=True) as session:
        wb_user_cabinet, adv_setting_reload = (
            await load_adv_setting_menu_entities_in_session(
                session,
                wb_user_cabinet_original_id,
                adv_setting_original_id,
            )
        )

    if wb_user_cabinet and adv_setting_reload:
        _ = await AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting_reload)()


def _build_complex_adv(main_adv: AdvSetting, search_adv: AdvSetting, shop_id: str) -> ComplexAdv:
    return ComplexAdv(
        adv_setting=main_adv,
        search_adv=search_adv,
        shop_id=shop_id,
    )


def _is_manual_search_campaign(search_adv_setting: AdvSetting) -> bool:
    """Allow manual search bid tool unless synced WB meta explicitly says otherwise."""
    if not wb_campaign_meta_known(search_adv_setting):
        return True
    return wb_supports_normquery_minus_phrases(search_adv_setting)


def _build_normquery_bid_items(
    current_bids: list[Any] | None,
    bid_value: int,
    search_adv_id: int,
) -> list[SetNormqueryBidsCommandItem]:
    """Build unique per-cluster write items from current WB search bids snapshot."""
    if not current_bids:
        return []
    seen: set[tuple[int, int, str]] = set()
    items: list[SetNormqueryBidsCommandItem] = []
    for bid in current_bids:
        advert_id = int(getattr(bid, "advert_id"))
        nm_id = int(getattr(bid, "nm_id"))
        norm_query = str(getattr(bid, "norm_query", "")).strip()
        key = (advert_id, nm_id, norm_query)
        if advert_id != search_adv_id or not norm_query or key in seen:
            continue
        seen.add(key)
        items.append(
            SetNormqueryBidsCommandItem(
                advert_id=advert_id,
                nm_id=nm_id,
                norm_query=norm_query,
                bid=bid_value,
            )
        )
    return items


async def _apply_normquery_bids(
    wb_modifier: Any,
    bid_items: list[SetNormqueryBidsCommandItem],
) -> SearchBidApplyResult:
    """Apply normquery bids one by one to preserve partial success reporting."""
    updated_keywords = 0
    errors: list[str] = []
    for item in bid_items:
        try:
            await wb_modifier.set_normquery_bids([item])
            updated_keywords += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "set_normquery_bids failed advert_id=%s nm_id=%s norm_query=%s",
                item.advert_id,
                item.nm_id,
                item.norm_query,
            )
            errors.append(f"{item.norm_query} (nm {item.nm_id}): {exc}")
    return SearchBidApplyResult(
        updated_keywords=updated_keywords,
        total_keywords=len(bid_items),
        errors=tuple(errors),
    )


async def set_common_bid_manual_start_in_session(
    session: AsyncSession,
    callback: types.CallbackQuery,
    callback_data: callbacks.SetCommonBidManual,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Открыть ручную установку common bid через переданную read-only session.

    Parent ``set_common_bid_manual_start`` открывает ``sm(read_only=True)`` и
    передаёт session сюда. Здесь загружаются обе кампании, вычисляется
    минимальная ставка и сохраняется FSM-контекст для следующего шага.
    """
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id

    adv_setting_original_id = callback_data.adv_setting_original_id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id

    stmt = (
        select(AdvSetting)
        .options(joinedload(AdvSetting.wb_cabinet))
        .where(AdvSetting.id == adv_setting_original_id)
    )
    result = await session.execute(stmt)
    adv_setting: AdvSetting | None = result.scalar_one_or_none()

    if not adv_setting:
        _ = await bot.send_message(chat_id, "Кампания не найдена.")
        return

    if is_ab_hold_structural_freeze(adv_setting.card_ab_hold_mode):
        _ = await bot.send_message(chat_id, AB_HOLD_MANUAL_COMMON_BID_BLOCKED_MSG)
        return

    if not adv_setting.search_adv_id:
        _ = await bot.send_message(
            chat_id,
            "У этой кампании нет поисковой (аукционной) РК.",
        )
        return

    search_adv_id = adv_setting.search_adv_id
    stmt_search = select(AdvSetting).where(AdvSetting.adv_id == search_adv_id)
    result_search = await session.execute(stmt_search)
    search_adv_setting: AdvSetting | None = result_search.scalar_one_or_none()

    if not search_adv_setting:
        _ = await bot.send_message(
            chat_id,
            "Поисковая РК не найдена в настройках.",
        )
        return
    if not _is_manual_search_campaign(search_adv_setting):
        _ = await bot.send_message(chat_id, "Эта кнопка доступна только для Поисковых РК.")
        return

    shop_id = adv_setting.wb_cabinet.shop_id if adv_setting.wb_cabinet else None
    if not shop_id:
        _ = await bot.send_message(chat_id, "Магазин не привязан к кампании.")
        return

    complex_adv = _build_complex_adv(adv_setting, search_adv_setting, shop_id)

    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            factory = cast(
                WBManagerHubFactory,
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory(),  # pyright: ignore
            )
            hub: WBManagerHub = factory.get_wb_manager_hub(shop_id)
            min_bids = await hub.wb_manager.get_min_bids_cache_only(
                [complex_adv],
                context="set_common_bid_manual",
            )
    except Exception:
        logger.exception("get_min_bids failed for adv_setting_id=%s", adv_setting_original_id)
        _ = await bot.send_message(
            chat_id,
            "Не удалось получить минимальную ставку из WB. Попробуйте позже.",
        )
        return

    nmids = list(adv_setting.nmids) if adv_setting.nmids else []
    if not nmids:
        _ = await bot.send_message(
            chat_id,
            "В кампании нет товаров (nmids). Невозможно получить минимальную ставку.",
        )
        return

    missing_nmids = [nmid for nmid in nmids if nmid not in min_bids.search]
    if missing_nmids:
        _ = await bot.send_message(
            chat_id,
            "Нет минимальных ставок в кеше для аукциона. Дождитесь обновления кеша.",
        )
        return

    min_common = max(min_bids.search[nmid] for nmid in nmids)
    _ = await state.update_data(
        adv_setting_original_id=adv_setting_original_id,
        wb_user_cabinet_original_id=wb_user_cabinet_original_id,
        min_bid_search=min_common,
    )
    await state.set_state(states.SetCommonBidManual.waiting_for_bid)
    _ = await bot.send_message(
        chat_id,
        f"Минимальная ставка для аукциона: {min_common} р.\n"
        f"Введите ставку для Поисковой РК (руб., целое число, не менее {min_common}):",
    )


@router.callback_query(callbacks.SetCommonBidManual.filter())
async def set_common_bid_manual_start(
    callback: types.CallbackQuery,
    callback_data: callbacks.SetCommonBidManual,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Открыть ручную установку common bid через injectable read-only session."""
    async with sm(read_only=True) as session:
        await set_common_bid_manual_start_in_session(
            session,
            callback,
            callback_data,
            bot,
            state,
        )


async def set_common_bid_manual_apply_in_session(
    session: AsyncSession,
    message: types.Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Применить common bid через переданную read-only session.

    Parent ``set_common_bid_manual_apply`` открывает ``sm(read_only=True)`` и
    передаёт session сюда. Здесь читаются актуальные данные РК, проверяется
    режим A/B Hold и после WB-обновления перезагружается меню.
    """
    chat_id = message.chat.id
    data: dict[str, Any] = await state.get_data()

    adv_setting_original_id = data.get("adv_setting_original_id")
    wb_user_cabinet_original_id = data.get("wb_user_cabinet_original_id")
    min_bid = data.get("min_bid_search")

    if adv_setting_original_id is None or wb_user_cabinet_original_id is None or min_bid is None:
        await state.set_state(None)
        _ = await message.answer(
            f"Произошла ошибка: не найдены сохраненные данные. Начните заново.\n\n"
            f"Если проблема будет повторяться, обратитесь в поддержку -> {const.SUPPORT_LINK}"
        )

        await asyncio.sleep(1)

        if wb_user_cabinet_original_id and adv_setting_original_id:
            await _reload_adv_setting_menu(
                bot, chat_id, wb_user_cabinet_original_id, adv_setting_original_id
            )

        return

    text = message.text or ""
    if not text.strip().isdigit():
        _ = await message.answer(
            f"Введите целое число (минимальная ставка {min_bid} р.).",
        )
        return

    bid_value = int(text.strip())
    if bid_value < min_bid:
        _ = await message.answer(
            f"Ставка не может быть меньше минимальной ({min_bid} р.).",
        )
        return
    if bid_value > MAX_BID_RUB:
        _ = await message.answer(
            f"Системное ограничение: ставка не более {MAX_BID_RUB} р.",
        )
        return

    stmt = (
        select(AdvSetting)
        .options(joinedload(AdvSetting.wb_cabinet))
        .where(AdvSetting.id == adv_setting_original_id)
    )
    result = await session.execute(stmt)
    adv_setting: AdvSetting | None = result.scalar_one_or_none()

    if not adv_setting or not adv_setting.search_adv_id:
        await state.set_state(None)
        _ = await message.answer("Кампания не найдена или нет поисковой РК.")
        return

    if is_ab_hold_structural_freeze(adv_setting.card_ab_hold_mode):
        await state.set_state(None)
        _ = await message.answer(AB_HOLD_MANUAL_COMMON_BID_BLOCKED_MSG)
        return

    search_adv_id = adv_setting.search_adv_id
    stmt_search = select(AdvSetting).where(AdvSetting.adv_id == search_adv_id)
    result_search = await session.execute(stmt_search)
    search_adv_setting: AdvSetting | None = result_search.scalar_one_or_none()

    if not search_adv_setting:
        await state.set_state(None)
        _ = await message.answer("Поисковая РК не найдена.")
        return
    if not _is_manual_search_campaign(search_adv_setting):
        await state.set_state(None)
        _ = await message.answer("Эта кнопка доступна только для Поисковых РК.")
        return

    shop_id = adv_setting.wb_cabinet.shop_id if adv_setting.wb_cabinet else None
    if not shop_id:
        await state.set_state(None)
        _ = await message.answer("Магазин не привязан к кампании.")
        return

    complex_adv = _build_complex_adv(adv_setting, search_adv_setting, shop_id)
    nmids = adv_setting.nmids
    if not nmids:
        await state.set_state(None)
        _ = await message.answer("В кампании нет товаров (nmids).")
        return

    command_items = [
        SetCommonBidsCommandItem(
            complex_adv=complex_adv,
            adv_type=AdvType.SEARCH,
            target_nmid=nmid,
            new_bid=bid_value,
        )
        for nmid in nmids
    ]
    command = SetCommonBidsCommand(items=command_items)

    _ = await message.answer(
        "Отправляю новую ставку в WB для Поисковой РК и её ключей..."
    )

    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            factory = cast(
                WBManagerHubFactory,
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory(),  # pyright: ignore
            )
            hub: WBManagerHub = factory.get_wb_manager_hub(shop_id)
            redis_client = hub.redis_client_wrapper
            current_bids = await hub.wb_data_manager.get_current_bids_for_advs(
                [complex_adv]
            )
            normquery_items = _build_normquery_bid_items(
                current_bids=current_bids,
                bid_value=bid_value,
                search_adv_id=int(search_adv_setting.adv_id),
            )

            await hub.wb_modifier.update_search_adv_common_cpm(command)
            normquery_result = await _apply_normquery_bids(
                hub.wb_modifier,
                normquery_items,
            )

            redis_bid_value = RedisCommonBidValueManager(redis_client)
            redis_bid_ts = RedisCommonBidTimestampManager(redis_client)
            bid_values = {nmid: bid_value for nmid in nmids}
            await redis_bid_value.set_bids(search_adv_id, bid_values)
            await redis_bid_ts.set(search_adv_id)
            if normquery_result.total_keywords > 0:
                cluster_bid_ts = RedisClusterBidsTimestampManager(redis_client)
                await cluster_bid_ts.set(adv_setting)
    except Exception:
        logger.exception(
            "update_search_adv_common_cpm failed for adv_setting_id=%s",
            adv_setting_original_id,
        )
        await state.set_state(None)
        _ = await message.answer(
            f"Ошибка при обновлении ставки на стороне WB,"
            f" при повторении ошибки обратитесь в поддержку -> {const.SUPPORT_LINK}"
        )
        return

    await state.set_state(None)
    if normquery_result.total_keywords == 0:
        _ = await message.answer(
            f"Готово. Общая ставка поисковой РК установлена: {bid_value} ₽. "
            "Ключи поисковой кампании для обновления ставок не найдены."
        )
    elif normquery_result.updated_keywords == normquery_result.total_keywords:
        _ = await message.answer(
            f"Готово. Общая ставка поисковой РК установлена: {bid_value} ₽. "
            "Такая же ставка поставлена всем ключам кампании."
        )
    else:
        errors_text = "; ".join(normquery_result.errors[:3])
        if len(normquery_result.errors) > 3:
            errors_text += f"; и ещё {len(normquery_result.errors) - 3}"
        _ = await message.answer(
            f"Общая ставка установлена: {bid_value} ₽. "
            f"По ключам обновлено: {normquery_result.updated_keywords} "
            f"из {normquery_result.total_keywords}. Ошибки: {errors_text}"
        )

    await _reload_adv_setting_menu(
        bot, chat_id, wb_user_cabinet_original_id, adv_setting_original_id
    )


@router.message(StateFilter(states.SetCommonBidManual.waiting_for_bid))
async def set_common_bid_manual_apply(
    message: types.Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Применить common bid через injectable read-only session."""
    async with sm(read_only=True) as session:
        await set_common_bid_manual_apply_in_session(session, message, bot, state)
