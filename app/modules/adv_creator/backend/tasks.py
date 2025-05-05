import logging

from arq import Retry

from app.client_bot import const
from app.client_bot.bot import get_bot
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.mixins.excs import AdvNotFoundInWBError
from app.modules.adv_creator.backend import MainAdvManager, CardsNotFoundForShopError
from app.modules.adv_creator.backend.exc import (
    NotEnoughBalanceOnShopError,
    StartComplexAdvError,
)
from app.modules.common_slaves.wildberries import super_cabinet_manager

logger = logging.getLogger(__name__)


async def create_complex_advs(
    ctx, nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int
) -> None:
    try:
        await _create_complex_advs(ctx, nmid, shop_id, hard_mode, user_telegram_id)
    except ApiForbiddenError:
        bot = get_bot()
        await bot.send_message(
            user_telegram_id,
            f"Нет токенов с нужными правами."
            f" Обратитесь в поддержку {const.SUPPORT_LINK}",
        )
        return
    except Exception:
        delay = 1
        logger.error(
            f"Ошибка задачи create_complex_advs, повтор через {delay} сек",
            exc_info=True,
        )
        raise Retry(defer=delay)


async def _create_complex_advs(
    ctx, nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int
) -> None:
    bot = ctx["bot"]
    access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
    manager = MainAdvManager(access)
    await bot.send_message(
        user_telegram_id, f"Создаю комплексную кампанию для артикула {nmid}"
    )
    try:
        auto_adv_id, search_adv_id = await manager.create_complex_advs(
            bot, user_telegram_id, nmid, hard_mode
        )

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

    except AdvNotFoundInWBError as exc:
        auto_adv_id = exc.auto_adv_id
        await bot.send_message(
            user_telegram_id,
            f"Не удалось правильно настроить авто-РК для {nmid}, "
            f"ID Авто {auto_adv_id} не найден после создания. Попробуйте "
            f"самостоятельно найти нет ли новой РК в кабинете WB и "
            f"обратитесь в поддержку -> {const.SUPPORT_LINK}",
        )

    except StartComplexAdvError as exc:
        auto_adv_id = exc.auto_adv_id
        search_adv_id = exc.search_adv_id
        await bot.send_message(
            user_telegram_id,
            f"Произошла ошибка при попытке запустить РК (Авто - {auto_adv_id} "
            f"и Аукцион - {search_adv_id}) проверьте"
            f" самостоятельно запустились ли кампании и правильность их создания,"
            f" а также при необходимости обратитесь в поддержку -> {const.SUPPORT_LINK}",
        )
