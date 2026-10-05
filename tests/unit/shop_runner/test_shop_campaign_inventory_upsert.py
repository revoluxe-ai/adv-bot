"""Upsert inventory по WB discovery (задача 2.2).

Spec: ``connected-shop-campaign-ad-data-collection``, scenario «Завершённая
кампания в WB». Debt:
``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Доказывает issued SQL в ``default_db.shop_campaign_inventory`` на injected
клиенте. Живой ClickHouse и миграция 007 не используются: таблица на диск
есть, в рабочую БД не выкладывалась.

EVIDENCE_CLASS=side_effect_proof
PROVES=PA_SIDE_EFFECT_PROOF
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.unit

from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.get_adverts_adverts_item_status import (
    GetAdvertsAdvertsItemStatus,
)
from app.modules.shop_runner.shop_wide_collection.inventory_upsert import (
    ROUTE_NOT_ASSIGNED,
    DiscoveredWbCampaign,
    ShopCampaignInventoryWrite,
    discovered_campaign_from_advert,
    upsert_discovered_shop_campaign_inventory,
)

_SHOP_A = "shop-a"
_SHOP_B = "shop-b"
_T0 = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
_T1 = datetime(2026, 9, 27, 13, 0, 0, tzinfo=timezone.utc)
_REPO = Path(__file__).resolve().parents[3]


class _Nm:
    """Узкий nm payload WB, без полного generated DTO."""

    def __init__(self, nm_id: int) -> None:
        self.nm_id = nm_id


class _Advert:
    """Узкий advert payload: id, status, nm_settings."""

    def __init__(self, adv_id: int, status: int, nm_ids: tuple[int, ...] = ()) -> None:
        self.id = adv_id
        self.status = status
        self.nm_settings: tuple[_Nm, ...] = tuple(_Nm(nm_id) for nm_id in nm_ids)


class _QueryRowsResult:
    """Ответ ``query`` с ``result_rows``, как у CH-клиента."""

    def __init__(self, result_rows: Sequence[Sequence[object]]) -> None:
        self.result_rows = result_rows


class InMemoryInventoryClickHouse:
    """Память строк inventory с тем же grain, что SELECT argMax по version.

    Клиент стоит после causal boundary (маппинг lifecycle и решение, какую
    строку писать). Сам lifecycle и epoch он не вычисляет.
    """

    def __init__(self) -> None:
        self.queries: list[tuple[str, dict[str, object]]] = []
        self.rows: list[dict[str, object]] = []

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRowsResult:
        """Принять SELECT/INSERT inventory и вернуть текущие строки магазина."""
        params = dict(parameters or {})
        self.queries.append((query, params))
        stripped = query.strip()
        if stripped.startswith("SELECT"):
            return _QueryRowsResult(self._select(query, params))
        if stripped.startswith("INSERT INTO"):
            self._require_inventory_insert(query)
            self.rows.append(dict(params))
            return _QueryRowsResult(())
        raise AssertionError(f"unexpected query: {query}")

    def _select(
        self, query: str, params: Mapping[str, object]
    ) -> list[tuple[object, ...]]:
        if "FROM default_db.shop_campaign_inventory" not in query:
            raise AssertionError(
                "select must qualify default_db.shop_campaign_inventory"
            )
        if "shop_id = %(shop_id)s" not in query:
            raise AssertionError("select must scope shop_id")
        shop_id = params["shop_id"]
        raw_ids = params["adv_ids"]
        if not isinstance(raw_ids, list):
            raise AssertionError("adv_ids must be a list")
        adv_ids: set[int] = set()
        for item in cast(Sequence[object], raw_ids):
            if isinstance(item, bool) or not isinstance(item, int):
                raise AssertionError("adv_id must be int")
            adv_ids.add(item)
        latest: dict[int, dict[str, object]] = {}
        for row in self.rows:
            adv_id = row["adv_id"]
            if row["shop_id"] != shop_id or adv_id not in adv_ids:
                continue
            if not isinstance(adv_id, int):
                raise AssertionError("stored adv_id must be int")
            current = latest.get(adv_id)
            if current is None or _version(row) >= _version(current):
                latest[adv_id] = row
        return [
            (
                row["adv_id"],
                row["route"],
                row["route_version"],
                row["version"],
                row["discovered_at"],
            )
            for row in latest.values()
        ]

    @staticmethod
    def _require_inventory_insert(query: str) -> None:
        if "INSERT INTO default_db.shop_campaign_inventory" not in query:
            raise AssertionError(
                "insert must qualify default_db.shop_campaign_inventory"
            )
        bare = query.replace("INSERT INTO default_db.shop_campaign_inventory", "")
        if "INSERT INTO shop_campaign_inventory" in bare:
            raise AssertionError("unqualified inventory insert")


def _version(row: Mapping[str, object]) -> int:
    value = row["version"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError("version must be int")
    return value


def _inserts(client: InMemoryInventoryClickHouse) -> list[dict[str, object]]:
    return [
        params
        for query, params in client.queries
        if query.strip().startswith("INSERT")
    ]


def _by_adv(
    written: Sequence[ShopCampaignInventoryWrite],
) -> dict[int, ShopCampaignInventoryWrite]:
    return {row.adv_id: row for row in written}


def _forbid(*_args: object, **_kwargs: object) -> Any:
    raise AssertionError("forbidden side effect")


@pytest.fixture
def forbid_foreign_writers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Падает, если upsert откроет свой CH, Redis epoch или management write.

    Spec запрещает ``update_advs_in_db`` ради discovery и второй SoT epoch
    в Redis. Узкий patch на класс/функцию, не на module attribute вокруг await.
    """
    monkeypatch.setattr(
        "app.utils.click_house.client.get_clickhouse_client",
        _forbid,
    )
    monkeypatch.setattr(
        "app.modules.common_slaves.wildberries.wb_db_manager.update_advs_in_db",
        _forbid,
    )
    monkeypatch.setattr(
        "app.core.redis_manager_v2.redis_client.RedisClient",
        _forbid,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.ApplyManager",
        _forbid,
    )


