"""LEGACY_BASELINE и write-gate RECORD-сбора shop-runner.

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Секция 1 change ``shop-wide-campaign-data-collection`` фиксирует текущий
managed universe до расширения shop-wide: RECORD-корутины берут только
``ComplexAdv`` из loader'а, predicate ``__get_advs`` оставляет ``refused`` и
отсекает ``done``, а тела full/common/clusters не доходят до management write.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import BindParameter, BinaryExpression, False_, True_

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager import (
    ApplyManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.wb_shop import WBShop
from app.modules.wb_adv_updater import data_manager

# WB-only id нет в loader ComplexAdv. RECORD collectors не должны его увидеть.
_WB_ONLY_ADV_ID = 999_001
_PARENT_ADV_ID = 101
_SEARCH_ADV_ID = 202
_SHOP_ID = "shop-legacy-baseline"

_RECORD_COROUTINES = (
    "update_common_sale_stat",
    "update_full_adv_stat",
    "update_clusters_adv_stats_today",
    "update_clusters_adv_stats_history",
)


class _FakeTaskGroup:
    """TaskGroup, который только фиксирует create_task и не исполняет корутины."""

    def __init__(self) -> None:
        self.created: list[Any] = []

    async def __aenter__(self) -> _FakeTaskGroup:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def create_task(self, coro: Any) -> MagicMock:
        """Сохранить аргумент create_task. Реальный цикл shop-runner здесь не идёт."""
        self.created.append(coro)
        return MagicMock()


class _CapturingSession:
    """Сессия, которая сохраняет statement ``__get_advs`` и отдаёт заданные строки."""

    def __init__(self, rows: list[Any]) -> None:
        self.statements: list[Any] = []
        self._rows = rows

    async def execute(self, stmt: Any) -> Any:
        """Записать SQLAlchemy statement и вернуть scalars без живой PG."""
        self.statements.append(stmt)
        result = MagicMock()
        result.scalars.return_value.all.return_value = self._rows
        return result


class _RecordingClustersUpdater:
    """Тонкий конец clusters: запоминает ComplexAdv, которые дошли из loader'а."""

    def __init__(self) -> None:
        self.today: list[list[ComplexAdv]] = []
        self.history: list[tuple[list[ComplexAdv], int]] = []

    async def update_today_stats(
        self, complex_advs: list[ComplexAdv]
    ) -> list[int]:
        """Принять сегодняшний universe и не писать CH."""
        self.today.append(list(complex_advs))
        return []

    async def update_past_days_stats(
        self, complex_advs: list[ComplexAdv], for_last_days: int
    ) -> None:
        """Принять исторический universe и не писать CH."""
        self.history.append((list(complex_advs), for_last_days))


class _RecordingCommonUpdater:
    """Тонкий конец common stat: запоминает ComplexAdv до CH/funnel write."""

    def __init__(self) -> None:
        self.batches: list[list[ComplexAdv]] = []

    async def update_last_week_stats(self, advs: list[ComplexAdv]) -> list[int]:
        """Принять nmid-universe loader'а и не писать воронку."""
        self.batches.append(list(advs))
        return []


def _bind_value(element: Any) -> Any:
    """Достать литерал сравнения: bind, ``true``/``false`` или сам узел."""
    if isinstance(element, BindParameter):
        return element.value
    if isinstance(element, True_):
        return True
    if isinstance(element, False_):
        return False
    return element


def _column_key(expression: BinaryExpression) -> str | None:
    """Имя колонки слева в сравнении predicate ``__get_advs``."""
    left = expression.left
    key = getattr(left, "key", None)
    if isinstance(key, str):
        return key
    element = getattr(left, "element", None)
    element_key = getattr(element, "key", None)
    if isinstance(element_key, str):
        return element_key
    return None


def _binary_by_column(stmt: Any) -> dict[str, list[BinaryExpression]]:
    """Собрать реальные сравнения statement, построенного ``__get_advs``."""
    found: dict[str, list[BinaryExpression]] = {}
    for element in visitors.iterate(stmt):
        if not isinstance(element, BinaryExpression):
            continue
        key = _column_key(element)
        if key is None:
            continue
        found.setdefault(key, []).append(element)
    return found


