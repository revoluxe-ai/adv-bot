from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot import const
from app.modules.adv_creator.backend import tasks


@asynccontextmanager
async def _dummy_di_context() -> Any:
    yield object()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_func_name", "inner_func_name", "kwargs", "task_name"),
    [
        (
            "create_search_only",
            "_create_search_only",
            {
                "nmid": 101,
                "shop_id": "shop_1",
                "existing_auto_adv_id": 5001,
                "user_telegram_id": 9001,
            },
            "create_search_only",
        ),
        (
            "create_auto_only",
            "_create_auto_only",
            {
                "nmid": 102,
                "shop_id": "shop_2",
                "existing_search_adv_id": 7001,
                "user_telegram_id": 9002,
            },
            "create_auto_only",
        ),
        (
            "create_complex_advs",
            "_create_complex_advs",
            {
                "nmid": 103,
                "shop_id": "shop_3",
                "hard_mode": False,
                "user_telegram_id": 9003,
            },
            "create_complex_advs",
        ),
    ],
)
async def test_adv_creator_tasks_unknown_error_notifies_and_reraises(
    task_func_name: str,
    inner_func_name: str,
    kwargs: dict[str, Any],
    task_name: str,
) -> None:
    ctx: dict[str, Any] = {}
    user_telegram_id = int(kwargs["user_telegram_id"])
    bot = MagicMock()
    bot.send_message = AsyncMock()

    with (
        patch.object(tasks.DIManager, "create", AsyncMock(return_value=_dummy_di_context())),
        patch.object(tasks, inner_func_name, AsyncMock(side_effect=RuntimeError("boom"))),
        patch.object(tasks, "get_bot", return_value=bot),
    ):
        task_func = getattr(tasks, task_func_name)
        with pytest.raises(RuntimeError, match="boom"):
            await task_func(ctx, **kwargs)

    expected_admin_ids = set(const.ADMINS)
    assert bot.send_message.await_count >= 1 + len(expected_admin_ids)

    first_call_args = bot.send_message.await_args_list[0].args
    assert first_call_args[0] == user_telegram_id
    assert "Произошла ошибка" in first_call_args[1]

    admin_messages: dict[int, list[str]] = {admin_id: [] for admin_id in expected_admin_ids}
    for call in bot.send_message.await_args_list[1:]:
        recipient = int(call.args[0])
        text = str(call.args[1])
        if recipient in admin_messages:
            admin_messages[recipient].append(text)

    for admin_id in expected_admin_ids:
        assert admin_messages[admin_id], f"Admin {admin_id} did not receive notifications"
        joined = "\n".join(admin_messages[admin_id])
        assert f"ARQ task failed: {task_name}" in joined
        assert "RuntimeError: boom" in joined
