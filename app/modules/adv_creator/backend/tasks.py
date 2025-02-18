import asyncio
import logging
from celery import shared_task
from aiogram.exceptions import TelegramRetryAfter
from app.client_bot.bot import get_bot
from app.core.wb_api.mixins.excs import AdvNotFoundInWBError
from app.modules.adv_creator import backend
from app.modules.adv_creator.backend import MainAdvManager

logger = logging.getLogger(__name__)
from app.core.wb_api.mixins.excs  import ItemCategoryNotInStockError
from app.core.wb_api.mixins.excs import CardNotFoundInWB
from app.core.wb_api.exceptions import ApiForbiddenError, TooManyRequests


async def _create_complex_advs(nmid: int, shop_id: str, hard_mode: bool):
    access = await backend.access_manager.get_access_for_wb_cabinet(shop_id)
    manager = MainAdvManager(access)
    while True:
        try:
            adv_adv: int = await manager.create_complex_advs(nmid, hard_mode)
            logger.debug(f'Создана РК adv_adv: {adv_adv}')
            return  adv_adv
        except backend.CardsNotFoundForShopError as exc:
            raise exc
        except ItemCategoryNotInStockError as e:
            raise e
        except AdvNotFoundInWBError as exc:
            logger.debug(f'Не найдено рк в Wildberries для {nmid} {shop_id}, повтор через 60 сек')
            await asyncio.sleep(60)
        except ApiForbiddenError:
            raise
        except TooManyRequests:
            logger.error(f'Слишком много запросов к Wildberries, повтор через 1 минуту')
            await asyncio.sleep(60)
        except CardNotFoundInWB:
            logger.error(f'Карточка с артикулом {nmid} не найдена на Wildberries')
            raise
        except Exception as exc:
            logger.error(f'Ошибка при создании комплексной рк для артикула {nmid}', exc_info=True)
            await asyncio.sleep(60 * 3)


def get_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop



@shared_task(time_limit=12 * 60 * 60)
def create_complex_advs_task(nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int):
    send_user_message.delay(f'Начинаю создавать комплекс кампаний для артикула {nmid}',
                            user_telegram_id)
    try:
        loop = get_event_loop()
        adv_id = loop.run_until_complete(_create_complex_advs(nmid, shop_id, hard_mode))
        send_user_message.delay(f'Кампания успешно создана, ID авто {adv_id}',
                                user_telegram_id)
    except CardNotFoundInWB:
        send_user_message.delay(f'Карточка с артикулом {nmid} не найдена на Wildberries',
                                user_telegram_id)
        return
    except ApiForbiddenError:
        send_user_message.delay('Нет нужных прав. Добавьте магазин с правильным токеном под новым именем',
                                user_telegram_id)
    except ItemCategoryNotInStockError:
        send_user_message.delay(f'Нет остатков у артикула {nmid}', user_telegram_id)
    except backend.CardsNotFoundForShopError:
        logger.error(f'Карточка с артикулом {nmid} не найдена на Wildberries')
        send_user_message.delay(f'Карточка с артикулом {nmid} не найдена на Wildberries')
    except Exception as e:
        logger.error(f"Task failed: {str(e)}", exc_info=True)
        raise

async def _send_user_message(message: str, user_telegram_id: int):
    bot = get_bot()
    try:
        await bot.send_message(user_telegram_id, message)
        await asyncio.sleep(0.5)
        await bot.session.close()
    except Exception as e:
        raise e


@shared_task(
    bind=True,
    max_retries=5,
    retry_backoff=True,  # Включает экспоненциальный рост времени повтора
    retry_backoff_max=600  # Максимум 10 минут
)
def send_user_message(self, message: str, user_telegram_id: int):
    loop = get_event_loop()
    try:
        loop.run_until_complete(_send_user_message(message, user_telegram_id))
    except TelegramRetryAfter as e:
        retry_after = e.retry_after or 600  # Устанавливаем задержку
        raise self.retry(countdown=retry_after)
    except Exception as e:
        raise e