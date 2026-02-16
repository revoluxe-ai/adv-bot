from .predict_keywords_target_place import PredictKeywordsTargetPlace
from .di import PredictKeywordsTargetPlaceContainer


def build_predict_keywords_target_place() -> PredictKeywordsTargetPlace:
    container = PredictKeywordsTargetPlaceContainer()
    manager: PredictKeywordsTargetPlace = container.predict_keywords_target_place_manager()
    return manager
