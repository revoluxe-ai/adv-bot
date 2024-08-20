import asyncio
import logging

from app.modules.wb_adv_updater.ml_data_manager import update_model

logger = logging.getLogger(__name__)


async def run_update_data_in_neo4j():
    from . import ml_data_manager
    await asyncio.gather(
            update_cards_in_graph(),
            ml_data_manager.update_wb_adv_phrase_in_db(),
        )


async def update_cards_in_graph():
    from . import ml_data_manager
    while True:
        try:
            await ml_data_manager.update_cards_in_graph()
            logger.debug('Карточки обновлены')
        except Exception as exc:
            logger.error(f'Ошибка обновления карточек в neo4j {exc}', exc_info=True)
        await asyncio.sleep(0)


async def run_update_model():
    while True:
        try:
            await update_model()
        except Exception as e:
            logger.error(f'Ошибка обновления модели {e}', exc_info=True)
        await asyncio.sleep(0)