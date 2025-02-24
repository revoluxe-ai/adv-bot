import logging
from app.client_bot import const
from app.core.wb_api.mixins.excs import AdvNotFoundInWBError
from app.modules.adv_creator import backend
from app.modules.adv_creator.backend import MainAdvManager, CardsNotFoundForShopError
from arq import Retry
from app.modules.adv_creator.backend.exc import NotEnoughBalanceOnShopError, StartComplexAdvError

logger = logging.getLogger(__name__)


async def create_complex_advs(ctx, nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int):
    try:
        await _create_complex_advs(ctx, nmid, shop_id, hard_mode, user_telegram_id)
    except Exception:
        delay = 1
        logger.error(f'Ошибка задачи create_complex_advs, повтор через {delay} сек')
        raise Retry(defer=delay)



async def _create_complex_advs(ctx, nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int):
    bot = ctx["bot"]
    access = await backend.access_manager.get_access_for_wb_cabinet(shop_id)
    manager = MainAdvManager(access)
    await bot.send_message(user_telegram_id, f'Создаю комплексную кампанию для артикула {nmid}')
    try:
        auto_adv_id, search_adv_id =  await manager.create_complex_advs(bot,
                                                     user_telegram_id,
                                                     nmid,
                                                     hard_mode)

        await bot.send_message(user_telegram_id, f'Комплексная кампания для артикула {nmid} создана,'
                                                 f' ID Авто-РК: {auto_adv_id},'
                                                 f' ID Поисковой РК: {search_adv_id}'
                                                 f' Проверьте: нет ли в Авто-кампании артикулов больше, чем должно быть. '
                                                 f'Если это так, то пожалуйста, удалите лишние артикулы сами и сообщите '
                                                 f'об этом инциденте в поддержку {const.SUPPORT_LINK}  Спасибо!',
                                                disable_web_page_preview=True)
    except CardsNotFoundForShopError:
        await bot.send_message(user_telegram_id, f'Карточка с артикулом {nmid} не найдена на Wildberries,'
                                                 f'проверьте правильность артикула!')

    except NotEnoughBalanceOnShopError:
        await bot.send_message(user_telegram_id, 'Недостаточно средств на балансе для пополнения РК при создании')


    except AdvNotFoundInWBError as exc:
        auto_adv_id = exc.auto_adv_id
        await bot.send_message(user_telegram_id, f'Не удалось правильно настроить авто-РК для {nmid}, '
                                                 f'ID Авто {auto_adv_id} не найден после создания. Попробуйте '
                                                 f'самостоятельно найти нет ли новой РК в кабинете WB и '
                                                 f'обратитесь в поддержку -> {const.SUPPORT_LINK}')


    except StartComplexAdvError as exc:
        auto_adv_id = exc.auto_adv_id
        search_adv_id = exc.search_adv_id
        await bot.send_message(user_telegram_id, f'Произошла ошибка при попытке запустить РК (Авто - {auto_adv_id} и Аукцион - {search_adv_id}) проверьте'
                                                 f' самостоятельно запустились ли кампании и правильность их создания,'
                                                 f' а также при необходимости обратитесь в поддержку -> {const.SUPPORT_LINK}')