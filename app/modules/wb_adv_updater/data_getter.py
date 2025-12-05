# from collections import defaultdict
#
# import pandas as pd
#
# from app.core.wb_api.data_classes.card_from_wb import CardFromWB
# from app.modules.wb_adv_updater.ABC_manager import AbcManager
# from app.utils import redis_manager
# from app.utils.NeoDataScience.driver import DataScience
#
#
# class DataGetter(AbcManager):
#     def __init__(self) -> None:
#         self._gds = DataScience()
#
#     @staticmethod
#     def normalize_df_data(df: pd.DataFrame, param_for_norm: str) -> pd.DataFrame:
#         max_ = df[param_for_norm].max()
#         min_ = df[param_for_norm].min()
#         return (df[param_for_norm] - min_) / (max_ - min_)
#
#     @staticmethod
#     def get_nmid_offer_id_df(cards: list[CardFromWB]) -> pd.DataFrame:
#         dict_ = defaultdict(list)
#         for card in cards:
#             dict_["nmid"].append(card.nmid)
#             dict_["offer_id"].append(card.offer_id)
#             dict_["shop_name"].append(card.shop_name)
#         nmid_offer_id_df = pd.DataFrame(dict_)
#         return nmid_offer_id_df
#
#     async def get_list_progress(self, jobid):
#         result = await self._gds.get_status_job(jobid)
#         return result
#
#     async def get_item_features_from_neo(self, nmids_batch):
#         result = await self._gds.get_nmid_vectors(nmids_batch)
#         return result
#
#     @staticmethod
#     async def get_item_features_from_redis(nmids_batch):
#         result = await redis_manager.get_nmid_vectors(nmids_batch)
#         return result
#
#     async def get_keyword_features_from_neo(self, keywords):
#         result = await self._gds.get_keywords_vectors_by_keywords(keywords)
#         return result
#
#     @staticmethod
#     async def get_keyword_features_from_redis(
#         keywords,
#     ) -> list[tuple[str, list[float]]]:
#         result = await redis_manager.get_keywords_vectors(keywords)
#         return result
