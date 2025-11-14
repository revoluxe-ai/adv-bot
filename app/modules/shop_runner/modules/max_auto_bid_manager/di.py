from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Dependency, Singleton
from dependency_injector import containers

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.modules.max_auto_bid_manager.max_cpm_redis_status_manager import (
    MaxCpmRedisStatusManager,
)
from .auto_max_bid_manager import AutoMaxBidManager


class AutoMaxCpmContainer(DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.modules.shop_runner.bidder.bidder_func",
            "app.client_bot.user_interface.views.messages.adv_keyword_messages.adv_keyword_messages",
            "app.modules.shop_runner.service_manager."
            "old_modules.setting_auto_updater_v2.adv_control_system."
            "executors.target_place_executor.utils",
        ]
    )
    redis_client_wrapper = Dependency(instance_of=RedisClient)
    max_cpm_redis_status_manager = Singleton(
        MaxCpmRedisStatusManager, redis_client=redis_client_wrapper
    )
    auto_max_cpm_bid_manager = Singleton(
        AutoMaxBidManager, max_cpm_status_manager=max_cpm_redis_status_manager
    )
