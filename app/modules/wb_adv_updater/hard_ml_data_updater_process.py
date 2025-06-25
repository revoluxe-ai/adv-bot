import asyncio
import logging


logger = logging.getLogger(__name__)


async def run_update_cards_data_in_neo4j():
    await asyncio.gather(
        update_cards_in_graph_small_cycle(),
    )


async def update_cards_in_graph_big_cycle():
    from . import ml_data_manager

    while True:
        try:
            await ml_data_manager.update_cards_in_graph_for_shops_big_cycle()
            logger.debug("Карточки обновлены")
        except Exception as exc:
            logger.error(f"Ошибка обновления карточек в neo4j {exc}", exc_info=True)
            del exc
        await asyncio.sleep(0)


async def update_cards_in_graph_small_cycle():
    from . import ml_data_manager

    while True:
        try:
            await ml_data_manager.update_cards_in_graph_small_cycle()
            logger.debug("Карточки обновлены")
        except Exception as exc:
            logger.error(f"Ошибка обновления карточек в neo4j {exc}", exc_info=True)
        await asyncio.sleep(0)


async def update_keywords_ctr_by_similary():
    from . import ml_data_manager

    while True:
        try:
            await ml_data_manager.update_keywords_ctr_by_similary()
            logger.debug("CTR обновлен")
        except Exception as exc:
            logger.error(f"Ошибка обновления CTR по похожести {exc}", exc_info=True)
        await asyncio.sleep(0)
