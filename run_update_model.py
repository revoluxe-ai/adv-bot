import asyncio

from app.modules.wb_adv_updater.runner import Runner
import asyncio


runner = Runner()

update_model_on_new_features = asyncio.Event()
update_model_on_new_features.set()
need_update_model =  asyncio.Event()
need_update_model.set()


async def run():
    await runner.run_update_model(update_model_on_new_features, need_update_model)



if __name__ == '__main__':
    asyncio.run(run())