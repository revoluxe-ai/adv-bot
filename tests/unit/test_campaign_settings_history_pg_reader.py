"""PostgreSQL settings reader tests without a database."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.modules.campaign_settings_contract import (
    HistoryPolicy,
    NormalizationPolicy,
    REGISTERED_SOURCES,
)
from app.modules.campaign_settings_history.pg_reader import (
    PostgresCampaignSettingsReader,
)

pytestmark = pytest.mark.unit


def _sample(policy, field_name: str):
    if policy.allowed_values:
        return policy.allowed_values[0]
    norm = policy.normalization
    if norm is NormalizationPolicy.INT:
        return 1
    if norm is NormalizationPolicy.FLOAT:
        return 1.0
    if norm is NormalizationPolicy.BOOL:
        return False
    if norm is NormalizationPolicy.STRING:
        return "Europe/Moscow" if field_name == "timezone" else field_name
    if norm is NormalizationPolicy.INT_LIST:
        return [11, 22]
    if norm is NormalizationPolicy.STRING_LIST:
        return []
    if norm is NormalizationPolicy.JSON_OBJECT:
        return {}
    if norm is NormalizationPolicy.DATE:
        return date(2026, 1, 1)
    raise AssertionError(norm)


def _source_obj(source: str, **extra):
    values = {}
    for name, policy in REGISTERED_SOURCES[source].fields.items():
        if policy.history is not HistoryPolicy.EXCLUDED:
            values[name] = _sample(policy, name)
    values.update(extra)
    return SimpleNamespace(**values)


class _ScalarView:
    def __init__(self, values):
        self._values = list(values)

    def unique(self):
        return self

    def all(self):
        return list(self._values)


class _Result:
    def __init__(self, *, scalars=None, scalar_one=None, rows=None):
        self._scalars = list(scalars or [])
        self._scalar_one = scalar_one
        self._rows = list(rows or [])

    def scalars(self):
        return _ScalarView(self._scalars)

    def scalar_one(self):
        return self._scalar_one

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.statements: list[str] = []

    async def execute(self, statement):
        self.statements.append(str(statement))
        if not self._results:
            raise AssertionError("unexpected SQL execute")
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_discovery_reads_distinct_pg_owners_without_active_filters() -> None:
    session = _FakeSession([_Result(scalars=[3, 9, 11])])
    reader = PostgresCampaignSettingsReader(session)  # type: ignore[arg-type]

    assert await reader.discover_cabinet_ids() == (3, 9, 11)
    sql = session.statements[0].lower()
    assert "distinct" in sql
    assert "wb_cabinet_id" in sql
    assert "bot_active" not in sql
    assert "active_status" not in sql
    assert "redis" not in sql


@pytest.mark.asyncio
async def test_load_cabinet_uses_bounded_batch_queries_and_effective_search_id() -> None:
    adv = _source_obj(
        "AdvSetting",
        id=101,
        wb_cabinet_id=77,
        adv_id=1001,
        _search_adv_id=None,
        search_adv_id=2002,
        nmids=[22, 11, 22],
        active_status="paused",
        bot_active=False,
    )
    keyword = _source_obj(
        "KeywordSetting",
        adv_setting_id=101,
        text="alpha",
    )
    shelf_11 = _source_obj(
        "AutoShelfBidControlSettings",
        nmid=11,
    )
    shelf_22 = _source_obj(
        "AutoShelfBidControlSettings",
        nmid=22,
    )
    time_row = _source_obj(
        "AdvTimeSettings",
        adv_setting_id=101,
    )
    mask = _source_obj(
        "AdvTimeWeekMask",
        adv_setting_id=101,
        dow=1,
        hours_mask=7,
    )
    session = _FakeSession(
        [
            _Result(scalar_one="shop-77"),
            _Result(scalars=[adv]),
            _Result(scalars=[keyword]),
            _Result(scalars=[shelf_11, shelf_22]),
            _Result(scalars=[time_row]),
            _Result(scalars=[mask]),
        ]
    )
    reader = PostgresCampaignSettingsReader(session)  # type: ignore[arg-type]

    batch = await reader.load_cabinet(77)

    assert len(session.statements) == 6
    assert batch.shop_id == "shop-77"
    assert len(batch.campaigns) == 1
    campaign = batch.campaigns[0]
    assert campaign.adv_setting_id == 101
    assert campaign.search_adv_id == 2002
    assert campaign.sources.adv_setting["_search_adv_id"] == 2002
    assert [row["text"] for row in campaign.sources.keyword_settings] == ["alpha"]
    assert [row["nmid"] for row in campaign.sources.auto_shelf_settings] == [11, 22]
    assert campaign.sources.adv_time_settings is not None
    assert campaign.sources.adv_time_week_masks[0]["dow"] == 1

    joined_sql = "\n".join(session.statements).lower()
    assert "update " not in joined_sql
    assert "insert " not in joined_sql
    assert "delete " not in joined_sql


@pytest.mark.asyncio
async def test_empty_cabinet_stops_after_shop_and_adv_queries() -> None:
    session = _FakeSession(
        [
            _Result(scalar_one="shop-77"),
            _Result(scalars=[]),
        ]
    )
    reader = PostgresCampaignSettingsReader(session)  # type: ignore[arg-type]

    batch = await reader.load_cabinet(77)

    assert batch.campaigns == ()
    assert len(session.statements) == 2
