"""Подключение существующих рекламных кампаний WB к артикулу (NM-id).

Описание функционала и направление миграции -> app/client_bot/user_interface/handlers/CONNECT_EXISTING_SPEC.md

"""

import logging
from typing import Any, cast

from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import load_only

from app.client_bot.user_interface.states import ConnectExistingAdvsStates
from app.client_bot.user_interface.views import callbacks
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.mp.wb.api.excs import ApiForbiddenError, BadRequestError
from app.core.wb_api.mixins.excs import CardNotFoundInWB
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCard, WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.connect_existing_advs import (
    get_connect_existing_candidates,
    validate_campaign_id_for_connect,
)
from app.modules.connect_existing_advs.candidates_service import (
    ConnectExistingCandidatesResult,
)

from app.modules.connect_existing_advs.status_display import format_status_for_display

from app.modules.wb_adv_updater import data_manager as wb_data_manager

from app.utils.db.session_maker import get_async_session_maker as sm

from app.modules.shop_menu.message import ShopMenu

logger = logging.getLogger(__name__)

DONE_STATUS = "done"
CampaignData = dict[str, Any]

WB_WAIT_MESSAGE = "Идёт обращение к Wildberries, пожалуйста подождите."



# Критерии «существующая РК» совпадают с get_all_adv_ids_for_nmid (main_manager): не refused/done, type 8 или 9
EXISTING_ADV_ACTIVE_STATUS_NOT_IN = ("refused", "done")
EXISTING_ADV_TYPES = (8, 9)

# Маппинг статуса WB API (int) в строку active_status в БД
_WB_STATUS_TO_DB: dict[int, str] = {
    4: "ready_for_start",
    7: "done",
    8: "refused",
    9: "started",
    11: "pause",
}


def _wb_status_code_to_text(code: int) -> str:
    """Код статуса WB API → active_status; неизвестные коды → ``unknown`` (как раньше, не ``started``)."""
    return _WB_STATUS_TO_DB.get(code, "unknown")


# Статусы, при которых кампанию не предлагаем для подключения (завершена/отклонена)
_CONNECTABLE_EXCLUDE_STATUSES = (7, 8, "done", "refused")


def _is_connectable_candidate(item: CampaignData) -> bool:
    """Кампания подходит для подключения (не завершена и не отклонена)."""
    status = item.get("status")
    if status is None:
        return True
    return status not in _CONNECTABLE_EXCLUDE_STATUSES


async def _get_adv_statuses_from_db(
    wb_cabinet_id: int, adv_ids: list[int]
) -> dict[int, str]:
    """Вернуть словарь campaign_id -> active_status для указанных id (auto=adv_id, аукцион=_search_adv_id)."""
    if not adv_ids:
        return {}
    async with sm(read_only=True) as session:
        stmt = (
            select(
                AdvSetting.adv_id,
                getattr(AdvSetting, "_search_adv_id"),
                AdvSetting.active_status,
            )
            .where(
                AdvSetting.wb_cabinet_id == wb_cabinet_id,
                or_(
                    AdvSetting.adv_id.in_(adv_ids),
                    getattr(AdvSetting, "_search_adv_id").in_(adv_ids),
                ),
            )
        )
        result = await session.execute(stmt)
        out: dict[int, str] = {}
        for adv_id, search_adv_id, status in result.all():
            if status is not None:
                if adv_id is not None and adv_id in adv_ids:
                    out[adv_id] = status
                if search_adv_id is not None and search_adv_id in adv_ids:
                    out[search_adv_id] = status
        return out


async def _sync_adv_status_from_wb(
    shop_id: str, wb_cabinet_id: int, adv_ids: list[int]
) -> None:
    """Запросить статус РК в WB и обновить active_status в БД (чтобы убрать рассинхрон)."""
    if not adv_ids:
        return

    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            container_any: Any = cast(Any, container)
            factory = (
                container_any.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)
            pm = hub.wb_data_manager.promotion_manager
            for adv_id in adv_ids:
                wb_status = await pm.get_campaign_status(adv_id)
                if wb_status is None:
                    # API вернул пустой список по этому adv_id. Мы нигде не фильтруем по done:
                    # get_campaigns_info не передаёт statuses; get_cabinet_adv_ids — только limit/offset.
                    # Пусто = либо кампания удалена на WB, либо WB не отдаёт её по ids (напр. завершённые).
                    # В обоих случаях помечаем done, чтобы не предлагать для подключения.
                    db_status = "done"
                else:
                    db_status = _WB_STATUS_TO_DB.get(wb_status)
                    if db_status is None:
                        continue
                async with sm(read_only=False) as session:
                    stmt = (
                        update(AdvSetting)
                        .where(
                            AdvSetting.wb_cabinet_id == wb_cabinet_id,
                            or_(
                                AdvSetting.adv_id == adv_id,
                                getattr(AdvSetting, "_search_adv_id") == adv_id,
                            ),
                        )
                        .values(active_status=db_status)
                    )
                    await session.execute(stmt)
                    await session.commit()
    except Exception:
        logger.exception("connect_existing: sync adv status from WB failed")


async def _ensure_card_ready(shop_id: str, nmid: int) -> bool:
    """Проверить доступность карточки через WB API, fallback — ensure_card_in_db.

    В unit-тестах DI-цепочка мокается, поэтому сначала идем через неё.
    """
    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            container_any: Any = cast(Any, container)
            factory = (
                container_any.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)


            _ = await hub.wb_data_manager.products_manager.get_card_by_nmid(nmid)
            return True
    except (CardNotFoundInWB, ApiForbiddenError):
        raise
    except Exception:
        logger.exception("connect_existing: direct card check failed, fallback to ensure")
        return await wb_data_manager.ensure_card_in_db(shop_id, nmid)




