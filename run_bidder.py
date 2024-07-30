from app.modules.wb_adv_updater.runner import Runner
import asyncio


runner = Runner()

if __name__ == '__main__':
    asyncio.run(runner.run_bidder_process())