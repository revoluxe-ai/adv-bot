from . import SuccessHandler, ErrorHandler
from ..statuses.result_status import Status
from ...common_slaves.wildberries.models import WBCabinet


class RedisManager:
    def __init__(self, wb_cabinet: WBCabinet):
        self.success_handler: SuccessHandler = SuccessHandler(wb_cabinet)
        self.error_handler: ErrorHandler = ErrorHandler(wb_cabinet)

    async def get_last_status(self, func_name) -> Status:
        success = await self.success_handler.get(func_name)
        error = await self.error_handler.get(func_name)

        if success.dt > error.dt:
            return Status("success", last_update=success.dt, last_error=None)
        else:
            return Status("error", last_update=success.dt, last_error=error.type_error)
