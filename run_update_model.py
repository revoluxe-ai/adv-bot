import asyncio
from time import sleep

from app.modules.wb_adv_updater.runner import run_update_model
import asyncio



update_model_on_new_features = asyncio.Event()
update_model_on_new_features.set()
need_update_model =  asyncio.Event()
need_update_model.set()
import logging

async def run():
    await run_update_model()



logger = logging.getLogger(__name__)

if __name__ == '__main__':
    while True:
        try:
            asyncio.run(run())
        except Exception as e:
            logger.exception(e)
            sleep(70)