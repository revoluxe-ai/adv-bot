# import asyncio
# from time import sleep
#
# from app.core.di import DIManager
#
#
# update_model_on_new_features = asyncio.Event()
# update_model_on_new_features.set()
# need_update_model = asyncio.Event()
# need_update_model.set()
# import logging
#
#
# async def run():
#     await run_update_model()
#
#
# logger = logging.getLogger(__name__)
#
#
# async def update_model() -> None:
#     # TODO: Сделать нормальный контекстый менеджер для DI
#     async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
#         await run()
#
#
# if __name__ == "__main__":
#     while True:
#         try:
#             asyncio.run(update_model())
#         except Exception as e:
#             logger.exception(e)
#             sleep(70)
