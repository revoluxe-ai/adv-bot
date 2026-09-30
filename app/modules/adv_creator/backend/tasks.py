import logging
import traceback
from typing import Any

import aiohttp

from app.client_bot import const
from app.client_bot.bot import get_bot
from app.core.di import DIManager
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.mixins.excs import AdvNotFoundInWBError, CardNotFoundInWB
from app.modules.adv_creator.backend import CardsNotFoundForShopError, MainAdvManager
from app.shared.domains.wb.exceptions import NotEnoughBalanceOnShopError
from app.core.mp.wb.api.excs import HttpTimeOutError, MaxAttemptsError
from app.modules.adv_creator.backend.exc import (
    AdvExistsForNmidError,
)
from app.core.di.app_container import AppContainer
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.wb_adv_updater import data_manager
from app.settings import settings

logger = logging.getLogger(__name__)


async def _send_user_message_best_effort(
    bot: Any,
    user_telegram_id: int,
    text: str,
    *,
    log_context: str,
    **send_kwargs: Any,
) -> None:
    """Отправить пользователю статус; сбой Telegram/прокси не прерывает ARQ-задачу.

    Args:
        bot: aiogram Bot из ctx воркера.
        user_telegram_id: Telegram id пользователя.
        text: Текст сообщения.
        log_context: Короткая метка для логов (имя задачи/шага).
        send_kwargs: Аргументы для ``bot.send_message`` (например disable_web_page_preview).
    """
    try:
        _ = await bot.send_message(user_telegram_id, text, **send_kwargs)
    except Exception:
        logger.warning(
            "Не удалось отправить Telegram-уведомление пользователю; задача продолжается",
            exc_info=True,
            extra={"log_context": log_context, "user_telegram_id": user_telegram_id},
        )


async def _notify_unknown_task_error(
    *,
    bot: Any,
    user_telegram_id: int,
    task_name: str,
    context_data: dict[str, Any],
) -> None:
    user_text = (
        "Произошла ошибка, но не волнуйтесь! Бот продолжает работать "
        "и по прежнему выполняет свои функции. Проблема только в интерфейсе, а администратор"
        " уже уведомлен о ней. Попробуйте выполнить нужное вам действие еще раз или вернитесь"
        " в главное меню, через команду /start . Связаться с разработчиком вы можете по "
        f"этому контакту: {const.SUPPORT_LINK}"
    )
    await bot.send_message(user_telegram_id, user_text)

    trace_error = traceback.format_exc()
    context_text = (
        f"ARQ task failed: {task_name}\n"
        f"user_telegram_id: {user_telegram_id}\n"
        f"context: {context_data}\n\n"
    )
    admin_text = context_text + trace_error
    for admin_telegram_id in set(const.ADMINS):
        part = admin_text
        while part:
            chunk = part[: const.MAX_MESSAGE_LENGTH]
            await bot.send_message(admin_telegram_id, chunk)
            part = part[const.MAX_MESSAGE_LENGTH :]


async def create_search_only(
    ctx: dict[str, Any],
    nmid: int,
    shop_id: str,
    existing_auto_adv_id: int,
    user_telegram_id: int,
) -> None:
    async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
        try:
            await _create_search_only(
                ctx, nmid, shop_id, existing_auto_adv_id, user_telegram_id
            )
        except ApiForbiddenError:
            bot = get_bot()
            await bot.send_message(
                user_telegram_id,
                f"Нет токенов с нужными правами. Обратитесь в поддержку {const.SUPPORT_LINK}",
            )
            return
        except Exception as e:
            logger.error(
                "Ошибка задачи create_search_only",
                exc_info=True,
            )
            bot = get_bot()
            try:
                await _notify_unknown_task_error(
                    bot=bot,
                    user_telegram_id=user_telegram_id,
                    task_name="create_search_only",
                    context_data={
                        "nmid": nmid,
                        "shop_id": shop_id,
                        "existing_auto_adv_id": existing_auto_adv_id,
                    },
                )
            except Exception:
                logger.exception(
                    "Ошибка отправки уведомлений по unknown error create_search_only"
                )
            raise e


