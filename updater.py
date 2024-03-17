from app import redis_func_cache
redis_func_cache.set_config()
from python_modules.logger import setup_logging
from app.keyword_async_ml_updater.runner import Runner
import logging


r = Runner()
if __name__ == '__main__':
    level = logging.INFO
    setup_logging()
    r.run(debug_mode = False)


    # asyncio.run(m.update_nmid_offer_id_shop_name_df())

    # m.save_full_predict()

    # m.graph_updater.save_offer_id_and_keyword_featers_dfs_for_ml()
    # m.get_model()
    # m.update_keywords_on_wb()
    # r.update_vectors(power=12, force=True)
    # r.run_all()
    # r.update_nmid_offer_id_df()

