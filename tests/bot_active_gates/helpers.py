"""Общие хелперы для gate-тестов shop-runner (RECORD vs ACT).

Доменные объекты собираются через ``AdvSettingFactory`` и DTO ``ComplexAdv``.
``MagicMock`` — только для внешних клиентов (WB hub, sessions, spies).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager.manager import CoroutinesManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from tests.factories.adv_factory import AdvSettingFactory


class _FixtureScalarResult:
    def __init__(self, rows: Sequence[AdvSetting]) -> None:
        self._rows = list(rows)

    def all(self) -> list[AdvSetting]:
        return list(self._rows)


class _FixtureExecuteResult:
    def __init__(self, rows: Sequence[AdvSetting]) -> None:
        self._rows = rows

    def scalars(self) -> _FixtureScalarResult:
        return _FixtureScalarResult(self._rows)


class _FixtureLoaderSession:
    def __init__(self, inactive_complex_adv: ComplexAdv) -> None:
        self._inactive_complex_adv = inactive_complex_adv

    async def execute(self, statement: object) -> _FixtureExecuteResult:
        sql = str(statement)
        if "WHERE advsetting.adv_id IN" in sql:
            search_adv = self._inactive_complex_adv.search_adv
            return _FixtureExecuteResult([search_adv] if search_adv is not None else [])
        if "advsetting.bot_active IS true" in sql:
            return _FixtureExecuteResult([])
        return _FixtureExecuteResult([self._inactive_complex_adv.adv_setting])


class _FixtureLoaderSessionContext:
    def __init__(self, inactive_complex_adv: ComplexAdv) -> None:
        self._session = _FixtureLoaderSession(inactive_complex_adv)

    async def __aenter__(self) -> _FixtureLoaderSession:
        return self._session

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        return None


def unwrap_coroutine(method: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    """Снять ``while_coroutine_decorator`` для одного тика в unit-тестах."""
    inner = getattr(method, "__wrapped__", None)
    if inner is None:
        return method  # type: ignore[return-value]
    return inner


def contains_adv_setting_identity(
    complex_advs: Sequence[ComplexAdv],
    adv_setting: AdvSetting,
) -> bool:
    """Проверить, что real builder вернул ComplexAdv именно для этой AdvSetting."""
    return any(adv.adv_setting is adv_setting for adv in complex_advs)


def make_fixture_loader_session_factory(
    inactive_complex_adv: ComplexAdv,
) -> Callable[..., _FixtureLoaderSessionContext]:
    """Собрать fake ``sm(...)`` для проверки loader-фильтра на конкретной fixture."""

    def _session_factory(*_: object, **__: object) -> _FixtureLoaderSessionContext:
        return _FixtureLoaderSessionContext(inactive_complex_adv)

    return _session_factory


def make_adv_setting(*, bot_active: bool = False, **overrides: object) -> AdvSetting:
    """AdvSetting через factory с включёнными auto-flags (leak detection)."""
    adv = AdvSettingFactory.build(
        bot_active=bot_active,
        adv_id=1001,
        id=1,
        nmids=[123456],
        active_status="started",
        auto_update_white_list=True,
        auto_update_target_place=True,
        individual_keywords_target_place_mode=True,
        automatic_version=2,
        auto_shelf_bid_control_enabled=True,
        updater_common_bid_in_search_adv_active_status=True,
        bidder_active=True,
        bidder_coroutine_type=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        white_list_mode=WhiteListMode.TAIL_TRIMMING,
        rec_system_mode=True,
        cpm=100,
        **overrides,
    )
    return adv


def make_search_adv(*, adv_id: int = 90001) -> AdvSetting:
    """Search-кампания для ComplexAdv (started, одна ставка)."""
    return AdvSettingFactory.build(
        adv_id=adv_id,
        active_status="started",
        cpm=90,
    )


def make_complex_adv(
    shop_id: str,
    adv_setting: AdvSetting,
    *,
    search_adv: AdvSetting | None = None,
) -> ComplexAdv:
    """ComplexAdv с пустым списком keywords (Redis miss не нужен в gate-тестах)."""

    async def _get_keywords(_: ComplexAdv, cache_only: bool = False) -> list[object]:
        return []

    return ComplexAdv(
        shop_id=shop_id,
        adv_setting=adv_setting,
        search_adv=search_adv or make_search_adv(),
        get_keywords_func=_get_keywords,
    )


def make_wb_api(access_mock: MagicMock, shop_id: str = "shop-gate-1") -> WBApi:
    """Минимальный WBApi для CoroutinesManager (использует access_mock с tokens)."""
    access_mock.shop_id = shop_id
    session = AsyncMock()
    session.close = MagicMock()
    return WBApi(access_mock, session)


def build_coroutines_manager(
    wb_api: WBApi,
    redis_client_wrapper: RedisClient,
    *,
    wb_manager_hub: MagicMock | None = None,
) -> CoroutinesManager:
    """CoroutinesManager с hub по умолчанию (WB clients — mock)."""
    hub = wb_manager_hub or MagicMock()
    hub.wb_data_manager = MagicMock()
    hub.wb_manager = MagicMock()
    hub.wb_modifier = MagicMock()
    return CoroutinesManager(
        wb_api,
        redis_client_wrapper,
        tasks_manager=TasksManager(max_workers=1),
        wb_manager_hub=hub,
    )
