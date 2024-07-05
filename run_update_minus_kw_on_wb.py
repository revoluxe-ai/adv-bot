from app.modules.wb_adv_updater.runner import Runner


runner = Runner()


if __name__ == '__main__':
    import asyncio
    asyncio.run(runner.run_update_keywords_on_wb())