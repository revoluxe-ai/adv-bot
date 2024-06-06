from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess


class ErrorHandler:
    def __init__(self, access: WBCabinetAccess):
        self._access = access
        self._keywords_more_than_1000 = KeywordsMoreThan1000()



    @abstractmethod
    async def register_error(self, error: Exception):
        pass

    @abstractmethod
    async def reset_error(self):
        pass