def _comparison_holds(expression: BinaryExpression, left_value: Any) -> bool:
    """Применить оператор из statement к значению строки.

    ``!=`` вызывается как обычный оператор. ``IS`` в SQLAlchemy делает
    ``left.is_(right)`` и на голом bool падает: для него смысл тот же, что
    Python ``is`` с захваченным правым литералом.
    """
    right = _bind_value(expression.right)
    operator = expression.operator
    if getattr(operator, "__name__", "") == "is_":
        return left_value is right
    return bool(operator(left_value, right))


def _setting(
    *,
    adv_id: int,
    nmids: list[int],
    active_status: str,
    bot_active: bool,
    setting_id: int,
) -> MagicMock:
    """Минимальная форма AdvSetting для ComplexAdv без живой PG-строки."""
    row = MagicMock(spec=AdvSetting)
    row.adv_id = adv_id
    row.id = setting_id
    row.nmids = list(nmids)
    row.active_status = active_status
    row.bot_active = bot_active
    row.search_adv_id = None
    row.plan_for_sales_for_day = None
    row.target_price_for_order = None
    row.max_price_for_order = None
    return row


def _loader_complex_adv() -> ComplexAdv:
    """Один refused parent с search-ногой: так loader отдаёт RECORD universe."""
    parent = _setting(
        adv_id=_PARENT_ADV_ID,
        nmids=[555],
        active_status="refused",
        bot_active=False,
        setting_id=1,
    )
    search = _setting(
        adv_id=_SEARCH_ADV_ID,
        nmids=[555],
        active_status="refused",
        bot_active=False,
        setting_id=2,
    )
    return ComplexAdv(
        shop_id=_SHOP_ID,
        adv_setting=parent,
        search_adv=search,
        target_pay_for_order=None,
    )


def _create_manager(access_mock: Any, fake_redis: Any) -> CoroutinesManager:
    """CoroutinesManager с подменённым hub: PG/WB/CH наружу не ходят."""
    access_mock.shop_id = _SHOP_ID
    access_mock.wb_cabinet.shop_id = _SHOP_ID
    wb_api = WBApi(access_mock, MagicMock())
    hub = MagicMock()
    hub.wb_data_manager = MagicMock()
    hub.wb_manager = MagicMock()
    hub.wb_modifier = MagicMock()
    plan_fact_reader = MagicMock()
    plan_fact_reader.get_latest_plan_fact = MagicMock()
    return CoroutinesManager(
        wb_api,
        RedisClient(redis_client=fake_redis),
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=plan_fact_reader,
        wb_manager_hub=hub,
    )


