"""Подключение существующих рекламных кампаний WB к артикулу (NM-id)."""

import logging

from aiohttp import ClientSession
from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.client_bot.user_interface.states import ConnectExistingAdvsStates
from app.client_bot.user_interface.views import callbacks
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.mixins.excs import CardNotFoundInWB
from app.core.mp.wb.api.excs import BadRequestError
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.connect_existing_advs import get_connect_existing_candidates
from app.modules.connect_existing_advs.candidates_service import (
    ConnectExistingCandidatesResult,
)
from app.modules.shop_runner.modules.wb_api import WBApi
from app.utils.db.session_maker import get_async_session_maker as sm

from app.modules.shop_menu.message import ShopMenu

logger = logging.getLogger(__name__)

DONE_STATUS = "done"

WB_WAIT_MESSAGE = "Идёт обращение к Wildberries, пожалуйста подождите."


async def _get_existing_adv_pair_not_done(
    wb_cabinet_id: int, nmid: int
) -> tuple[int | None, int | None] | None:
    """Если есть в БД пара РК (Аукцион + Авто) по артикулу не в done — вернуть (adv_id, search_adv_id), иначе None."""
    async with sm(read_only=True) as session:
        stmt = select(AdvSetting)\
            .options(load_only(AdvSetting.adv_id, AdvSetting._search_adv_id, AdvSetting.name))\
            .where(
            AdvSetting.wb_cabinet_id == wb_cabinet_id,
            AdvSetting.nmids == [nmid],
            AdvSetting.active_status != DONE_STATUS,
        ).limit(1)
        result = await session.execute(stmt)
        adv = result.scalars().one_or_none()
    if adv is None:
        return None
    return adv.adv_id, adv.search_adv_id

router = Router()


def _serialize_candidates(result: ConnectExistingCandidatesResult) -> tuple[list[dict], list[dict]]:
    """Serialize candidates for FSM state (id, name)."""
    auction = [{"id": c.id, "name": c.settings.name} for c in result.auction_candidates]
    auto = [{"id": c.id, "name": c.settings.name} for c in result.auto_candidates]
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


