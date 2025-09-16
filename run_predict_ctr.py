import asyncio

from app.modules.wb_adv_updater.runner import run_update_predict_ctr

if __name__ == "__main__":
    asyncio.run(run_update_predict_ctr())
