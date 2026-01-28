from unittest.mock import MagicMock

from dependency_injector import providers

from app.core.di.wb_manager_hub.wb_manager_hub import WBManagerHub


def test_wb_manager_hub_unwraps_wb_manager_provider() -> None:
    sentinel = MagicMock(name="wb_manager")
    provider = providers.Singleton(lambda: sentinel)

    hub = WBManagerHub(
        wb_data_manager=MagicMock(),
        wb_promotion_manager=MagicMock(),
        wb_manager=provider,
        redis_client_wrapper=MagicMock(),
        cluster_bids_update_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
    )

    assert hub.wb_manager is sentinel