async def _run_record_collectors(
    manager: CoroutinesManager,
    loader_adv: ComplexAdv,
    monkeypatch: pytest.MonkeyPatch,
) -> SimpleNamespace:
    """Прогнать тела RECORD-корутин один раз через реальный id-сбор.

    ``get_complex_advs`` — вход loader'а. Агрегация id и вызов thin end остаются
    production-кодом. ``__wrapped__`` снимает бесконечный ``while_coroutine``.
    """
    forbidden: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    async def _forbid(name: str, *args: Any, **kwargs: Any) -> None:
        forbidden.append((name, args, kwargs))

    def _forbid_init(name: str, *args: Any, **kwargs: Any) -> None:
        forbidden.append((name, args, kwargs))

    clusters = _RecordingClustersUpdater()
    common = _RecordingCommonUpdater()
    full_ids: set[int] = set()

    async def _get_full_adv_stat(
        _data_manager: Any,
        adv_ids: set[int] | list[int],
        threshold_dates: Any = None,
    ) -> list[Any]:
        full_ids.update(int(adv_id) for adv_id in adv_ids)
        _ = threshold_dates
        return []

    async def _refuse_ch_insert(_stats: Any) -> None:
        forbidden.append(("full_wb_adv_stat.insert", (_stats,), {}))

    async def _get_complex_advs(**kwargs: Any) -> list[ComplexAdv]:
        assert kwargs["only_bot_active"] is False
        assert kwargs["load_extras"] is False
        return [loader_adv]

    manager._wb_shop_data_manager.get_complex_advs = _get_complex_advs  # type: ignore[method-assign]
    # Атрибут не читается текущим collector: если код начнёт сливать его в universe, тест упадёт.
    manager._wb_shop_data_manager.wb_only_discovered_ids = {_WB_ONLY_ADV_ID}  # type: ignore[attr-defined]

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.manager.wb_data_getter.get_full_adv_stat_for_adv_ids",
        _get_full_adv_stat,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.manager.full_wb_adv_stat.insert",
        _refuse_ch_insert,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.manager.ClustersAdvStatUpdaterContainer",
        lambda **_kwargs: SimpleNamespace(
            clusters_adv_stat_updater=lambda: clusters
        ),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.common_sale_stat_updater.CommonSaleStatUpdaterContainer",
        lambda **_kwargs: SimpleNamespace(
            common_sale_stat_updater=lambda: common
        ),
    )
    async def _forbid_sync_from_wb(*args: Any, **kwargs: Any) -> None:
        await _forbid("data_manager.update_advs_data_from_wb_to_pg", *args, **kwargs)

    monkeypatch.setattr(
        data_manager,
        "update_advs_data_from_wb_to_pg",
        _forbid_sync_from_wb,
    )

    async def _forbid_update_advs_in_db(*args: Any, **kwargs: Any) -> None:
        await _forbid("wb_db_manager.update_advs_in_db", *args, **kwargs)

    monkeypatch.setattr(
        "app.modules.common_slaves.wildberries.wb_db_manager.update_advs_in_db",
        _forbid_update_advs_in_db,
    )
    monkeypatch.setattr(
        ShopDataUpdater,
        "__init__",
        lambda self, *args, **kwargs: _forbid_init(
            "ShopDataUpdater.__init__", *args, **kwargs
        ),
    )
    async def _forbid_shop_update(self: Any, *args: Any, **kwargs: Any) -> None:
        await _forbid("ShopDataUpdater.update_advs_data", *args, **kwargs)

    monkeypatch.setattr(ShopDataUpdater, "update_advs_data", _forbid_shop_update)

    async def _forbid_apply(self: Any, *args: Any, **kwargs: Any) -> None:
        await _forbid("ApplyManager.apply", *args, **kwargs)

    monkeypatch.setattr(ApplyManager, "apply", _forbid_apply)

    created: list[Any] = []

    def _spy_adv_setting_init(self: Any, *args: Any, **kwargs: Any) -> None:
        created.append(self)
        forbidden.append(("AdvSetting.__init__", args, kwargs))

    monkeypatch.setattr(AdvSetting, "__init__", _spy_adv_setting_init)

    await manager.update_full_adv_stat.__wrapped__(  # type: ignore[attr-defined]
        manager, only_bot_active=False
    )
    await manager.update_common_sale_stat.__wrapped__(  # type: ignore[attr-defined]
        manager, only_bot_active=False
    )
    await manager.update_clusters_adv_stats_today.__wrapped__(  # type: ignore[attr-defined]
        manager, only_bot_active=False
    )
    await manager.update_clusters_adv_stats_history.__wrapped__(  # type: ignore[attr-defined]
        manager, only_bot_active=False
    )

    return SimpleNamespace(
        full_ids=full_ids,
        common_batches=common.batches,
        clusters_today=clusters.today,
        clusters_history=clusters.history,
        forbidden=forbidden,
        loader_ids=set(loader_adv.all_adv_ids),
    )