async def _create_search_only(
    ctx: dict[str, Any],
    nmid: int,
    shop_id: str,
    existing_auto_adv_id: int,
    user_telegram_id: int,
) -> None:
    from app.modules.shop_runner.modules.wb_api import WBApi

    bot = ctx["bot"]
    client_session = ctx["client_session"]
    access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
    manager = MainAdvManager(access, client_session)

    try:
        card_ready = await data_manager.ensure_card_in_db(shop_id, nmid)
    except CardNotFoundInWB:
        await bot.send_message(
            user_telegram_id,
            f"Карточка с артикулом {nmid} не найдена на Wildberries,"
            f" проверьте правильность артикула!",
        )
        return
    if not card_ready:
        await bot.send_message(
            user_telegram_id,
            f"Не удалось дождаться загрузки карточки {nmid} в базу. Попробуйте позже.",
        )
        return

    async with aiohttp.ClientSession() as client_session:
        wb_api = WBApi(access, client_session)
        await data_manager.update_advs_data_from_wb_to_pg(wb_api)

    await bot.send_message(
        user_telegram_id,
        "Создаю поисковую РК и подключаю к существующей авто-кампании.",
    )
    try:
        search_adv_id = await manager.create_search_only(
            bot, user_telegram_id, nmid, existing_auto_adv_id, hard_mode=True
        )
        await bot.send_message(
            user_telegram_id,
            f"Поисковая РК создана и подключена к авто-кампании. ID поиска: {search_adv_id}",
        )
    except CardsNotFoundForShopError:
        await bot.send_message(
            user_telegram_id,
            f"Карточка с артикулом {nmid} не найдена на Wildberries,"
            f" проверьте правильность артикула!",
        )
    except NotEnoughBalanceOnShopError as exc:
        adv_id = getattr(exc, "adv_id", None)
        await bot.send_message(
            user_telegram_id,
            f"Недостаточно средств на балансе shop id: {shop_id}"
            f" для пополнения РК для артикула {nmid}"
            + (f" ADV ID: {adv_id}" if adv_id is not None else ""),
        )
    except (HttpTimeOutError, MaxAttemptsError):
        await bot.send_message(
            user_telegram_id,
            f"Не удалось выполнить запрос к Wildberries (таймаут или превышено число попыток). "
            f"Попробуйте повторить позже или обратитесь в поддержку {const.SUPPORT_LINK}",
        )


async def create_auto_only(
    ctx: dict[str, Any],
    nmid: int,
    shop_id: str,
    existing_search_adv_id: int,
    user_telegram_id: int,
) -> None:
    async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
        try:
            await _create_auto_only(
                ctx, nmid, shop_id, existing_search_adv_id, user_telegram_id
            )
        except ApiForbiddenError:
            bot = get_bot()
            await bot.send_message(
                user_telegram_id,
                f"Нет токенов с нужными правами. Обратитесь в поддержку {const.SUPPORT_LINK}",
            )
            return
        except Exception as e:
            logger.error(
                "Ошибка задачи create_auto_only",
                exc_info=True,
            )
            bot = get_bot()
            try:
                await _notify_unknown_task_error(
                    bot=bot,
                    user_telegram_id=user_telegram_id,
                    task_name="create_auto_only",
                    context_data={
                        "nmid": nmid,
                        "shop_id": shop_id,
                        "existing_search_adv_id": existing_search_adv_id,
                    },
                )
            except Exception:
                logger.exception(
                    "Ошибка отправки уведомлений по unknown error create_auto_only"
                )
            raise e