async def _get_matching_adv_setting_for_connect_existing(
    wb_cabinet_id: int, nmid: int,
) -> AdvSetting | None:
    """Одна строка AdvSetting по фильтрам connect-existing; ORDER BY id — детерминизм при нескольких совпадениях."""
    async with sm(read_only=True) as session:
        stmt = (
            select(AdvSetting)
            .options(
                load_only(
                    AdvSetting.id,
                    AdvSetting.adv_id,
                    getattr(AdvSetting, "_search_adv_id"),
                    AdvSetting.name,
                )
            )
            .where(
                and_(
                    AdvSetting.wb_cabinet_id == wb_cabinet_id,
                    AdvSetting.nmids == [nmid],
                    AdvSetting.active_status.not_in(EXISTING_ADV_ACTIVE_STATUS_NOT_IN),
                    AdvSetting.type.in_(EXISTING_ADV_TYPES),
                )
            )
            .order_by(AdvSetting.id)
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()


async def _get_existing_adv_row_for_connect_not_done(
    wb_cabinet_id: int, nmid: int,
) -> tuple[int, int | None, int | None] | None:
    """(adv_setting.id, adv_id, search_adv_id) для той же строки, что и пара ID; иначе None."""
    adv = await _get_matching_adv_setting_for_connect_existing(wb_cabinet_id, nmid)
    if adv is None:
        return None
    return adv.id, adv.adv_id, adv.search_adv_id


async def _get_existing_adv_pair_not_done(
    wb_cabinet_id: int, nmid: int
) -> tuple[int | None, int | None] | None:
    """Если есть в БД РК по артикулу (статус не refused/done, type 8 или 9) — вернуть (adv_id, search_adv_id), иначе None."""
    adv = await _get_matching_adv_setting_for_connect_existing(wb_cabinet_id, nmid)
    if adv is None:
        return None
    return adv.adv_id, adv.search_adv_id


router = Router()


def _auction_choice_menu_keyboard(
    auction_list: list[CampaignData],
    wb_user_cabinet_original_id: int,
) -> InlineKeyboardMarkup:
    """Клавиатура: Ввести ID | Выбрать из списка (если есть) | Создать РК | Назад."""
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(
        [
            InlineKeyboardButton(
                text="Ввести ID кампании",
                callback_data=callbacks.ConnectExistingChooseAuction(
                    action="enter_id"
                ).pack(),
            )
        ]
    )
    if auction_list:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Выбрать из существующих",
                    callback_data=callbacks.ConnectExistingChooseAuction(
                        action="choose_list"
                    ).pack(),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Создать РК",
                callback_data=callbacks.ConnectExistingConfirmType1(adv_id=0).pack(),
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=callbacks.ConnectExistingChooseAuction(
                    action="back"
                ).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _auto_choice_menu_keyboard(
    auto_list: list[CampaignData],
    wb_user_cabinet_original_id: int,
) -> InlineKeyboardMarkup:
    """Клавиатура: Ввести ID | Выбрать из списка (если есть) | Создать РК | Назад."""
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(
        [
            InlineKeyboardButton(
                text="Ввести ID кампании",
                callback_data=callbacks.ConnectExistingChooseAuto(
                    action="enter_id"
                ).pack(),
            )
        ]
    )
    if auto_list:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Выбрать из существующих",
                    callback_data=callbacks.ConnectExistingChooseAuto(
                        action="choose_list"
                    ).pack(),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Создать РК",
                callback_data=callbacks.ConnectExistingConfirmType2(adv_id=0).pack(),
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=callbacks.ConnectExistingChooseAuto(action="back").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_auction_choice_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
) -> None:
    """Показать меню выбора способа для аукционной РК (шаг 1)."""
    data: dict[str, Any] = await state.get_data()
    auction_list: list[CampaignData] = data.get("auction_candidates") or []
    wb_user_cabinet_original_id: int = data.get("wb_user_cabinet_original_id") or 0
    await state.set_state(ConnectExistingAdvsStates.confirm_type1)
    kb = _auction_choice_menu_keyboard(auction_list, wb_user_cabinet_original_id)
    await bot.send_message(
        chat_id,
        "Как подключить поисковую (аукцион) РК для этого артикула?",
        reply_markup=kb,
    )


async def _send_auto_choice_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
) -> None:
    """Показать меню выбора способа для авто-РК (шаг 2)."""
    data: dict[str, Any] = await state.get_data()
    auto_list: list[CampaignData] = data.get("auto_candidates") or []
    wb_user_cabinet_original_id: int = data.get("wb_user_cabinet_original_id") or 0
    await state.set_state(ConnectExistingAdvsStates.confirm_type2)
    kb = _auto_choice_menu_keyboard(auto_list, wb_user_cabinet_original_id)
    await bot.send_message(
        chat_id,
        "Как подключить авто-кампанию для этого артикула?",
        reply_markup=kb,
    )


