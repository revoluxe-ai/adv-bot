from time import sleep
import logging

logger = logging.getLogger(__name__)

from app.modules.wb_adv_updater.runner import Runner
import asyncio


runner = Runner()

if __name__ == '__main__':
    while True:
        try:
             asyncio.run(runner.run_bidder_process())
        except Exception as e:
            logging.error(f'Error in run_bidder: {e}')
            sleep(60)