def test_inventory_upsert_is_wired_via_shop_runner_tick() -> None:
    """§8.1: shop-runner tick вызывает unmanaged orchestrator с inventory upsert.

    Spec ``connected-shop-campaign-ad-data-collection``: dual-path через
    ``WBShop.run`` → ``collect_shop_wide_campaign_advertising`` →
    ``tick_wiring.run_shop_wide_unmanaged_tick``. scripts/Job не primary executor.
    """
    wb_shop = (_REPO / "app" / "modules" / "shop_runner" / "wb_shop.py").read_text(
        encoding="utf-8"
    )
    manager = (
        _REPO / "app" / "modules" / "shop_runner" / "service_manager" / "manager.py"
    ).read_text(encoding="utf-8")
    tick_wiring = (
        _REPO
        / "app"
        / "modules"
        / "shop_runner"
        / "shop_wide_collection"
        / "tick_wiring.py"
    ).read_text(encoding="utf-8")
    assert "collect_shop_wide_campaign_advertising" in wb_shop
    assert "collect_shop_wide_campaign_advertising" in manager
    assert "run_shop_wide_unmanaged_tick" in manager
    assert "collect_unmanaged_campaign_advertising" in tick_wiring
    assert "apply_shop_wide_collection_gate" in wb_shop
    assert not list((_REPO / "scripts").glob("collect_shop_wide_adv.py"))


