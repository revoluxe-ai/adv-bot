from dependency_injector import containers, providers
from .predict_keywords_target_place import  PredictKeywordsTargetPlace
from .clickhouse_manager import ClickHouseManager

class PredictKeywordsTargetPlaceContainer(containers.DeclarativeContainer):


    _clickhouse_manager = providers.Singleton(ClickHouseManager)

    predict_keywords_target_place_manager = providers.Singleton(PredictKeywordsTargetPlace,
                                                                clickhouse_manager=_clickhouse_manager)
    