async def _create_auto_only(
    ctx: dict[str, Any],
    nmid: int,
    shop_id: str,
    existing_search_adv_id: int,
    user_telegram_id: int,
) -> None:
    from app.modules.shop_runner.modules.wb_api import WBApi

    bot = ctx["bot"]
    client_session = ctx["client_session"]
    access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
    manager = MainAdvManager(access, client_session)

    try:
        card_ready = await data_manager.ensure_card_in_db(shop_id, nmid)
    except CardNotFoundInWB:
        await bot.send_message(
            user_telegram_id,
            f"Карточка с артикулом {nmid} не найдена на Wildberries,"
            f" проверьте правильность артикула!",
        )
        return
    if not card_ready:
        await bot.send_message(
            user_telegram_id,
            f"Не удалось дождаться загрузки карточки {nmid} в базу. Попробуйте позже.",
        )
        return

    async with aiohttp.ClientSession() as client_session:
        wb_api = WBApi(access, client_session)
        await data_manager.update_advs_data_from_wb_to_pg(wb_api)

    await bot.send_message(
        user_telegram_id,
        "Создаю авто-РК и подключаю к существующей поисковой.",
    )
    try:
        auto_adv_id = await manager.create_auto_only(
            bot, user_telegram_id, nmid, existing_search_adv_id, hard_mode=True
        )
        await bot.send_message(
            user_telegram_id,
            f"Авто-РК создана и подключена. ID авто: {auto_adv_id}",
        )
    except CardsNotFoundForShopError:
        await bot.send_message(
            user_telegram_id,
            f"Карточка с артикулом {nmid} не найдена на Wildberries,"
            f" проверьте правильность артикула!",
        )
    except NotEnoughBalanceOnShopError as exc:
        adv_id = getattr(exc, "adv_id", None)
        await bot.send_message(
            user_telegram_id,
            f"Недостаточно средств на балансе shop id: {shop_id}"
            f" для пополнения РК для артикула {nmid}"
            + (f" ADV ID: {adv_id}" if adv_id is not None else ""),
        )
    except (HttpTimeOutError, MaxAttemptsError):
        await bot.send_message(
            user_telegram_id,
            f"Не удалось выполнить запрос к Wildberries (таймаут или превышено число попыток). "
            f"Попробуйте повторить позже или обратитесь в поддержку {const.SUPPORT_LINK}",
        )


async def create_complex_advs(
    ctx: dict[str, Any], nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int
) -> None:
    # TODO: Тут ошибка попала в прод: отсутствие импорта
    async with await DIManager.create(AppContainer):  # type:ignore[attr-defined]
        try:
            await _create_complex_advs(ctx, nmid, shop_id, hard_mode, user_telegram_id)
        except ApiForbiddenError:
            bot = get_bot()
            await bot.send_message(
                user_telegram_id,
                f"Нет токенов с нужными правами. Обратитесь в поддержку {const.SUPPORT_LINK}",
            )
            return
        except Exception as e:
            logger.error(
                "Ошибка задачи create_complex_advs",
                exc_info=True,
            )
            bot = get_bot()
            try:
                await _notify_unknown_task_error(
                    bot=bot,
                    user_telegram_id=user_telegram_id,
                    task_name="create_complex_advs",
                    context_data={
                        "nmid": nmid,
                        "shop_id": shop_id,
                        "hard_mode": hard_mode,
                    },
                )
            except Exception:
                logger.exception(
                    "Ошибка отправки уведомлений по unknown error create_complex_advs"
                )
            raise e


