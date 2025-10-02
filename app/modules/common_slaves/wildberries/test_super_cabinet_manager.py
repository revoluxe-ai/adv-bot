import asyncio
import pytest

from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess

# TODO: Тест зависает, если запускаем все через pytest, сам отдельно работает.
"""

Причина «зависания»
Сам тест завершается-успешно (✓), но после него собыLoop остаётся с необработанными задачами (WBShop._alive_worker_run, AsyncMockMixin._execute_mock_call).
Когда тест запускается из PyCharm-UI – он выполняется отдельно, поэтому лишние tasks не мешают. В общем запуске через CLI в одном-процессе эти «висящие» корутины держат event-loop; pytest-timeout ловит это и пишет большой трейс.
Что создаёт лишние задачи
AsyncMock() по умолчанию возвращает coroutine-object; при первом await он ставит «хвостовую» task, которая остаётся незавершённой. То же происходит с моками __aenter__/__aexit__.
Как по-уму починить
Делать все AsyncMock с spec_set и возвращать обычные значения, а не корутины, если они не await-ятся.
Очищать loop в конце теста:
Проще и быстрее (чтобы релиз не стопорить)
Сделать этот тест skip, как мы поступили с другими легаси-тестами:
Либо запустить его в отдельном subprocess-плагине (pytest-xprocess/pytest-forked), но это дольше настраивать.
Предлагаю вариант со skip – он уберёт зависание и не влияет на рабочий код.

"""


@pytest.mark.asyncio
@pytest.mark.parametrize("shop_id", ["7de14a75-4939-40ff-b4dd-9dd5472a4348"])
async def test_super_cabinet_manager_get_access_for_wb_cabinet(shop_id):
    with patch("app.modules.common_slaves.wildberries.super_cabinet_manager.sm") as sm_mock:
        # Два отдельных async context manager для двух вызовов `async with sm()`
        # Use plain MagicMock for sessions; AsyncMock only for awaited methods
        session1 = MagicMock()
        session2 = MagicMock()

        cm1 = MagicMock()
        cm1.__aenter__ = AsyncMock(return_value=session1)
        cm1.__aexit__ = AsyncMock(return_value=False)

        cm2 = MagicMock()
        cm2.__aenter__ = AsyncMock(return_value=session2)
        cm2.__aexit__ = AsyncMock(return_value=False)

        sm_mock.side_effect = [cm1, cm2]

        # 1) Первый SELECT -> scalar() вернет cabinet_id
        exec1 = MagicMock()
        exec1.scalar.return_value = 123
        session1.execute = AsyncMock(return_value=exec1)

        # 2) Второй блок: session.get -> WBCabinet со shop_id
        wb_cabinet = MagicMock()
        wb_cabinet.shop_id = shop_id
        session2.get = AsyncMock(return_value=wb_cabinet)

        # 3) SELECT токенов -> scalars().all() -> валидный токен с тем же shop_id
        exec2 = MagicMock()
        scalars = MagicMock()
        token = MagicMock()
        token.check_valid.return_value = True
        token.shop_id = shop_id
        token.api_key = "test"
        scalars.all.return_value = [token]
        exec2.scalars.return_value = scalars
        session2.execute = AsyncMock(return_value=exec2)

        access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
        assert isinstance(access, WBCabinetAccess)

        # Ensure no pending tasks remain after test (cancel them)
        current = asyncio.current_task()
        for task in list(asyncio.all_tasks()):
            if task is current:
                continue
            if task.done():
                continue
            task.cancel()
            try:
                await task
            except Exception:
                pass
