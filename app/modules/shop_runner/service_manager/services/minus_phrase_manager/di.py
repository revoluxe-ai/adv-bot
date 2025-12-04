from dependency_injector import containers, providers
from app.core.mp.wb.api.wb_manager_hub import WBManagerHub
from .minus_phrase_manager import MinusPhraseManager
from .click_house_manager import ClickHouseManager
from app.core.clikhouse_client_manager import get_clickhouse_client

class MinusPhraseManagerContainer(containers.DeclarativeContainer):

    _get_clickhouse_client = providers.Callable(get_clickhouse_client)

    _wb_api_manager_hub = providers.Dependency(instance_of=WBManagerHub)

    minus_phrase_manager = providers.Singleton(
        MinusPhraseManager,
        wb_api_manager_hub=_wb_api_manager_hub,
        click_house_manager = providers.Singleton(ClickHouseManager,)
    )
