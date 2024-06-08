import asyncio

from app.modules.wb_adv_updater.wb_manager import Manager


manager = Manager()


async def run():
    await manager.update_cards_in_graph()



if __name__ == '__main__':
    asyncio.run(run())