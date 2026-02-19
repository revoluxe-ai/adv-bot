from dependency_injector import containers, providers



from .clickhouse_manager import ClickHouseManager
from .predict_keywords_target_place import PredictKeywordsTargetPlace
from ..bids_for_positions_manager.builder import build_bids_for_positions_manager


class PredictKeywordsTargetPlaceContainer(containers.DeclarativeContainer):
    _clickhouse_manager = providers.Singleton(ClickHouseManager)
    _bids_for_positions_manager = providers.Singleton(build_bids_for_positions_manager)
    predict_keywords_target_place_manager = providers.Singleton(
        PredictKeywordsTargetPlace,
        clickhouse_manager=_clickhouse_manager,
        bids_for_positions_manager=_bids_for_positions_manager,
    )