async def test_finished_and_unmapped_campaigns_are_upserted(
    forbid_foreign_writers: None,
) -> None:
    """S03: завершённая кампания пишется; неизвестный статус — ``unknown``.

    Spec ``connected-shop-campaign-ad-data-collection``: lifecycle finished
    остаётся в shop-wide discovery и не отсекается из-за отсутствия
    management. Коды вне active/paused/finished не выкидываются.

    EVIDENCE_CLASS=side_effect_proof. Падает, если finished или unknown
    перестанут попадать в INSERT ``default_db.shop_campaign_inventory``.
    """
    del forbid_foreign_writers
    finished = discovered_campaign_from_advert(
        _Advert(700, int(GetAdvertsAdvertsItemStatus.VALUE_7), ())
    )
    active = discovered_campaign_from_advert(
        _Advert(900, int(GetAdvertsAdvertsItemStatus.VALUE_9), (11,))
    )
    paused = discovered_campaign_from_advert(
        _Advert(1100, int(GetAdvertsAdvertsItemStatus.VALUE_11), (12, 13))
    )
    unmapped = (
        DiscoveredWbCampaign(801, int(GetAdvertsAdvertsItemStatus.VALUE_8), ()),
        DiscoveredWbCampaign(401, int(GetAdvertsAdvertsItemStatus.VALUE_4), ()),
        DiscoveredWbCampaign(
            -101, int(GetAdvertsAdvertsItemStatus.VALUE_NEGATIVE_1), ()
        ),
        DiscoveredWbCampaign(9901, None, (1,)),
        DiscoveredWbCampaign(12345, 99, ()),
    )
    client = InMemoryInventoryClickHouse()
    written = await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_A,
        campaigns=(finished, active, paused, *unmapped),
        observed_at=_T0,
    )
    by_adv = _by_adv(written)
    assert set(by_adv) == {700, 900, 1100, 801, 401, -101, 9901, 12345}
    assert by_adv[700].wb_lifecycle == "finished"
    assert by_adv[700].wb_status == "7"
    assert by_adv[700].nm_ids == ()
    assert by_adv[700].route == ROUTE_NOT_ASSIGNED
    assert by_adv[700].route_version == 0
    assert by_adv[900].wb_lifecycle == "active"
    assert by_adv[900].nm_ids == (11,)
    assert by_adv[1100].wb_lifecycle == "paused"
    assert by_adv[1100].nm_ids == (12, 13)
    for adv_id in (801, 401, -101, 9901, 12345):
        assert by_adv[adv_id].wb_lifecycle == "unknown"
    assert by_adv[9901].wb_status == ""
    assert all(row.shop_id == _SHOP_A for row in written)
    insert_queries = [
        query for query, _params in client.queries if "INSERT INTO" in query
    ]
    assert len(insert_queries) == len(by_adv)
    for query in insert_queries:
        assert "INSERT INTO default_db.shop_campaign_inventory" in query
        assert "route_version" in query
        assert "redis" not in query.lower()
        for foreign in (
            "full_adv_wb_stat",
            "wb_common_stat",
            "clusters_adv_stats",
            "shop_campaign_collection_availability",
        ):
            assert foreign not in query


async def test_repeat_upsert_preserves_route_epoch_until_route_changes(
    forbid_foreign_writers: None,
) -> None:
    """Повтор discovery не двигает ``route_version`` и не пишет Redis.

    Design §D.1 / §C: epoch — только колонка inventory. ``version`` растёт
    на каждый upsert. Явный route от вызывающего (не от этого модуля)
    увеличивает epoch на 1. Повтор того же route epoch не меняет.
    """
    del forbid_foreign_writers
    campaign = DiscoveredWbCampaign(
        700,
        int(GetAdvertsAdvertsItemStatus.VALUE_7),
        (5,),
    )
    client = InMemoryInventoryClickHouse()
    first = await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_A,
        campaigns=(campaign,),
        observed_at=_T0,
    )
    second = await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_A,
        campaigns=(campaign,),
        observed_at=_T1,
    )
    assert first[0].route_version == 0
    assert second[0].route_version == 0
    assert second[0].version == 2
    assert second[0].discovered_at == first[0].discovered_at
    assert second[0].last_seen_at != first[0].last_seen_at
    assert second[0].route == ROUTE_NOT_ASSIGNED

    third = await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_A,
        campaigns=(campaign,),
        routes={700: "UNMANAGED"},
        observed_at=_T1,
    )
    assert third[0].route == "UNMANAGED"
    assert third[0].route_version == 1
    assert third[0].version == 3

    fourth = await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_A,
        campaigns=(campaign,),
        routes={700: "UNMANAGED"},
        observed_at=_T1,
    )
    assert fourth[0].route_version == 1
    assert fourth[0].version == 4
    assert all("redis" not in query.lower() for query, _params in client.queries)


async def test_same_adv_id_in_another_shop_starts_its_own_epoch(
    forbid_foreign_writers: None,
) -> None:
    """Строка inventory принадлежит ``shop_id``: чужой магазин не продолжает version.

    Spec держит inventory ключом ``(shop_id, adv_id)``. SELECT обязан
    передавать shop_id, иначе epoch одного магазина протечёт в другой.
    """
    del forbid_foreign_writers
    campaign = DiscoveredWbCampaign(700, 7, ())
    client = InMemoryInventoryClickHouse()
    await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_A,
        campaigns=(campaign,),
        routes={700: "UNMANAGED"},
        observed_at=_T0,
    )
    written_b = await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_B,
        campaigns=(campaign,),
        observed_at=_T1,
    )
    assert written_b[0].shop_id == _SHOP_B
    assert written_b[0].version == 1
    assert written_b[0].route_version == 0
    assert written_b[0].route == ROUTE_NOT_ASSIGNED
    selects = [
        params
        for query, params in client.queries
        if query.strip().startswith("SELECT")
    ]
    assert [params["shop_id"] for params in selects] == [_SHOP_A, _SHOP_B]


