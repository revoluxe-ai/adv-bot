from app.core.redis_manager_v2 import BaseRedisManager
from app.core.redis_manager_v2.mixins import PredictCTRRedisMixin


class PredictCTRRedisManager(PredictCTRRedisMixin, BaseRedisManager):
    pass