def _ids_of(advs: list[ComplexAdv]) -> set[int]:
    """Собрать all_adv_ids пачки, которую collector передал в thin end."""
    found: set[int] = set()
    for adv in advs:
        found.update(int(adv_id) for adv_id in adv.all_adv_ids)
    return found


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wb_shop_run_record_coroutines_only_bot_active_false(
    access_mock: Any,
    fake_redis: Any,
) -> None:
    """Tick ``WBShop.run`` запускает RECORD с ``only_bot_active=False``.

    Spec ``connected-shop-campaign-ad-data-collection``, контраст S01: сегодня
    universe задаёт loader, а не отдельный Job. Флаг нужен, чтобы ``refused`` и
    ``bot_active=False`` не выпадали из RECORD до shop-wide expansion.
    """
    access_mock.shop_id = _SHOP_ID
    wb_api = MagicMock(spec=WBApi)
    wb_api.shop_id = _SHOP_ID
    redis_manager = MagicMock(spec=RedisShopManager)
    redis_manager.DEFAULT_TTL = 60
    shop = WBShop(
        wb_api,
        redis_manager,
        RedisClient(redis_client=fake_redis),
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=MagicMock(),
        wb_manager_hub=MagicMock(),
    )
    shop._alive_worker_run = MagicMock(return_value=None)  # type: ignore[method-assign]

    with (
        patch("app.modules.shop_runner.wb_shop.CoroutinesManager") as manager_cls,
        patch("asyncio.TaskGroup", new=_FakeTaskGroup),
    ):
        await shop.run()

    instance = manager_cls.return_value
    for name in _RECORD_COROUTINES:
        call = getattr(instance, name).call_args
        assert call is not None, name
        assert call.kwargs["only_bot_active"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_record_collectors_take_loader_ids_not_wb_only(
    access_mock: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RECORD collectors получают только ``all_adv_ids`` loader ComplexAdv.

    Spec ``connected-shop-campaign-ad-data-collection``. WB-only id не входит в
    full/common/clusters, пока universe не расширен. ``bot_active=False`` у
    refused-строки не выкидывает её из этого прогона.
    """
    loader_adv = _loader_complex_adv()
    assert loader_adv.bot_active is False
    manager = _create_manager(access_mock, fake_redis)
    trace = await _run_record_collectors(manager, loader_adv, monkeypatch)

    assert trace.loader_ids == {_PARENT_ADV_ID, _SEARCH_ADV_ID}
    assert _WB_ONLY_ADV_ID not in trace.loader_ids
    assert trace.full_ids == trace.loader_ids
    assert _WB_ONLY_ADV_ID not in trace.full_ids
    assert len(trace.common_batches) == 1
    assert _ids_of(trace.common_batches[0]) == trace.loader_ids
    assert trace.common_batches[0][0] is loader_adv
    assert len(trace.clusters_today) == 1
    assert trace.clusters_today[0][0] is loader_adv
    assert _ids_of(trace.clusters_today[0]) == trace.loader_ids
    assert len(trace.clusters_history) == 1
    history_advs, for_last_days = trace.clusters_history[0]
    assert history_advs[0] is loader_adv
    assert for_last_days == 365
    assert _ids_of(history_advs) == trace.loader_ids
    assert loader_adv.bot_active is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_advs_predicate_includes_refused_and_excludes_done() -> None:
    """``__get_advs`` при ``only_bot_active=False`` оставляет refused и режет done.

    Spec ``connected-shop-campaign-ad-data-collection``, design §B.1. Фильтр — это
    SQL statement метода, не копия условия в тесте. Python-хвост не выкидывает
    refused-строку, которую сессия вернула.
    """
    refused = MagicMock(spec=AdvSetting)
    refused.active_status = "refused"
    session = _CapturingSession([refused])
    # Имя __get_advs манглится классом; вызываем тот же staticmethod, что loader.
    rows = await WBShopDataManager._WBShopDataManager__get_advs(  # type: ignore[attr-defined]
        session, _SHOP_ID, False
    )

    assert rows == [refused]
    assert len(session.statements) == 1
    by_column = _binary_by_column(session.statements[0])
    status_preds = by_column["active_status"]
    assert len(status_preds) == 1
    assert _bind_value(status_preds[0].right) == "done"
    assert _comparison_holds(status_preds[0], "refused") is True
    assert _comparison_holds(status_preds[0], "active") is True
    assert _comparison_holds(status_preds[0], "done") is False
    assert "bot_active" not in by_column
    shop_preds = by_column["shop_id"]
    assert _bind_value(shop_preds[0].right) == _SHOP_ID
    bind_values = [
        element.value
        for element in visitors.iterate(session.statements[0])
        if isinstance(element, BindParameter)
    ]
    assert "refused" not in bind_values
    assert "done" in bind_values


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_advs_only_bot_active_true_adds_bot_active_filter() -> None:
    """Парный случай: ``only_bot_active=True`` добавляет ``bot_active``, не меняя done.

    RECORD shop-wide этот флаг не ставит. Тест держит отличие billing-фильтра от
    predicate ``active_status != 'done'`` (design §B.1, §B.3).
    """
    refused = MagicMock(spec=AdvSetting)
    refused.active_status = "refused"
    refused.bot_active = False
    session = _CapturingSession([refused])
    rows = await WBShopDataManager._WBShopDataManager__get_advs(  # type: ignore[attr-defined]
        session, _SHOP_ID, True
    )

    assert rows == [refused]
    by_column = _binary_by_column(session.statements[0])
    assert _comparison_holds(by_column["active_status"][0], "refused") is True
    assert _comparison_holds(by_column["active_status"][0], "done") is False
    bot_preds = by_column["bot_active"]
    assert len(bot_preds) == 1
    assert _comparison_holds(bot_preds[0], False) is False
    assert _comparison_holds(bot_preds[0], True) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_complex_advs_post_filter_drops_empty_nmids() -> None:
    """Post-filter ``get_complex_advs`` оставляет только ComplexAdv с nmids.

    Spec ``connected-shop-campaign-ad-data-collection``, design §B.1. Пустой
    ``nmids`` отсекается реальным циклом метода; ``refused`` с nmids остаётся.
    ``get_pre_complex_advs`` — вход, не фильтр.
    """
    cabinet = MagicMock()
    cabinet.shop_id = _SHOP_ID
    data_manager_obj = WBShopDataManager(
        cabinet,
        tasks_manager=TasksManager(max_workers=1),
        wb_api_data_manager=MagicMock(),
        wb_manager=MagicMock(),
        plan_fact_reader=MagicMock(),
    )
    kept_setting = _setting(
        adv_id=_PARENT_ADV_ID,
        nmids=[555],
        active_status="refused",
        bot_active=False,
        setting_id=11,
    )
    empty_setting = _setting(
        adv_id=_WB_ONLY_ADV_ID,
        nmids=[],
        active_status="started",
        bot_active=True,
        setting_id=12,
    )

    async def _pre(
        *, only_bot_active: bool, skip_plan_fact: bool = False
    ) -> list[PreComplexAdv]:
        assert only_bot_active is False
        assert skip_plan_fact is False
        return [
            PreComplexAdv(auto_adv=kept_setting, plan_data=None),
            PreComplexAdv(auto_adv=empty_setting, plan_data=None),
        ]

    data_manager_obj.get_pre_complex_advs = _pre  # type: ignore[method-assign]
    loaded = await data_manager_obj.get_complex_advs(
        only_bot_active=False,
        load_extras=False,
    )

    assert [adv.adv_id for adv in loaded] == [_PARENT_ADV_ID]
    assert loaded[0].nmids == [555]
    assert loaded[0].bot_active is False
    assert _WB_ONLY_ADV_ID not in {adv.adv_id for adv in loaded}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_record_collectors_do_not_reach_forbidden_management_writes(
    access_mock: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RECORD collection не доходит до discovery/management write.

    Spec ``connected-shop-campaign-ad-data-collection`` (L8, S10, S21).
    Запрещённые адаптеры стоят на границе: если тело full/common/clusters их
    вызовет, вызов попадёт в trace. Разрешённый путь — те же loader id на stat
    thin end. ``bot_active`` refused-строки не меняется. Отдельная корутина
    ``update_advs_data_from_wb_to_pg`` в этот прогон не входит: она не является
    RECORD collector.
    """
    loader_adv = _loader_complex_adv()
    manager = _create_manager(access_mock, fake_redis)
    trace = await _run_record_collectors(manager, loader_adv, monkeypatch)

    assert trace.forbidden == []
    assert trace.full_ids == {_PARENT_ADV_ID, _SEARCH_ADV_ID}
    assert _WB_ONLY_ADV_ID not in trace.full_ids
    assert loader_adv._adv_setting.bot_active is False
    assert loader_adv._search_adv is not None
    assert loader_adv._search_adv.bot_active is False
