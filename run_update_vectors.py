from app.modules.wb_adv_updater.runner import Runner
import asyncio

runner = Runner()


need_update_model:asyncio.Event = asyncio.Event()
update_model_on_new_features:asyncio.Event = asyncio.Event()


if __name__ == '__main__':
    asyncio.run(runner.run_update_vectors(need_update_model, update_model_on_new_features))