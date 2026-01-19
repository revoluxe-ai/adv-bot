import logging
from typing import Any

import aiohttp

from app.client_bot import const
from app.client_bot.bot import get_bot
from app.core.di import DIManager
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.mixins.excs import AdvNotFoundInWBError
from app.modules.adv_creator.backend import CardsNotFoundForShopError, MainAdvManager
from app.shared.domains.wb.exceptions import NotEnoughBalanceOnShopError
from app.modules.adv_creator.backend.exc import (
    AdvExistsForNmidError,
)
from app.core.di.app_container import AppContainer
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.wb_adv_updater import data_manager

logger = logging.getLogger(__name__)


async def create_complex_advs(
    ctx: dict[str, Any], nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int
) -> None:
    # TODO: Тут ошибка попала в прод: отсутствие импорта
    async with await DIManager.create(AppContainer): # type:ignore[attr-defined]
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

            raise e


async def _create_complex_advs(
    ctx: dict[str, Any], nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int
) -> None:
    from app.modules.shop_runner.modules.wb_api import WBApi

    bot = ctx["bot"]
    client_session = ctx["client_session"]
    access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
    manager = MainAdvManager(access, client_session)
    async with aiohttp.ClientSession() as client_session:
        wb_api = WBApi(access, client_session)
        await data_manager.update_advs_data_from_wb_to_pg(wb_api)

    await bot.send_message(
        user_telegram_id, f"Создаю комплексную кампанию для артикула {nmid}"
    )
    try:
        result = await manager.create_complex_advs(
            bot, user_telegram_id, nmid, hard_mode
        )
        if not result:
            return None
        auto_adv_id, search_adv_id = result

        await bot.send_message(
            user_telegram_id,
            f"Комплексная кампания для артикула {nmid} создана,"
            f" ID Авто-РК: {auto_adv_id},"
            f" ID Поисковой РК: {search_adv_id}"
            f" Проверьте: нет ли в Авто-кампании"
            f" артикулов больше, чем должно быть. "
            f"Если это так, то пожалуйста, удалите"
            f" лишние артикулы сами и сообщите "
            f"об этом инциденте в поддержку {const.SUPPORT_LINK}  Спасибо!",
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
