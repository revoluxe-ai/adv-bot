import asyncio
import logging


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


