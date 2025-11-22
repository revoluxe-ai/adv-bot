import typing
if typing.TYPE_CHECKING:
    from .managers import WBDataManager



class WBManagerHub:
    def __init__(self, wb_data_manager: "WBDataManager"):
        self.__wb_data_manager = wb_data_manager

    @property
    def wb_data_manager(self) -> "WBDataManager":
        return self.__wb_data_manager