async def _save_connect_existing_finish(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    data: dict[str, Any],
    chosen_auction: int,
    chosen_auto: int,
    auto_candidates: list[CampaignData],
) -> None:
    """Сохранить выбранную пару аукцион+авто в AdvSetting и показать меню магазина."""
    nmid = data["nmid"]
    wb_cabinet_id = data["wb_cabinet_id"]
    shop_id = data.get("shop_id")
    card_name = data.get("card_name")
    if not card_name and shop_id:
        try:
            async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
                container_any: Any = cast(Any, container)
                factory = (
                    container_any.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
                )
                hub = factory.get_wb_manager_hub(shop_id)
                card = await hub.wb_data_manager.products_manager.get_card_by_nmid(nmid)
                card_name = card.name
        except Exception as e:
            logger.warning("connect_existing could not fetch card for name: %s", e)
            card_name = str(nmid)
    if not card_name:
        card_name = str(nmid)

    from app.modules.adv_creator.backend.main_manager import get_name_for_adv

    auto_name = get_name_for_adv(nmid, card_name, "auto")
    auction_name = get_name_for_adv(nmid, card_name, "auction")
    complex_adv_name = get_name_for_adv(nmid, card_name, "complex")
    auto_name_trunc = auto_name[:100]
    auction_name_trunc = auction_name[:100]

    auction_candidates: list[CampaignData] = data.get("auction_candidates") or []
    current_auction_name = next(
        (c["name"] for c in auction_candidates if c["id"] == chosen_auction),
        "",
    )
    current_auto_name = next(
        (c["name"] for c in auto_candidates if c["id"] == chosen_auto),
        "",
    )
    need_rename_auction = current_auction_name.strip() != auction_name_trunc.strip()
    need_rename_auto = current_auto_name.strip() != auto_name_trunc.strip()

    if shop_id:
        try:
            async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
                container_any: Any = cast(Any, container)
                factory = (
                    container_any.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
                )
                hub = factory.get_wb_manager_hub(shop_id)
                pm = hub.wb_data_manager.promotion_manager
                await pm.set_auction_placement(
                    chosen_auction, search=True, recommendations=False
                )
                if need_rename_auction:
                    await pm.rename_campaign(chosen_auction, auction_name_trunc)
                if need_rename_auto:
                    await pm.rename_campaign(chosen_auto, auto_name_trunc)
        except Exception:
            logger.exception(
                "connect_existing set_auction_placement or rename_campaign failed"
            )
            await bot.send_message(
                chat_id,
                "Кампании подключены в боте, но настройка размещения или переименование на WB не удалось. "
                "Проверьте кампанию в кабинете WB.",
            )

    from app.modules.adv_creator.backend.main_manager import MainAdvManager

    async with sm(read_only=False) as session:
        wb_cabinet = await session.get(WBCabinet, wb_cabinet_id)
        if wb_cabinet is None:
            await bot.send_message(chat_id, "Кабинет не найден.")
            return
        auto_status_text = "started"
        for c in auto_candidates:
            if c.get("id") == chosen_auto and "status" in c:
                auto_status_text = _wb_status_code_to_text(int(c["status"]))
                break
        # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
        adv_data = {
            "adv_id": chosen_auto,
            "_search_adv_id": chosen_auction,
            "max_place": 1,
            "max_cpm": wb_cabinet.default_max_cpm,
            "reset_place": True,
            "name": complex_adv_name,
            "bidder_active": False,
            "wb_cabinet_id": wb_cabinet.id,
            "parsing_active": False,
            "bot_active": False,
            "auto_adv_target_status": False,
            "auto_update_white_list": False,
            "auto_update_target_place": False,
            "active_status": auto_status_text,
            "type": 8,
            "nmids": [nmid],
            "hard_min_ctr": 0.1,
        }
        insert_stmt = insert(AdvSetting).values(adv_data)
        on_conflict_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["adv_id"],
            set_={k: v for k, v in adv_data.items() if k != "adv_id"},
        )
        await session.execute(on_conflict_stmt)
        await session.commit()
        logger.info(
            "connect_existing upserted AdvSetting adv_id=%s nmid=%s auction=%s",
            chosen_auto,
            nmid,
            chosen_auction,
        )

    # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
    await getattr(MainAdvManager, "_apply_default_settings_to_adv")(chosen_auto)
    wb_user_cabinet_original_id = data.get("wb_user_cabinet_original_id")
    await state.clear()
    await bot.send_message(
        chat_id,
        f"Кампании подключены для артикула {nmid}. Аукцион: {chosen_auction}, Авто: {chosen_auto}.",
    )
    if wb_user_cabinet_original_id is not None:
        await ShopMenu(
            bot,
            chat_id,
            state,
            wb_user_cabinet_original_id,
        )()


def _serialize_candidates(
    result: ConnectExistingCandidatesResult,
) -> tuple[list[CampaignData], list[CampaignData]]:
    """Serialize candidates for FSM state (id, name, status, status_text)."""
    def _item_dict(c: Any) -> CampaignData:
        status_val = getattr(c.status, "value", c.status) if hasattr(c, "status") else None
        return {
            "id": c.id,
            "name": c.settings.name,
            "status": status_val,
            "status_text": format_status_for_display(status_val),
        }
    auction = [_item_dict(c) for c in result.auction_candidates]
    auto = [_item_dict(c) for c in result.auto_candidates]
    return auction, auto


