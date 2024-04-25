from abc import ABC
import os


class AbcManager(ABC):
    data_folder = 'app/keyword_async_ml_updater/data'
    keyword_stat_df_path = os.path.join(data_folder, 'df.csv')
    nmid_offer_id_shop_name_df_path = os.path.join(data_folder, 'nmid_offer_id_df.csv')
    model_path = os.path.join(data_folder, 'model.ml')
    keywords_vectors_path = os.path.join(data_folder, 'keywords_vectors.csv')
    nmids_vectors_path = os.path.join(data_folder, 'offer_ids_vectors.csv')
