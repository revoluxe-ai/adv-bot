from app.core.wb_api.mixins.check_righter_base import CheckRighter


class AdvRightsChecker(CheckRighter):
    ENTRY_POINT = "https://advert-api.wildberries.ru/ping"
