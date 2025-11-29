import typing

if typing.TYPE_CHECKING:
    from .managers import WBDataManager, WBModifier


class WBManagerHub:
    def __init__(
        self, wb_data_manager: "WBDataManager", wb_promotion_manager: "WBModifier"
    ):
        self.__wb_data_manager = wb_data_manager
        self.__wb_promotion_manager = wb_promotion_manager

    @property
    def wb_data_manager(self) -> "WBDataManager":
        return self.__wb_data_manager

    @property
    def wb_modifier(self) -> "WBModifier":
        return self.__wb_promotion_manager
