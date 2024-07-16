from app.modules.wb_adv_updater.wb_manager import  Manager



manager = Manager()


async def upload_cards_to_neo4j():
    await manager.update_wb_adv_phrase_in_db_bot_active()


if __name__ == '__main__':
    import asyncio
    asyncio.run(upload_cards_to_neo4j())