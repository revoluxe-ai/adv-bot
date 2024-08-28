from app.modules.wb_adv_updater.runner import update_all_data_in_db



if __name__ == '__main__':
    import asyncio
    asyncio.run(update_all_data_in_db())