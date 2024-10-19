from .utils.redis_func_cache import set_config
set_config()


from app.modules.common_slaves.wildberries import exceptions as exc
from app.modules.wb_adv_updater import wb_manager