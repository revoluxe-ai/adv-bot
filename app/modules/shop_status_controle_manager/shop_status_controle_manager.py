from datetime import datetime

from .base_manager import BaseManager
from .redis_manager import Success, Error
from .statuses.result_status import Status as ResultStatus


class StatusControlManager(BaseManager):
    async def add_success_status(self, func_name: str) -> None:
        dt = datetime.now()
        success = Success(dt)
        await self.success_handler.set(func_name, success)

    async def add_error_status(self, func_name: str, error: Exception) -> None:
        dt = datetime.now()
        type_error = type(error).__name__
        message = str(error)
        error_obj = Error(dt, type_error, message)
        await self.error_handler.set(func_name, error_obj)

    async def get_last_status(self, func_name: str) -> ResultStatus | None:
        last_success = await self.success_handler.get(func_name)
        last_error = await self.error_handler.get(func_name)
        if not last_success and not last_error:
            return None
        if last_success and not last_error:
            status = ResultStatus(
                result="success", last_update=last_success.dt, last_error=None
            )
        elif not last_success and last_error:
            status = ResultStatus(
                result="error", last_update=last_error.dt, last_error=last_error
            )
        else:
            if last_success.dt > last_error.dt:
                status = ResultStatus(
                    result="success", last_update=last_success.dt, last_error=None
                )
            else:
                status = ResultStatus(
                    result="error", last_update=last_error.dt, last_error=last_error
                )
        return status

    async def get_status_text(self) -> str:
        from .coroutines_names_for_users_mapper import user_names as fn_users_names

        text = ""

        for fn_original_name, user_fn_name in fn_users_names.items():
            status = await self.get_last_status(fn_original_name)
            if not status:
                text += f"{user_fn_name}: Нет данных о выполнении функции\n"
                continue
            if status.result == "success":
                text += (
                    f"{user_fn_name}: Функция успешно работает {status.last_update}\n"
                )
            else:
                text += (
                    f"{user_fn_name}: Ошибка функции {status.last_update}, "
                    f"Тип ошибки: {status.last_error}\n"
                )

        return text
