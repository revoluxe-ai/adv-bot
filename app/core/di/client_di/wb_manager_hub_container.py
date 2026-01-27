from typing import cast

from dependency_injector import containers, providers
from dependency_injector.providers import Provider

from app.core.di.client_di.wb_data_container import WBDataContainer
from ..wb_manager_hub.wb_manager_hub import WBManagerHub
from ...mp.wb.api.auth_client_handler import AuthClientHandler
from ...mp.wb.api.httpx_client_handler import HttpxClientHandler
from ...mp.wb.api.managers import WBDataManager, WBModifier
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager import (
    ClusterBidsManagerContainer,
    UpdateClusterBidsManager,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager import (
    RedisKeywordBidderStatusManager,
)
from ...redis_manager_v2.redis_client import RedisClient


class WBManagerHubContainer(containers.DeclarativeContainer):
    _shop_id = providers.Dependency(instance_of=str)
    _httpx_client_handler = providers.Dependency(instance_of=HttpxClientHandler)

    _redis_wrapper = providers.Dependency(instance_of=RedisClient)

    _auth_client_handler = providers.Singleton(
        AuthClientHandler,
        shop_id=_shop_id,
        httpx_client_handler=_httpx_client_handler,
    )

    _wb_data_container: WBDataContainer = providers.Container(  # pyright: ignore
        WBDataContainer,
        _auth_client_handler=_auth_client_handler,
    )

    _wb_data_manager: Provider[WBDataManager] = cast(
        Provider[WBDataManager],
        _wb_data_container.wb_data_manager,
    )
    _wb_promotion_manager: Provider[WBModifier] = cast(
        Provider[WBModifier],
        _wb_data_container.wb_promotion_manager,
    )

    _cluster_bids_updater_container: providers.Container[ClusterBidsManagerContainer] = (
        providers.Container(
            ClusterBidsManagerContainer, shop_id=_shop_id, redis_client=_redis_wrapper
        )
    )
    _cluster_bids_updater_container_typed = cast(
        ClusterBidsManagerContainer,
        _cluster_bids_updater_container,
    )
    _update_cluster_bids_manager: Provider[UpdateClusterBidsManager] = cast(
        Provider[UpdateClusterBidsManager],
        _cluster_bids_updater_container_typed.update_cluster_bids_manager,
    )
    _wb_manager = cast(
        Provider["WBManager"],
        _cluster_bids_updater_container_typed.wb_manager,
    )
    _redis_keyword_bidder_status_manager: Provider[RedisKeywordBidderStatusManager] = cast(
        Provider[RedisKeywordBidderStatusManager],
        _cluster_bids_updater_container_typed.redis_keyword_bidder_status_manager,
    )

    wb_manager_hub = providers.Singleton(
        WBManagerHub,
        wb_data_manager=_wb_data_manager,
        wb_promotion_manager=_wb_promotion_manager,
        wb_manager=_wb_manager,
        cluster_bids_update_manager=_update_cluster_bids_manager,
        redis_client_wrapper=_redis_wrapper,
        redis_keyword_bidder_status_manager=_redis_keyword_bidder_status_manager

    )