@router.message(StateFilter(ConnectExistingAdvsStates.waiting_nmid))
async def connect_existing_advs_nmid(
    message: Message,
    bot: Bot,
    state: FSMContext,
    client_session: ClientSession,
) -> None:
    """Принять NM-id, проверить карточку на WB, получить кандидатов, показать первый тип (аукцион)."""
    if message.text is None:
        await bot.send_message(message.chat.id, "Отправьте Артикул WB товара числом.")
        return
    text = message.text.strip()
    try:
        nmid = int(text)
    except ValueError:
        await bot.send_message(message.chat.id, "Артикул WB товара должен быть целым числом.")
        return
    if nmid <= 0:
        await bot.send_message(message.chat.id, "Артикул WB товара  должен быть больше 0.")
        return

    data = await state.get_data()
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
        access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
        wb_api = WBApi(access, client_session)
        card = await wb_api.get_card_by_text(nmid)
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
            message.chat.id,
            "Артикул не найден на Wildberries. Проверьте NM-id и магазин.\n\n"
            "Вы по-прежнему в режиме «Подключить существующие». Введите другой Артикул WB товара (одно число) или нажмите кнопку ниже.",
            reply_markup=keyboard,
        )
        return
    except ApiForbiddenError:
        await bot.send_message(
            message.chat.id,
            "Нет доступа к API WB. Проверьте токены магазина.",
        )
        return

    existing_pair = await _get_existing_adv_pair_not_done(wb_cabinet_id, nmid)
    # Блокируем только если уже есть обе РК (Аукцион и Авто). Иначе продолжаем и подставим имеющуюся.
    if existing_pair is not None:
        existing_auto_id, existing_auction_id = existing_pair
        if existing_auto_id is not None and existing_auction_id is not None:
            ids_text = f"Аукцион: {existing_auction_id}, Авто: {existing_auto_id}"
            await state.clear()
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
                message.chat.id,
                f"Для этого артикула уже есть подключённые РК (Аукцион и Авто). "
                f"ID кампаний: {ids_text}. Отмените создание и вернитесь в меню магазина.",
                reply_markup=keyboard,
            )
            return
        # Одна РК есть — сохраняем в state, дальше подставим её и создадим/выберем недостающую
        await state.update_data(
            existing_auto_id=existing_auto_id,
            existing_auction_id=existing_auction_id,
            card_name=card.name,
        )

    try:
        candidates_result = await get_connect_existing_candidates(shop_id, nmid)
        logger.info(
            "connect_existing candidates for nmid=%s shop_id=%s: auction=%s auto=%s",
            nmid,
            shop_id,
            len(candidates_result.auction_candidates),
            len(candidates_result.auto_candidates),
        )
    except ApiForbiddenError:
        await bot.send_message(
            message.chat.id,
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
                message.chat.id,
                "Ошибка запроса к WB. Попробуйте позже или обратитесь в поддержку.",
            )
            return
    except Exception as e:
        logger.exception("connect_existing get_candidates failed")
        await bot.send_message(
            message.chat.id,
            "Ошибка при получении списка кампаний. Попробуйте позже или обратитесь в поддержку.",
        )
        return

    auction_list, auto_list = _serialize_candidates(candidates_result)
    await state.update_data(
        nmid=nmid,
        wb_cabinet_id=wb_cabinet_id,
        shop_id=shop_id,
        card_name=card.name,
        auction_candidates=auction_list,
        auto_candidates=auto_list,
        chosen_auction_adv_id=None,
        chosen_auto_adv_id=None,
    )

    # Только авто без поиска — не считаем валидными; предлагаем продолжить создание (деактивация старых + create)
    if not auction_list and auto_list:
        await state.set_state(ConnectExistingAdvsStates.waiting_confirm_continue_invalid)
        lines = [
            "Без подключённой поисковой РК кампания не считается валидной.",
            "",
            "Для этого артикула найдены кампании без поиска (не валидные):",
            "",
        ]
        for a in auto_list:
            lines.append(f"- Авто-РК: {a['id']}, Поисковая РК: не указана")
        lines.extend([
            "",
            "Если вы уверены, что эти кампании не активны, вы можете продолжить создание новой кампании, "
            "нажав на кнопку «✅ Продолжить создание». В случае продолжения уже существующие кампании "
            "будут деактивированы в боте во избежание конфликтов и излишних расходов.",
        ])
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Продолжить создание",
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
        await bot.send_message(
            message.chat.id,
            "\n".join(lines),
            reply_markup=kb,
        )
        return

    # Обе отсутствуют — предложить создать обе через create_complex_advs
    if not auction_list and not auto_list:
        await state.set_state(ConnectExistingAdvsStates.waiting_confirm_create_both)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Да, создать обе",
                        callback_data=callbacks.ConnectExistingCreateBoth(action="confirm").pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Нет",
                        callback_data=callbacks.ConnectExistingCreateBoth(action="cancel").pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            message.chat.id,
            f"Кампании для артикула {nmid} не найдены. Создать обе (аукцион + авто)?",
            reply_markup=kb,
        )
        return

    # Если в БД уже есть аукцион по этому артикулу — переходим сразу к шагу 2 (авто)
    data_after = await state.get_data()
    existing_auction_id = data_after.get("existing_auction_id")
    if existing_auction_id:
        await state.update_data(chosen_auction_adv_id=existing_auction_id)
        await state.set_state(ConnectExistingAdvsStates.confirm_type2)
        auto_candidates_skip: list[dict] = data_after.get("auto_candidates") or []
        kb_rows: list[list[InlineKeyboardButton]] = []
        if auto_candidates_skip:
            first_auto = auto_candidates_skip[0]
            kb_rows.append(
                [
                    InlineKeyboardButton(
                        text="Подтвердить",
                        callback_data=callbacks.ConnectExistingConfirmType2(
                            adv_id=first_auto["id"]
                        ).pack(),
                    )
                ]
            )
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text="Создать РК",
                    callback_data=callbacks.ConnectExistingConfirmType2(adv_id=0).pack(),
                )
            ]
        )
        await bot.send_message(
            message.chat.id,
            "Аукционная РК уже подключена. Выберите авто-кампанию или создайте новую:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        )
        return

    # Шаг 1: показать тип 1 (аукцион)
    await state.set_state(ConnectExistingAdvsStates.confirm_type1)
    if auction_list:
        first = auction_list[0]
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Подтвердить",
                        callback_data=callbacks.ConnectExistingConfirmType1(adv_id=first["id"]).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Создать РК",
                        callback_data=callbacks.ConnectExistingConfirmType1(adv_id=0).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            message.chat.id,
            f"Найдена поисковая (аукцион) кампания: «{first['name']}» (ID {first['id']}). Подтвердить или создать новую?",
            reply_markup=kb,
        )
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Создать РК",
                        callback_data=callbacks.ConnectExistingConfirmType1(adv_id=0).pack(),
                    )
                ],
            ]
        )
        await bot.send_message(
            message.chat.id,
            "Поисковая (аукцион) кампания для этого артикула не найдена. Создать?",
            reply_markup=kb,
        )


