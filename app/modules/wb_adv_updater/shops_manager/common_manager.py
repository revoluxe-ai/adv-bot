#
#
# async def updating_keywords_in_shops(self):
#     async with _sm() as session:
#         stmt = select(WBCabinet).options(
#             joinedload(WBCabinet.adv_settings),
#             joinedload(WBCabinet.wb_user_cabinets)
#             .joinedload(WBUserCabinet.user)
#         ).filter(WBCabinet.adv_settings.any(AdvSetting.bot_active == True))
#
#         result = await session.execute(stmt)
#         cabinets: list[WBCabinet] = result.scalars().all()
#         keyword_update_tasks: dict[str, asyncio.Task] = {}
#         for cabinet in cabinets:
#             shop_id  = cabinet.shop_id
#             if shop_id not in keyword_update_tasks:
#                 all_users = cabinet.wb_user_cabinets.users
#                 all_tokens = [token  for user in all_users for token in user.wb_tokens]
#                 fake_user = User()
#                 fake_user.wb_tokens = all_tokens
#                 fake_user_wb_cabinet = WBUserCabinet()
#                 fake_user_wb_cabinet.wb_cabinet = cabinet
#                 fake_user_wb_cabinet.user = fake_user
#                 keyword_update_task = asyncio.create_task(self._update_keywords_in_cabinet(fake_user_wb_cabinet))
#                 keyword_update_task.add_done_callback(lambda task: keyword_update_tasks.pop(shop_id))
#                 keyword_update_tasks[shop_id] = keyword_update_task
#             else:
#                 task = keyword_update_tasks[shop_id]
#                 if task.done():
#                     if task.exception():
#                         raise task.exception()
#
#
#
# def __update_keywords_in_cabinet(self, cabinet:WBUserCabinet):
#     pass
#
#
#
#
#
#
#
#
#
#