async def _create_complex_advs(
    ctx: dict[str, Any], nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int
) -> None:
    from app.modules.shop_runner.modules.wb_api import WBApi

    bot = ctx["bot"]
    client_session = ctx["client_session"]
    access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
    manager = MainAdvManager(access, client_session)

    try:
        card_ready = await data_manager.ensure_card_in_db(shop_id, nmid)
    except CardNotFoundInWB:
        await bot.send_message(
            user_telegram_id,
            f"Карточка с артикулом {nmid} не найдена на Wildberries,"
            f"проверьте правильность артикула!",
        )
        return
    if not card_ready:
        await bot.send_message(
            user_telegram_id,
            f"Не удалось дождаться загрузки карточки {nmid} в базу. Попробуйте позже.",
        )
        return

    async with aiohttp.ClientSession() as client_session:
        wb_api = WBApi(access, client_session)
        await data_manager.update_advs_data_from_wb_to_pg(wb_api)

    await _send_user_message_best_effort(
        bot,
        user_telegram_id,
        f"Создаю комплексную кампанию для артикула {nmid}",
        log_context="create_complex_advs.progress",
    )
    try:
        result = await manager.create_complex_advs(
            bot, user_telegram_id, nmid, hard_mode
        )
        if not result:
            return None
        auto_adv_id, search_adv_id = result

        await _send_user_message_best_effort(
            bot,
            user_telegram_id,
            f"Комплексная кампания для артикула {nmid} создана,"
            f" ID Авто-РК: {auto_adv_id},"
            f" ID Поисковой РК: {search_adv_id}"
            f" Проверьте: нет ли в Авто-кампании"
            f" артикулов больше, чем должно быть. "
            f"Если это так, то пожалуйста, удалите"
            f" лишние артикулы сами и сообщите "
            f"об этом инциденте в поддержку {const.SUPPORT_LINK}  Спасибо!",
            log_context="create_complex_advs.success",
            disable_web_page_preview=True,
        )
    except CardsNotFoundForShopError:
        await bot.send_message(
            user_telegram_id,
            f"Карточка с артикулом {nmid} не найдена на Wildberries,"
            f"проверьте правильность артикула!",
        )

    except NotEnoughBalanceOnShopError as exc:
        adv_id = exc.adv_id
        await bot.send_message(
            user_telegram_id,
            f"Недостаточно средств на балансе shop id: {shop_id}"
            f" для пополнения РК для артикула {nmid} "
            f"ADV ID кампанию, которую не смогли пополнить: {adv_id}",
        )
        del exc

    except AdvNotFoundInWBError as exc:
        assert exc.auto_adv_id is not None
        auto_adv_id = exc.auto_adv_id
        await bot.send_message(
            user_telegram_id,
            f"Не удалось правильно настроить авто-РК для {nmid}, "
            f"ID Авто {auto_adv_id} не найден после создания. Попробуйте "
            f"самостоятельно найти нет ли новой РК в кабинете WB и "
            f"обратитесь в поддержку -> {const.SUPPORT_LINK}",
        )
        del exc

    except (HttpTimeOutError, MaxAttemptsError):
        await bot.send_message(
            user_telegram_id,
            f"Не удалось выполнить запрос к Wildberries (таймаут или превышено число попыток). "
            f"Попробуйте повторить позже или обратитесь в поддержку {const.SUPPORT_LINK}",
        )
        return

    except AdvExistsForNmidError as exc:
        # Отправить сообщение с кнопками выбора
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        from ..telegram.into_callback import ConfirmCreateComplexAdv

        exist_adv_ids_rows = (
            exc.exist_adv_ids_rows
        )  # Список кортежей (auto_id, search_id | None)
        message = "Найдены существующие кампании для этого артикула:\n"
        message += (
            "".join(
                f"- Авто-РК: {auto_id}, Поисковая РК: {search_id if search_id else 'не указана'}\n"
                for auto_id, search_id in exist_adv_ids_rows
            )
            + "\n"
        )

        message += (
            "Если вы уверены, что эти кампании не активны, то вы можете продолжить создание новой кампании,"
            " нажав на кнопку '✅ Продолжить создание'. В случае продолжения уже существующие кампании "
            " будут деактивированы в боте во избежание конфликтов и излишних расходов.\n\n"
        )

        builder = InlineKeyboardBuilder()
        if access.wb_cabinet is None:
            raise ValueError("У доступа не установлен магазин")
        wb_original_cabinet_id = access.wb_cabinet.id
        assert isinstance(wb_original_cabinet_id, int)
        builder.row(
            InlineKeyboardButton(
                text="✅ Продолжить создание",
                callback_data=ConfirmCreateComplexAdv(
                    action="continue",
                    nmid=nmid,
                    wb_cabinet_original_id=wb_original_cabinet_id,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=ConfirmCreateComplexAdv(
                    action="cancel",
                    nmid=nmid,
                    wb_cabinet_original_id=wb_original_cabinet_id,
                ).pack(),
            ),
        )

        await bot.send_message(
            user_telegram_id, message, reply_markup=builder.as_markup()
        )
        return None