@router.callback_query(
    StateFilter(ConnectExistingAdvsStates.confirm_type1),
    callbacks.ConnectExistingConfirmType1.filter(),
)
async def connect_existing_confirm_type1(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingConfirmType1,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Подтверждение/создание по первому типу (аукцион) → показать второй тип (авто)."""
    await callback.answer()
    if callback.message is None:
        return
    data = await state.get_data()
    chosen_auction = callback_data.adv_id if callback_data.adv_id else None  # 0 = создать
    await state.update_data(chosen_auction_adv_id=chosen_auction)
    if chosen_auction is None:
        # TODO (todo 4): создать аукционную РК
        await bot.send_message(
            callback.message.chat.id,
            "Создание аукционной РК будет доступно в следующем обновлении. Пока выберите существующую.",
        )
        return

    auto_candidates: list[dict] = data.get("auto_candidates") or []
    await state.set_state(ConnectExistingAdvsStates.confirm_type2)

    kb_rows_type2: list[list[InlineKeyboardButton]] = []
    if auto_candidates:
        first = auto_candidates[0]
        kb_rows_type2.append(
            [
                InlineKeyboardButton(
                    text="Подтвердить",
                    callback_data=callbacks.ConnectExistingConfirmType2(
                        adv_id=first["id"]
                    ).pack(),
                )
            ]
        )
    kb_rows_type2.append(
        [
            InlineKeyboardButton(
                text="Создать РК",
                callback_data=callbacks.ConnectExistingConfirmType2(adv_id=0).pack(),
            )
        ]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows_type2)
    if auto_candidates:
        first = auto_candidates[0]
        await bot.send_message(
            callback.message.chat.id,
            f"Найдена авто-кампания: «{first['name']}» (ID {first['id']}). Подтвердить или создать новую?",
            reply_markup=kb,
        )
    else:
        await bot.send_message(
            callback.message.chat.id,
            "Авто-кампания для этого артикула не найдена. Создать?",
            reply_markup=kb,
        )


@router.callback_query(
    StateFilter(ConnectExistingAdvsStates.confirm_type2),
    callbacks.ConnectExistingConfirmType2.filter(),
)
async def connect_existing_confirm_type2(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingConfirmType2,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Подтверждение/создание по второму типу (авто) → сохранить в AdvSetting."""
    await callback.answer()
    if callback.message is None:
        return
    data = await state.get_data()
    chosen_auto = callback_data.adv_id if callback_data.adv_id else None
    if chosen_auto is None:
        # TODO (todo 4): создать авто РК
        await bot.send_message(
            callback.message.chat.id,
            "Создание авто-РК будет доступно в следующем обновлении. Пока выберите существующую.",
        )
        return

    chosen_auction = data.get("chosen_auction_adv_id")
    nmid = data["nmid"]
    wb_cabinet_id = data["wb_cabinet_id"]
    shop_id = data.get("shop_id")
    if chosen_auction is None:
        await bot.send_message(
            callback.message.chat.id,
            "Сначала выберите или создайте аукционную кампанию.",
        )
        return

    card_name = data.get("card_name")
    if not card_name and shop_id:
        try:
            access = await super_cabinet_manager.get_access_for_wb_cabinet(
                wb_cabinet_id
            )
            async with ClientSession() as client_session:
                wb_api = WBApi(access, client_session)
                card = await wb_api.get_card_by_text(nmid)
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

    if shop_id:
        try:
            from app.core.di.app_container import AppContainer
            from app.core.di.di_manager import DIManager

            async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
                factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
                hub = factory.get_wb_manager_hub(shop_id)
                pm = hub.wb_data_manager.promotion_manager
                await pm.rename_campaign(chosen_auto, auto_name[:100])
                await pm.rename_campaign(chosen_auction, auction_name[:100])
        except Exception as e:
            logger.exception("connect_existing rename_campaign failed")
            await bot.send_message(
                callback.message.chat.id,
                "Кампании подключены в боте, но переименование на WB не удалось. "
                "Проверьте названия в кабинете WB.",
            )

    from app.client_bot.modules.default_settings import apply_defaults_to_adv_setting

    async with sm(read_only=False) as session:
        wb_cabinet = await session.get(WBCabinet, wb_cabinet_id)
        if wb_cabinet is None:
            await bot.send_message(callback.message.chat.id, "Кабинет не найден.")
            return
        stmt = select(AdvSetting).where(
            AdvSetting.wb_cabinet_id == wb_cabinet_id,
            AdvSetting.nmids == [nmid],
        ).limit(1)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.adv_id = chosen_auto
            existing._search_adv_id = chosen_auction
            existing.name = complex_adv_name
            existing.active_status = "9"
            existing.type = 8
            existing.nmids = [nmid]
            apply_defaults_to_adv_setting(existing, wb_cabinet)
            logger.info(
                "connect_existing updated existing AdvSetting id=%s nmid=%s auction=%s auto=%s",
                existing.id,
                nmid,
                chosen_auction,
                chosen_auto,
            )
        else:
            adv_setting = AdvSetting(
                adv_id=chosen_auto,
                name=complex_adv_name,
                wb_cabinet_id=wb_cabinet_id,
                nmids=[nmid],
                active_status="9",
                type=8,
                _search_adv_id=chosen_auction,
            )
            apply_defaults_to_adv_setting(adv_setting, wb_cabinet)
            session.add(adv_setting)
            logger.info(
                "connect_existing created new AdvSetting nmid=%s wb_cabinet_id=%s auction=%s auto=%s",
                nmid,
                wb_cabinet_id,
                chosen_auction,
                chosen_auto,
            )
        await session.commit()
    await state.clear()
    await bot.send_message(
        callback.message.chat.id,
        f"Кампании подключены для артикула {nmid}. Аукцион: {chosen_auction}, Авто: {chosen_auto}.",
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
    await callback.answer()
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
        await bot.send_message(callback.message.chat.id, "Данные сессии потеряны. Начните заново.")
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
    await callback.answer()
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
        await bot.send_message(callback.message.chat.id, "Данные сессии потеряны. Начните заново.")
        return
    try:
        from arq import create_pool
        from app.arq_workers.arq_redis_settings import arq_redis_settings

        redis_task_pool = await create_pool(arq_redis_settings)
        await redis_task_pool.enqueue_job(
            "create_complex_advs",
            nmid,
            shop_id,
            True,  # hard_mode: деактивировать существующие в боте и создать новые
            callback.from_user.id,
        )
        await bot.send_message(
            callback.message.chat.id,
            "Задача на создание кампаний добавлена в очередь. Существующие кампании по этому артикулу будут деактивированы в боте. Ожидайте уведомления.",
        )
    except Exception as e:
        logger.exception("connect_existing enqueue create_complex_advs (continue despite invalid) failed")
        await bot.send_message(
            callback.message.chat.id,
            f"Не удалось поставить задачу: {e}",
        )
    finally:
        await state.clear()


@router.callback_query(callbacks.ConnectExistingAdvsBackToShop.filter())
async def connect_existing_advs_back_to_shop(
    callback: CallbackQuery,
    callback_data: callbacks.ConnectExistingAdvsBackToShop,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Вернуться в меню магазина из сценария «подключить существующие» (уже есть РК или отмена)."""
    await callback.answer()
    await state.clear()
    if callback.message is None:
        return
    await ShopMenu(
        bot,
        int(callback.message.chat.id),
        state,
        callback_data.wb_user_cabinet_original_id,
    )()
