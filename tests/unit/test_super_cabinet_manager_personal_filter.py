from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.common_slaves.wildberries import super_cabinet_manager

pytestmark = pytest.mark.unit


def _build_sm_context(session: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_get_access_for_wb_cabinet_filters_non_personal_tokens() -> None:
    shop_id = "shop-1"
    with patch("app.modules.common_slaves.wildberries.super_cabinet_manager.sm") as sm_mock:
        session1 = MagicMock()
        session2 = MagicMock()
        sm_mock.side_effect = [_build_sm_context(session1), _build_sm_context(session2)]

        exec1 = MagicMock()
        exec1.scalar.return_value = 123
        session1.execute = AsyncMock(return_value=exec1)

        wb_cabinet = MagicMock()
        wb_cabinet.shop_id = shop_id
        wb_cabinet.active = True
        session2.get = AsyncMock(return_value=wb_cabinet)

        base_token = MagicMock()
        base_token.api_key = "base"
        base_token.check_valid.return_value = True
        base_token.is_personal = False
        base_token.shop_id = shop_id

        personal_token = MagicMock()
        personal_token.api_key = "personal"
        personal_token.check_valid.return_value = True
        personal_token.is_personal = True
        personal_token.shop_id = shop_id

        exec2 = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = [base_token, personal_token]
        exec2.scalars.return_value = scalars
        session2.execute = AsyncMock(return_value=exec2)

        access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)

        assert len(access.tokens) == 1
        assert access.tokens[0] is personal_token


@pytest.mark.asyncio
async def test_get_access_for_wb_cabinet_raises_when_no_personal_tokens() -> None:
    shop_id = "shop-1"
    with (
        patch("app.modules.common_slaves.wildberries.super_cabinet_manager.sm") as sm_mock,
        patch(
            "app.modules.common_slaves.wildberries.super_cabinet_manager.deactivate_cabinet_atomic_with_user_trackers",
            new_callable=AsyncMock,
        ) as deactivate_mock,
    ):
        session1 = MagicMock()
        session2 = MagicMock()
        sm_mock.side_effect = [_build_sm_context(session1), _build_sm_context(session2)]

        exec1 = MagicMock()
        exec1.scalar.return_value = 123
        session1.execute = AsyncMock(return_value=exec1)

        wb_cabinet = MagicMock()
        wb_cabinet.shop_id = shop_id
        wb_cabinet.active = True
        session2.get = AsyncMock(return_value=wb_cabinet)
        session2.commit = AsyncMock(return_value=None)

        non_personal = MagicMock()
        non_personal.api_key = "np"
        non_personal.check_valid.return_value = True
        non_personal.is_personal = False
        non_personal.shop_id = shop_id

        exec2 = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = [non_personal]
        exec2.scalars.return_value = scalars
        session2.execute = AsyncMock(return_value=exec2)

        with pytest.raises(ApiForbiddenError):
            await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)

        deactivate_mock.assert_awaited_once_with(
            shop_id,
            notification_type=super_cabinet_manager.NotificationType.TOKEN_DEACTIVATED.value,
        )
