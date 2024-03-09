import new
from session_maker import get_async_session_maker


class UserCabinetManager:
    def __init__(self, user_wb_cabinet: new.types.WBUserCabinet):
        tokens: new.types.User = user_wb_cabinet.user
        self.__wb_api = new.WBApi(tokens)







#
# def get_wb_user_cabinet_manager(user_wb_cabinet: new.types.WBUserCabinet):
#
