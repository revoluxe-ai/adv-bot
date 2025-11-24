from dependency_injector import containers, providers

from app.core.redis_manager_v2.redis_client import RedisClient
from .redis_last_total_views import  RedisLastTotalViews

class BidderContainer(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(
        packages=["app.modules.shop_runner.run_process_func",]
    )

    _redis_client = providers.Dependency(instance_of=RedisClient)

    redis_last_total_views = providers.Singleton(RedisLastTotalViews,
                                                 redis_client=_redis_client)