async def test_empty_discovery_issues_no_sql(forbid_foreign_writers: None) -> None:
    """Пустой список кампаний не создаёт SELECT и INSERT.

    Spec не требует строки-заглушки, когда WB ничего не вернул.
    """
    del forbid_foreign_writers
    client = InMemoryInventoryClickHouse()
    written = await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_A,
        campaigns=(),
        observed_at=_T0,
    )
    assert written == ()
    assert client.queries == []


async def test_duplicate_adv_id_in_one_batch_keeps_the_last_payload(
    forbid_foreign_writers: None,
) -> None:
    """Два payload одного adv_id в одном discovery дают одну строку.

    Последний статус побеждает, кампания не пропадает и не двоится.
    """
    del forbid_foreign_writers
    client = InMemoryInventoryClickHouse()
    written = await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_A,
        campaigns=(
            DiscoveredWbCampaign(700, 9, (1,)),
            DiscoveredWbCampaign(700, 7, (2, 3)),
        ),
        observed_at=_T0,
    )
    assert len(written) == 1
    assert written[0].wb_lifecycle == "finished"
    assert written[0].nm_ids == (2, 3)
    assert len(_inserts(client)) == 1


async def test_clickhouse_errors_propagate(forbid_foreign_writers: None) -> None:
    """Сбой клиента не превращается в пустой discovery.

    Spec: неизвестность и ошибка не маскируются под «кампаний нет».
    """
    del forbid_foreign_writers

    class _Broken:
        async def query(
            self,
            query: str,
            parameters: Mapping[str, object] | None = None,
        ) -> _QueryRowsResult:
            del query, parameters
            raise RuntimeError("clickhouse unavailable")

    with pytest.raises(RuntimeError, match="clickhouse unavailable"):
        await upsert_discovered_shop_campaign_inventory(
            _Broken(),
            shop_id=_SHOP_A,
            campaigns=(DiscoveredWbCampaign(700, 7, ()),),
            observed_at=_T0,
        )


def test_map_inputs_used_by_upsert_cover_wb_status_enum() -> None:
    """Коды generated-клиента WB совпадают с осью lifecycle inventory.

    Spec называет active/paused/finished. Остальные значения enum WB
    остаются ``unknown`` и проверяются вместе с upsert, не вместо него.
    """
    assert int(GetAdvertsAdvertsItemStatus.VALUE_9) == 9
    assert int(GetAdvertsAdvertsItemStatus.VALUE_11) == 11
    assert int(GetAdvertsAdvertsItemStatus.VALUE_7) == 7
    assert int(GetAdvertsAdvertsItemStatus.VALUE_8) == 8
    assert int(GetAdvertsAdvertsItemStatus.VALUE_4) == 4
    assert int(GetAdvertsAdvertsItemStatus.VALUE_NEGATIVE_1) == -1


async def test_missing_route_key_does_not_drop_campaign(
    forbid_foreign_writers: None,
) -> None:
    """Маршрут передан соседу, а finished id в map нет — строка всё равно пишется.

    Задача 3.1 ещё не резолвер. Пропуск ключа в ``routes`` не фильтр universe.
    Spec ``connected-shop-campaign-ad-data-collection``: отсутствие management
    route не исключает завершённую кампанию из discovery upsert.
    """
    del forbid_foreign_writers
    client = InMemoryInventoryClickHouse()
    written = await upsert_discovered_shop_campaign_inventory(
        client,
        shop_id=_SHOP_A,
        campaigns=(
            DiscoveredWbCampaign(700, 7, ()),
            DiscoveredWbCampaign(900, 9, ()),
        ),
        routes={900: "UNMANAGED"},
        observed_at=_T0,
    )
    by_adv = _by_adv(written)
    assert set(by_adv) == {700, 900}
    assert by_adv[700].wb_lifecycle == "finished"
    assert by_adv[700].route == ROUTE_NOT_ASSIGNED
    assert by_adv[700].route_version == 0
    assert by_adv[900].route == "UNMANAGED"
    assert by_adv[900].route_version == 1
