import asyncio
import logging
from functools import partial

from celery import shared_task
from app.client_bot.bot import get_bot
from app.core.wb_api.mixins.excs import ItemCategoryNotInStockError, AdvNotFoundInWBError
from app.modules.adv_creator import backend
from app.modules.adv_creator.backend import MainAdvManager
from celery import shared_task

logger = logging.getLogger(__name__)


async def _create_complex_advs(nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int):
    access = await backend.access_manager.get_access_for_wb_cabinet(shop_id)
    manager = MainAdvManager(access)

    while True:
        try:
            adv_adv: int = await manager.create_complex_advs(nmid, hard_mode)
            telegram_bot = get_bot()
            try:
                await telegram_bot.send_message(
                    user_telegram_id,
                    f'Создана РК adv_adv: {adv_adv}'
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления: {str(e)}", exc_info=True)

            finally:
                await telegram_bot.close()
            logger.debug(f'Создана РК adv_adv: {adv_adv}')
            break

        except backend.CardsNotFoundForShopError as exc:
            raise exc
        except AdvNotFoundInWBError as exc:
            logger.debug(f'Не найдено рк в Wildberries для {nmid} {shop_id}, повтор через 60 сек')
            await asyncio.sleep(60)
        except Exception as exc:
            logger.error(f'Ошибка при создании комплексной рк для артикула {nmid}', exc_info=True)
            await asyncio.sleep(60 * 3)


@shared_task(time_limit=12 * 60 * 60)
def create_complex_advs_task(nmid: int, shop_id: str, hard_mode: bool, user_telegram_id: int):
    """
    Celery task that properly handles the asyncio event loop lifecycle.
    """
    try:
        return asyncio.run(_create_complex_advs(nmid, shop_id, hard_mode, user_telegram_id))
    except Exception as e:
        logger.error(f"Task failed: {str(e)}", exc_info=True)

        raise