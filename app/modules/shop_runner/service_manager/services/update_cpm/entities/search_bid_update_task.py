# class SearchBidUpdateTask:
#     def __init__(self, adv_setting, *, nmid: int, new_bid: int) -> None:
#         adv_id = adv_setting.search_adv_id
#         if not adv_id:
#             raise ValueError(
#                 "SearchBidUpdateTask requires adv_setting with search_adv_id"
#             )
#         if nmid not in adv_setting.nmids:
#             raise ValueError(f"nmid {nmid} not in adv_setting.nmids")
#         self.adv_id = adv_id
#         self.new_bid = new_bid
#
#
# class SearchBidUpdateTasksGroup:
#     def __init__(self) -> None:
#         self.tasks = []
#
#     def add_task(self, adv_setting, *, nmid: int, new_bid: int) -> None:
#         task = SearchBidUpdateTask(adv_setting, nmid=nmid, new_bid=new_bid)
#         self.tasks.append(task)
