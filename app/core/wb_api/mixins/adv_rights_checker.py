from app.core.wb_api.check_righter import CheckRighter


class AdvRightsChecker(CheckRighter):
    ENTRY_POINT = "https://advert-api.wildberries.ru/ping"
