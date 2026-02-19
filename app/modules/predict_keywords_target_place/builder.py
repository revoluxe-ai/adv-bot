from .di import PredictKeywordsTargetPlaceContainer
from .predict_keywords_target_place import PredictKeywordsTargetPlace


def build_predict_keywords_target_place() -> PredictKeywordsTargetPlace:
    container = PredictKeywordsTargetPlaceContainer()
    return container.predict_keywords_target_place_manager()