@router.callback_query(callbacks.ConnectExistingAdvs.filter())
async def connect_existing_advs_start(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingAdvs,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Точка входа: «Подключить существующие кампании» — запрос NM-id."""
    await state.clear()
    if callback.message is None:
        return
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(ConnectExistingAdvsStates.waiting_nmid)
    await bot.send_message(
        callback.message.chat.id,
        "Введите артикул WB товара — одно число, больше 0:",
    )


async def _connect_existing_after_card_resolved(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    nmid: int,
    card_name: str,
    wb_user_cabinet_original_id: int,
    shop_id: str,
    wb_cabinet_id: int,
) -> None:
    """Продолжить сценарий «подключить существующие» после успешного получения карточки по артикулу."""
    existing_row = await _get_existing_adv_row_for_connect_not_done(
        wb_cabinet_id, nmid
    )
    existing_pair = None
    if existing_row is not None:
        adv_setting_original_id, existing_auto_id, existing_auction_id = existing_row
        existing_pair = (existing_auto_id, existing_auction_id)
        if existing_auto_id is not None and existing_auction_id is not None:
            ids_text = f"Аукцион: {existing_auction_id}, Авто: {existing_auto_id}"
            await state.clear()
            first_row: list[InlineKeyboardButton] = [
                InlineKeyboardButton(
                    text="Перепривязать кампании WB",
                    callback_data=callbacks.RebindAdvCampaignIds(
                        action="menu",
                        adv_setting_original_id=adv_setting_original_id,
                        wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="В меню магазина",
                    callback_data=callbacks.ConnectExistingAdvsBackToShop(
                        wb_user_cabinet_original_id=wb_user_cabinet_original_id
                    ).pack(),
                ),
            ]
            second_row = [
                InlineKeyboardButton(
                    text="Ввести другой артикул",
                    callback_data=callbacks.ConnectExistingChangeNmid(
                        wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                    ).pack(),
                ),
            ]
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[first_row, second_row]
            )
            await bot.send_message(
                chat_id,
                f"Для этого артикула уже есть подключённые РК (Аукцион и Авто). "
                f"ID кампаний: {ids_text}. Перепривяжите кампании, введите другой артикул "
                f"или вернитесь в меню магазина.",
                reply_markup=keyboard,
            )
            return
        await state.update_data(
            existing_auto_id=existing_auto_id,
            existing_auction_id=existing_auction_id,
            card_name=card_name,
        )

    extra_adv_ids = []
    if existing_pair is not None:
        extra_adv_ids = [
            x for x in (existing_pair[0], existing_pair[1]) if x is not None
        ]
    try:
        candidates_result = await get_connect_existing_candidates(
            shop_id, nmid, extra_adv_ids=extra_adv_ids or None
        )
        logger.info(
            "connect_existing candidates for nmid=%s shop_id=%s: auction=%s auto=%s",
            nmid,
            shop_id,
            len(candidates_result.auction_candidates),
            len(candidates_result.auto_candidates),
        )
    except ApiForbiddenError:
        await bot.send_message(
            chat_id,
            "Нет доступа к API WB. Проверьте токены магазина.",
        )
        return
    except BadRequestError as e:
        detail = (getattr(e, "detail", None) or str(e)).lower()
        if "path not found" in detail or "not found" in detail:
            candidates_result = ConnectExistingCandidatesResult(
                auction_candidates=[],
                auto_candidates=[],
            )
            logger.info(
                "connect_existing: WB returned not found for shop (no adverts?), treating as empty candidates"
            )
        else:
            logger.exception("connect_existing get_candidates BadRequestError")
            await bot.send_message(
                chat_id,
                "Ошибка запроса к WB. Попробуйте позже или обратитесь в поддержку.",
            )
            return
    except Exception:
        logger.exception("connect_existing get_candidates failed")
        await bot.send_message(
            chat_id,
            "Ошибка при получении списка кампаний. Попробуйте позже или обратитесь в поддержку.",
        )
        return

    auction_list, auto_list = _serialize_candidates(candidates_result)
    auction_list = [a for a in auction_list if _is_connectable_candidate(a)]
    auto_list = [a for a in auto_list if _is_connectable_candidate(a)]
    await state.update_data(
        nmid=nmid,
        wb_cabinet_id=wb_cabinet_id,
        shop_id=shop_id,
        card_name=card_name,
        auction_candidates=auction_list,
        auto_candidates=auto_list,
        chosen_auction_adv_id=None,
        chosen_auto_adv_id=None,
    )

    if not auction_list and auto_list:
        await state.set_state(
            ConnectExistingAdvsStates.waiting_confirm_continue_invalid
        )
        lines = [
            "По этому артикулу в WB найдены авто-кампании без поисковой:",
            "",
        ]
        for a in auto_list:
            status_txt = a.get("status_text") or format_status_for_display(a.get("status"))
            lines.append(f"• Авто-РК: {a['id']}, статус: {status_txt}, поисковая: не указана")
        lines.extend(
            [
                "",
                "Чтобы полноценно вести рекламу, нужна и поисковая РК. Нажмите «Создать поисковую РК» — бот создаст поисковую кампанию и привяжет к первой авто из списка. Или «Отмена».",
            ]
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Создать поисковую РК",
                        callback_data=callbacks.ConnectExistingContinueDespiteInvalid(
                            action="confirm"
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Отмена",
                        callback_data=callbacks.ConnectExistingContinueDespiteInvalid(
                            action="cancel"
                        ).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)
        return

    if not auction_list and not auto_list:
        data_for_branch = await state.get_data()
        existing_auto_id_from_db = data_for_branch.get("existing_auto_id")
        existing_auction_id_from_db = data_for_branch.get("existing_auction_id")
        if existing_auto_id_from_db is not None or existing_auction_id_from_db is not None:
            adv_ids_to_sync = [
                x for x in (existing_auto_id_from_db, existing_auction_id_from_db) if x is not None
            ]
            await _sync_adv_status_from_wb(shop_id, wb_cabinet_id, adv_ids_to_sync)
            existing_pair_after_sync = await _get_existing_adv_pair_not_done(
                wb_cabinet_id, nmid
            )
            if existing_pair_after_sync is None:
                await state.set_state(
                    ConnectExistingAdvsStates.waiting_confirm_create_both
                )
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Да, создать обе",
                                callback_data=callbacks.ConnectExistingCreateBoth(
                                    action="confirm"
                                ).pack(),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="Нет",
                                callback_data=callbacks.ConnectExistingCreateBoth(
                                    action="cancel"
                                ).pack(),
                            )
                        ],
                    ],
                )
                await bot.send_message(
                    chat_id,
                    f"По этому артикулу в нашей базе была запись о кампании. Статус обновлён с WB: кампания завершена. РК для этого артикула нет. Создать обе (аукцион + авто)?",
                    reply_markup=kb,
                )
                return
            search_already_in_db = (
                existing_auction_id_from_db is not None
                or existing_pair_after_sync[1] is not None
            )
            statuses = await _get_adv_statuses_from_db(
                wb_cabinet_id, adv_ids_to_sync
            )
            lines = [
                "По этому артикулу в боте есть запись о кампании (по нашей базе она не «завершена» и не «отклонена»):",
                "",
            ]
            if existing_auto_id_from_db is not None:
                st_auto = format_status_for_display(statuses.get(existing_auto_id_from_db))
                st_auction = format_status_for_display(statuses.get(existing_auction_id_from_db)) if existing_auction_id_from_db else "—"
                lines.append(
                    f"• Авто-РК: {existing_auto_id_from_db}, статус: {st_auto}; поисковая РК: {existing_auction_id_from_db if existing_auction_id_from_db else 'не указана'}, статус: {st_auction}"
                )
            if existing_auction_id_from_db is not None and existing_auto_id_from_db is None:
                st_auction = format_status_for_display(statuses.get(existing_auction_id_from_db))
                lines.append(
                    f"• Поисковая РК: {existing_auction_id_from_db}, статус: {st_auction}; авто-РК: не указана"
                )
            lines.append("")
            lines.append(
                "В списке кампаний по артикулу от WB эта кампания не пришла (так бывает: API не всегда отдаёт все кампании в выборке). Статус выше только что обновлён с WB — если там «пауза» или «запущена», кампания на WB есть."
            )
            if search_already_in_db:
                lines.append("")
                lines.append(
                    "Поисковая РК уже привязана к артикулу в боте. Дополнительно создавать её не нужно — вернитесь в меню магазина."
                )
                wb_uid = data_for_branch.get("wb_user_cabinet_original_id")
                if isinstance(wb_uid, int):
                    kb = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="В меню магазина",
                                    callback_data=callbacks.ConnectExistingAdvsBackToShop(
                                        wb_user_cabinet_original_id=wb_uid
                                    ).pack(),
                                )
                            ],
                        ],
                    )
                else:
                    kb = InlineKeyboardMarkup(inline_keyboard=[])
                await state.clear()
            else:
                lines.extend(
                    [
                        "",
                        "Что можно сделать:",
                        "• «Создать поисковую РК» — бот создаст поисковую кампанию и привяжет к этой авто.",
                        "• «Отмена» — ничего не создаём.",
                    ]
                )
                await state.set_state(
                    ConnectExistingAdvsStates.waiting_confirm_continue_invalid
                )
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Создать поисковую РК",
                                callback_data=callbacks.ConnectExistingContinueDespiteInvalid(
                                    action="confirm"
                                ).pack(),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="Отмена",
                                callback_data=callbacks.ConnectExistingContinueDespiteInvalid(
                                    action="cancel"
                                ).pack(),
                            )
                        ],
                    ],
                )
            await bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)
            return
        await state.set_state(ConnectExistingAdvsStates.waiting_confirm_create_both)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Да, создать обе",
                        callback_data=callbacks.ConnectExistingCreateBoth(
                            action="confirm"
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Нет",
                        callback_data=callbacks.ConnectExistingCreateBoth(
                            action="cancel"
                        ).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            chat_id,
            f"Кампании для артикула {nmid} не найдены. Создать обе (аукцион + авто)?",
            reply_markup=kb,
        )
        return

    data_after = await state.get_data()
    existing_auction_id = data_after.get("existing_auction_id")
    if existing_auction_id:
        await state.update_data(chosen_auction_adv_id=existing_auction_id)
        await _send_auto_choice_menu(bot, chat_id, state)
        return

    await _send_auction_choice_menu(bot, chat_id, state)

@router.message(StateFilter(ConnectExistingAdvsStates.waiting_nmid))
async def connect_existing_advs_nmid(
    message: Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Принять NM-id, проверить карточку на WB, получить кандидатов, показать первый тип (аукцион)."""
    if message.text is None:
        await bot.send_message(message.chat.id, "Отправьте Артикул WB товара числом.")
        return

    text = message.text.strip()
    try:
        nmid = int(text)
    except ValueError:
        await bot.send_message(
            message.chat.id, "Артикул WB товара должен быть целым числом."
        )
        return

    if nmid <= 0:
        await bot.send_message(
            message.chat.id, "Артикул WB товара  должен быть больше 0."
        )
        return

    data: dict[str, Any] = await state.get_data()
    wb_user_cabinet_original_id: int = data["wb_user_cabinet_original_id"]

    async with sm(read_only=True) as session:
        stmt = (
            select(WBCabinet.id, WBCabinet.shop_id)
            .join(WBUserCabinet)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        row = result.one_or_none()

    if row is None:
        await bot.send_message(message.chat.id, "Кабинет не найден.")
        return

    wb_cabinet_id, shop_id = row[0], str(row[1])

    await bot.send_message(message.chat.id, WB_WAIT_MESSAGE)
    try:
        card_ready = await _ensure_card_ready(shop_id, nmid)
        if not card_ready:
            await bot.send_message(
                message.chat.id,
                "Не удалось дождаться загрузки карточки в базу. Попробуйте позже.",
            )
            return
    except CardNotFoundInWB:
        await state.update_data(
            nmid=nmid,
            wb_user_cabinet_original_id=wb_user_cabinet_original_id,
            shop_id=shop_id,
            wb_cabinet_id=wb_cabinet_id,
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Загрузить и найти по полному списку",
                        callback_data=callbacks.ConnectExistingCardNotFound(
                            action="retry_full_list"
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="В меню магазина",
                        callback_data=callbacks.ConnectExistingAdvsBackToShop(
                            wb_user_cabinet_original_id=wb_user_cabinet_original_id
                        ).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            message.chat.id,
            "С фильтром артикул не найден. Проверьте, правильный ли артикул и от этого ли магазина.\n\n"
            "Если уверены — нажмите «Загрузить и найти по полному списку». Будет загружен полный список карточек без фильтра, может занять длительное время.",
            reply_markup=keyboard,
        )
        return
    except ApiForbiddenError:
        await bot.send_message(
            message.chat.id,
            "Нет доступа к API WB. Проверьте токены магазина.",
        )
        return

    async with sm(read_only=True) as session:
        stmt_card_name = select(WBCard.name).where(WBCard.nmid == nmid).limit(1)
        result_card_name = await session.execute(stmt_card_name)
        card_name = result_card_name.scalar_one_or_none() or str(nmid)

    await _connect_existing_after_card_resolved(
        bot,
        message.chat.id,
        state,
        nmid,
        card_name,
        wb_user_cabinet_original_id,
        shop_id,
        wb_cabinet_id,
    )

@router.callback_query(
    StateFilter(ConnectExistingAdvsStates.waiting_nmid),
    callbacks.ConnectExistingCardNotFound.filter(),
)
async def connect_existing_card_not_found_retry_full_list(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingCardNotFound,
    bot: Bot,
    state: FSMContext,
) -> None:
    """По нажатию «Загрузить и найти по полному списку» — поиск карточки без фильтра."""
    if callback_data.action != "retry_full_list":
        return

    if callback.message is None:
        return

    chat_id = callback.message.chat.id
    data: dict[str, Any] = await state.get_data()
    nmid = data.get("nmid")
    shop_id = data.get("shop_id")
    wb_user_cabinet_original_id = data.get("wb_user_cabinet_original_id")
    wb_cabinet_id = data.get("wb_cabinet_id")

    if (
        nmid is None
        or shop_id is None
        or wb_user_cabinet_original_id is None
        or wb_cabinet_id is None
    ):
        await bot.send_message(
            chat_id,
            "Сессия устарела. Введите артикул заново или вернитесь в меню магазина.",
        )
        return

    await bot.send_message(chat_id, "Идёт поиск по полному списку карточек…")

    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            container_any: Any = cast(Any, container)
            factory = (
                container_any.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)
            card = await hub.wb_data_manager.products_manager.get_card_by_nmid_via_full_list(nmid)
    except CardNotFoundInWB:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="В меню магазина",
                        callback_data=callbacks.ConnectExistingAdvsBackToShop(
                            wb_user_cabinet_original_id=wb_user_cabinet_original_id
                        ).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            chat_id,
            "Артикул не найден на Wildberries. Проверьте NM-id и магазин.",
            reply_markup=keyboard,
        )
        return
    except ApiForbiddenError:
        await bot.send_message(
            chat_id,
            "Нет доступа к API WB. Проверьте токены магазина.",
        )
        return

    await _connect_existing_after_card_resolved(
        bot,
        chat_id,
        state,
        nmid,
        card.name,
        wb_user_cabinet_original_id,
        shop_id,
        wb_cabinet_id,
    )

@router.callback_query(
    StateFilter(
        ConnectExistingAdvsStates.confirm_type1,
        ConnectExistingAdvsStates.waiting_auction_adv_id,
    ),
    callbacks.ConnectExistingChooseAuction.filter(),
)
async def connect_existing_choose_auction(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingChooseAuction,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Меню выбора способа для аукционной РК: ввести ID, список, создать, назад."""
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    data: dict[str, Any] = await state.get_data()
    wb_user_cabinet_original_id: int = data.get("wb_user_cabinet_original_id") or 0
    auction_list: list[CampaignData] = data.get("auction_candidates") or []

    if callback_data.action == "back":
        await state.clear()
        await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
        await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
        return

    if callback_data.action == "enter_id":
        await state.set_state(ConnectExistingAdvsStates.waiting_auction_adv_id)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Назад",
                        callback_data=callbacks.ConnectExistingChooseAuction(
                            action="back"
                        ).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            chat_id,
            "Введите ID поисковой (аукцион) кампании — одно число. Или нажмите «Назад».",
            reply_markup=kb,
        )
        return

    if callback_data.action == "choose_list":
        if not auction_list:
            await bot.send_message(chat_id, "Список кампаний пуст.")
            await _send_auction_choice_menu(bot, chat_id, state)
            return
        rows: list[list[InlineKeyboardButton]] = []
        for c in auction_list:
            label = f"{c.get('name', '') or c['id']} (ID {c['id']})"
            if len(label) > 40:
                label = f"ID {c['id']} — {str(c.get('name', ''))[:30]}…"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=label,
                        callback_data=callbacks.ConnectExistingConfirmType1(
                            adv_id=c["id"]
                        ).pack(),
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=callbacks.ConnectExistingChooseAuction(
                        action="back"
                    ).pack(),
                )
            ],
        )
        await state.set_state(ConnectExistingAdvsStates.confirm_type1)
        await bot.send_message(
            chat_id,
            "Выберите поисковую (аукцион) кампанию из списка:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        return

    if callback_data.action == "create":
        await bot.send_message(
            chat_id,
            "Создание аукционной РК будет доступно в следующем обновлении. Пока выберите существующую (ввести ID или из списка).",
        )
        await _send_auction_choice_menu(bot, chat_id, state)
        return


@router.message(StateFilter(ConnectExistingAdvsStates.waiting_auction_adv_id))
async def connect_existing_auction_adv_id_entered(
    message: Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Принять введённый ID аукционной кампании, проверить и перейти к шагу 2 или показать ошибку."""
    if message.text is None:
        await bot.send_message(
            message.chat.id,
            "Отправьте ID кампании числом или нажмите «Назад».",
        )
        return
    text = message.text.strip()
    try:
        adv_id = int(text)
    except ValueError:
        await bot.send_message(
            message.chat.id,
            "ID кампании должен быть целым числом. Введите снова или нажмите «Назад».",
        )
        return
    if adv_id <= 0:
        await bot.send_message(
            message.chat.id,
            "ID кампании должен быть больше 0. Введите снова или нажмите «Назад».",
        )
        return

    data = await state.get_data()
    shop_id = data.get("shop_id")
    nmid = data.get("nmid")
    if not shop_id or nmid is None:
        await bot.send_message(
            message.chat.id,
            "Данные сессии потеряны. Начните заново.",
        )
        await state.clear()
        return

    ok, err_msg, candidate = await validate_campaign_id_for_connect(
        shop_id, nmid, adv_id, "auction"
    )
    if not ok:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Ввести снова",
                        callback_data=callbacks.ConnectExistingChooseAuction(
                            action="enter_id"
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Назад",
                        callback_data=callbacks.ConnectExistingChooseAuction(
                            action="back"
                        ).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            message.chat.id,
            f"{err_msg} Введите другой ID или нажмите «Назад».",
            reply_markup=kb,
        )
        return

    assert candidate is not None
    await state.update_data(chosen_auction_adv_id=candidate["id"])
    await state.set_state(ConnectExistingAdvsStates.confirm_type2)
    await _send_auto_choice_menu(bot, message.chat.id, state)


@router.callback_query(
    StateFilter(
        ConnectExistingAdvsStates.confirm_type1,
        ConnectExistingAdvsStates.waiting_auction_adv_id,
    ),
    callbacks.ConnectExistingConfirmType1.filter(),
)
async def connect_existing_confirm_type1(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingConfirmType1,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Выбор аукционной РК из списка → показать меню способа для авто (шаг 2)."""
    if callback.message is None:
        return
    chosen_auction = (
        callback_data.adv_id if callback_data.adv_id else None
    )  # 0 = создать
    await state.update_data(chosen_auction_adv_id=chosen_auction)
    if chosen_auction is None:
        await bot.send_message(
            callback.message.chat.id,
            "Создание аукционной РК будет доступно в следующем обновлении. Пока выберите существующую (ввести ID или из списка).",
        )
        await _send_auction_choice_menu(bot, callback.message.chat.id, state)
        return

    await _send_auto_choice_menu(bot, callback.message.chat.id, state)


@router.callback_query(
    StateFilter(
        ConnectExistingAdvsStates.confirm_type2,
        ConnectExistingAdvsStates.waiting_auto_adv_id,
    ),
    callbacks.ConnectExistingConfirmType2.filter(),
)
async def connect_existing_confirm_type2(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingConfirmType2,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Подтверждение/создание по второму типу (авто) → сохранить в AdvSetting."""
    if callback.message is None:
        return
    data = await state.get_data()
    chosen_auto = callback_data.adv_id if callback_data.adv_id else None
    if chosen_auto is None:
        chosen_auction = data.get("chosen_auction_adv_id")
        nmid = data.get("nmid")
        shop_id = data.get("shop_id")
        if chosen_auction is None:
            await bot.send_message(
                callback.message.chat.id,
                "Сначала выберите аукционную кампанию.",
            )
            return
        if nmid is None or shop_id is None:
            await bot.send_message(
                callback.message.chat.id, "Данные сессии потеряны. Начните заново."
            )
            return
        try:
            from arq import create_pool
            from app.arq_workers.arq_redis_settings import arq_redis_settings

            redis_task_pool = await create_pool(arq_redis_settings)
            await redis_task_pool.enqueue_job(
                "create_auto_only",
                nmid,
                shop_id,
                chosen_auction,
                callback.from_user.id,
            )
            await bot.send_message(
                callback.message.chat.id,
                "Задача на создание авто-РК добавлена в очередь. Ожидайте уведомления.",
            )
        except Exception as e:
            logger.exception(
                "connect_existing enqueue create_auto_only failed"
            )
            await bot.send_message(
                callback.message.chat.id,
                f"Не удалось поставить задачу: {e}",
            )
        finally:
            await state.clear()
        # После старта создания авто-РК меню магазина не показываем.
        return

    chosen_auction = data.get("chosen_auction_adv_id")
    if chosen_auction is None:
        await bot.send_message(
            callback.message.chat.id,
            "Сначала выберите или создайте аукционную кампанию.",
        )
        return

    auto_candidates_list: list[CampaignData] = data.get("auto_candidates") or []
    await _save_connect_existing_finish(
        bot,
        int(callback.message.chat.id),
        state,
        data,
        chosen_auction,
        chosen_auto,
        auto_candidates_list,
    )


@router.callback_query(
    StateFilter(
        ConnectExistingAdvsStates.confirm_type2,
        ConnectExistingAdvsStates.waiting_auto_adv_id,
    ),
    callbacks.ConnectExistingChooseAuto.filter(),
)
async def connect_existing_choose_auto(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingChooseAuto,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Меню выбора способа для авто-РК: ввести ID, список, создать, назад."""
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    data: dict[str, Any] = await state.get_data()
    auto_list: list[CampaignData] = data.get("auto_candidates") or []

    if callback_data.action == "back":
        await _send_auction_choice_menu(bot, chat_id, state)
        return

    if callback_data.action == "enter_id":
        await state.set_state(ConnectExistingAdvsStates.waiting_auto_adv_id)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Назад",
                        callback_data=callbacks.ConnectExistingChooseAuto(
                            action="back"
                        ).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            chat_id,
            "Введите ID авто-кампании — одно число. Или нажмите «Назад».",
            reply_markup=kb,
        )
        return

    if callback_data.action == "choose_list":
        if not auto_list:
            await bot.send_message(chat_id, "Список кампаний пуст.")
            await _send_auto_choice_menu(bot, chat_id, state)
            return
        rows: list[list[InlineKeyboardButton]] = []
        for c in auto_list:
            label = f"{c.get('name', '') or c['id']} (ID {c['id']})"
            if len(label) > 40:
                label = f"ID {c['id']} — {str(c.get('name', ''))[:30]}…"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=label,
                        callback_data=callbacks.ConnectExistingConfirmType2(
                            adv_id=c["id"]
                        ).pack(),
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=callbacks.ConnectExistingChooseAuto(
                        action="back"
                    ).pack(),
                )
            ],
        )
        await state.set_state(ConnectExistingAdvsStates.confirm_type2)
        await bot.send_message(
            chat_id,
            "Выберите авто-кампанию из списка:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        return

    if callback_data.action == "create":
        await bot.send_message(
            chat_id,
            "Создание авто-РК: нажмите кнопку «Создать РК» в меню выше (она добавляет задачу в очередь).",
        )
        await _send_auto_choice_menu(bot, chat_id, state)
        return


@router.message(StateFilter(ConnectExistingAdvsStates.waiting_auto_adv_id))
async def connect_existing_auto_adv_id_entered(
    message: Message,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Принять введённый ID авто-кампании, проверить и сохранить или показать ошибку."""
    if message.text is None:
        await bot.send_message(
            message.chat.id,
            "Отправьте ID кампании числом или нажмите «Назад».",
        )
        return
    text = message.text.strip()
    try:
        adv_id = int(text)
    except ValueError:
        await bot.send_message(
            message.chat.id,
            "ID кампании должен быть целым числом. Введите снова или нажмите «Назад».",
        )
        return
    if adv_id <= 0:
        await bot.send_message(
            message.chat.id,
            "ID кампании должен быть больше 0. Введите снова или нажмите «Назад».",
        )
        return

    data = await state.get_data()
    shop_id = data.get("shop_id")
    nmid = data.get("nmid")
    chosen_auction = data.get("chosen_auction_adv_id")
    if not shop_id or nmid is None or chosen_auction is None:
        await bot.send_message(
            message.chat.id,
            "Данные сессии потеряны. Начните заново.",
        )
        await state.clear()
        return

    ok, err_msg, candidate = await validate_campaign_id_for_connect(
        shop_id, nmid, adv_id, "auto"
    )
    if not ok:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Ввести снова",
                        callback_data=callbacks.ConnectExistingChooseAuto(
                            action="enter_id"
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Назад",
                        callback_data=callbacks.ConnectExistingChooseAuto(
                            action="back"
                        ).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            message.chat.id,
            f"{err_msg} Введите другой ID или нажмите «Назад».",
            reply_markup=kb,
        )
        return

    assert candidate is not None
    await _save_connect_existing_finish(
        bot,
        message.chat.id,
        state,
        data,
        chosen_auction,
        candidate["id"],
        [candidate],
    )


@router.callback_query(
    StateFilter(ConnectExistingAdvsStates.waiting_confirm_create_both),
    callbacks.ConnectExistingCreateBoth.filter(),
)
async def connect_existing_create_both(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingCreateBoth,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Подтверждение создания обеих кампаний (create_complex_advs) или отмена."""
    if callback.message is None:
        return
    if callback_data.action == "cancel":
        data = await state.get_data()
        wb_user_cabinet_original_id = data.get("wb_user_cabinet_original_id")
        await state.clear()
        if wb_user_cabinet_original_id is not None:
            await ShopMenu(
                bot,
                int(callback.message.chat.id),
                state,
                wb_user_cabinet_original_id,
            )()
        else:
            await bot.send_message(callback.message.chat.id, "Отменено.")
        return
    data = await state.get_data()
    nmid = data.get("nmid")
    shop_id = data.get("shop_id")
    if nmid is None or shop_id is None:
        await bot.send_message(
            callback.message.chat.id, "Данные сессии потеряны. Начните заново."
        )
        return
    try:
        from arq import create_pool
        from app.arq_workers.arq_redis_settings import arq_redis_settings

        redis_task_pool = await create_pool(arq_redis_settings)
        await redis_task_pool.enqueue_job(
            "create_complex_advs",
            nmid,
            shop_id,
            False,
            callback.from_user.id,
        )
        await bot.send_message(
            callback.message.chat.id,
            "Задача на создание обеих кампаний добавлена в очередь. Ожидайте уведомления.",
        )
    except Exception as e:
        logger.exception("connect_existing enqueue create_complex_advs failed")
        await bot.send_message(
            callback.message.chat.id,
            f"Не удалось поставить задачу: {e}",
        )
    finally:
        await state.clear()
    # После старта создания РК меню магазина не показываем — только сообщение об очереди.


@router.callback_query(callbacks.ConnectExistingCreateBoth.filter())
async def connect_existing_create_both_stale_session(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingCreateBoth,
    bot: Bot,
) -> None:
    """Ответ на устаревшую inline-кнопку «создать обе» вне FSM waiting_confirm_create_both.

    Регистрируется после stateful-хендлера: при валидном state срабатывает он;
    иначе пользователь получает явный текст вместо «Update is not handled».
    """
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    if callback_data.action == "cancel":
        _ = await bot.send_message(chat_id, "Отменено.")
        return
    _ = await bot.send_message(
        chat_id,
        "Сессия подключения кампаний истекла. Откройте магазин и начните "
        "«Подключить существующие» заново — не нажимайте старую кнопку в истории чата.",
    )


@router.callback_query(
    StateFilter(ConnectExistingAdvsStates.waiting_confirm_continue_invalid),
    callbacks.ConnectExistingContinueDespiteInvalid.filter(),
)
async def connect_existing_continue_despite_invalid(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingContinueDespiteInvalid,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Продолжить создание при наличии только авто без поиска: деактивация старых + create_complex_advs (hard_mode)."""
    if callback.message is None:
        return
    if callback_data.action == "cancel":
        data = await state.get_data()
        wb_user_cabinet_original_id = data.get("wb_user_cabinet_original_id")
        await state.clear()
        if wb_user_cabinet_original_id is not None:
            await ShopMenu(
                bot,
                int(callback.message.chat.id),
                state,
                wb_user_cabinet_original_id,
            )()
        else:
            await bot.send_message(callback.message.chat.id, "Отменено.")
        return
    data = await state.get_data()
    nmid = data.get("nmid")
    shop_id = data.get("shop_id")
    auto_candidates: list[CampaignData] = data.get("auto_candidates") or []
    existing_auto_id_from_state = data.get("existing_auto_id")
    if nmid is None or shop_id is None:
        await bot.send_message(
            callback.message.chat.id, "Данные сессии потеряны. Начните заново."
        )
        return
    if auto_candidates:
        existing_auto_adv_id = int(auto_candidates[0]["id"])
    elif existing_auto_id_from_state is not None:
        existing_auto_adv_id = int(existing_auto_id_from_state)
    else:
        await bot.send_message(callback.message.chat.id, "Нет данных об авто-кампании.")
        return
    try:
        from arq import create_pool
        from app.arq_workers.arq_redis_settings import arq_redis_settings

        redis_task_pool = await create_pool(arq_redis_settings)
        await redis_task_pool.enqueue_job(
            "create_search_only",
            nmid,
            shop_id,
            existing_auto_adv_id,
            callback.from_user.id,
        )
        await bot.send_message(
            callback.message.chat.id,
            "Задача на создание поисковой РК добавлена в очередь. Ожидайте уведомления.",
        )
    except Exception as e:
        logger.exception(
            "connect_existing enqueue create_search_only (continue despite invalid) failed"
        )
        await bot.send_message(
            callback.message.chat.id,
            f"Не удалось поставить задачу: {e}",
        )
    finally:
        await state.clear()
    # После старта создания поисковой РК меню магазина не показываем.


@router.callback_query(callbacks.ConnectExistingChangeNmid.filter())
async def connect_existing_change_nmid(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingChangeNmid,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Снова запросить артикул (например, при уже подключённых к этому nm id РК)."""
    if callback.message is None:
        return
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.clear()
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(ConnectExistingAdvsStates.waiting_nmid)
    await bot.send_message(
        callback.message.chat.id,
        "Введите артикул WB товара — одно число, больше 0:",
    )


@router.callback_query(callbacks.ConnectExistingAdvsBackToShop.filter())
async def connect_existing_advs_back_to_shop(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingAdvsBackToShop,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Вернуться в меню магазина из сценария «подключить существующие» (уже есть РК или отмена)."""
    await state.clear()
    if callback.message is None:
        return
    await ShopMenu(
        bot,
        int(callback.message.chat.id),
        state,
        callback_data.wb_user_cabinet_original_id,
    )()
