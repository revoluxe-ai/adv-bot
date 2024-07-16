from app.modules.wb_adv_updater.wb_manager import  Manager



manager = Manager()


async def upload_cards_to_neo4j():
    await manager.update_cards_in_graph_for_shops()


if __name__ == '__main__':
    import asyncio
    asyncio.run(upload_cards_to_neo4j())