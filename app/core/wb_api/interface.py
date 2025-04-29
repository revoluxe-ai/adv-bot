from app.modules.common_slaves.wildberries.models import WBToken


class Headers:
    def __init__(self, token: WBToken):
        self.current_token: WBToken = token

    @property
    def standart(self):
        return {"Authorization": self.current_token.api_key}


class InterfaceWBAPI:
    headers: Headers
