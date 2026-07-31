"""Интеграция V3: порядок target_place по strategy_mode (MIN_CPA / OPTIMUM / MAX_CONVERSION).

На WB меньший номер позиции = выше в выдаче. Ожидаем:
pos(MAX) <= pos(OPT) <= pos(MIN), и три значения различаются.

Использует test ClickHouse + образцы ``KeywordSetting.text`` из Postgres.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    resolve_keyword_bid_profile,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync import (
    sync_keyword_target_places_v3,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from tests.integration.helpers.v3_target_place_assertions import (
    assert_ladder_positions_distinct_and_ordered,
    assert_profile_resolves_like_orchestrator,
    target_places_for_v3_modes,
)
from tests.integration.helpers.v3_target_place_samples import (
    ensure_v3_keyword_samples,
)
import app.modules.bids_for_positions_manager.clickhouse_manager.clickhouse_manager as bids_ch_module
import app.modules.predict_keywords_target_place.clickhouse_manager.clickhouse_manager as predict_ch_module
from tests.integration.test_predict_keywords_target_place_integration import (
    TEST_NMID,
    _ensure_predict_tables,
    _make_adv_mock,
)
from tests.support.rewrite_default_db_ch_client import patch_get_clickhouse_client
from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST

def _synthetic_ladder_profile(keyword: str, ts: datetime) -> list[BidPosition]:
    """Профиль, где MAX→pos1, OPT→pos2, MIN→pos3 (разные и упорядочены).

    MIN_CPA: min CPO → pos 3; MAX — max conv на pos 1;
    OPTIMUM (production balance): компромисс → pos 2, не pos 1/3.
    """
    positions = [
        (1, 500, 0.40),
        (2, 45, 0.36),
        (3, 40, 0.20),
    ]
    out: list[BidPosition] = []
    for pos, bid, conv in positions:
        bp = BidPosition(keyword, pos, bid, ts)
        bp.conv_carts_to_views = conv
        out.append(bp)
    return out


def _profiles_for_db_keyword(
    keyword_text: str,
    ts: datetime,
    *,
    ch_key: str | None = None,
) -> dict[str, list[BidPosition]]:
    """Словарь профилей с ключом как в CH (может отличаться регистром от БД)."""
    key = ch_key if ch_key is not None else keyword_text
    return {key: _synthetic_ladder_profile(key, ts)}


@pytest.fixture
async def v3_db_keyword_samples(async_session: AsyncSession):
    """До 25 ключей из V3-кампаний; при пустой БД — минимальный сид."""
    return await ensure_v3_keyword_samples(async_session, limit=25)


@pytest.mark.asyncio
async def test_v3_strategy_target_positions_ordered_on_synthetic_profile() -> None:
    """Лестница V3 на фиксированном профиле: MAX <= OPT <= MIN и все разные."""
    ts = datetime.now()
    profile = _synthetic_ladder_profile("ladder_kw", ts)
    places = target_places_for_v3_modes(profile)
    assert_ladder_positions_distinct_and_ordered(
        places[KeywordStrategyMode.MIN_CPA],
        places[KeywordStrategyMode.OPTIMUM],
        places[KeywordStrategyMode.MAX_CONVERSION],
        keyword="ladder_kw",
    )


@pytest.mark.asyncio
async def test_v3_resolve_profile_matches_orchestrator_for_mixed_case_key() -> None:
    """Резолвер: CH-ключ в исходном регистре, текст ключа в БД — lower."""
    ts = datetime.now()
    profiles = _profiles_for_db_keyword("kw_min", ts, ch_key="Kw_Min")
    resolved = assert_profile_resolves_like_orchestrator(profiles, "kw_min")
    places = target_places_for_v3_modes(resolved)
    assert_ladder_positions_distinct_and_ordered(
        places[KeywordStrategyMode.MIN_CPA],
        places[KeywordStrategyMode.OPTIMUM],
        places[KeywordStrategyMode.MAX_CONVERSION],
        keyword="kw_min/Kw_Min",
    )


@pytest.mark.asyncio
async def test_v3_sync_keyword_target_places_applies_modes_from_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sync_keyword_target_places_v3: все ключи, OFF — позиция MIN_CPA из профиля."""
    from unittest.mock import AsyncMock, MagicMock

    from tests.unit.test_keyword_target_place_updater_v3 import _patched_sm

    from tests.unit.auto_updater_v3.test_no_data_activation import _kw as _calc_kw

    ts = datetime.now()
    base_profile = _synthetic_ladder_profile("updater_kw", ts)
    profiles = {
        "updater_kw_off": base_profile,
        "updater_kw_min": base_profile,
        "updater_kw_opt": base_profile,
        "updater_kw_max": base_profile,
    }

    min_kw = MagicMock()
    min_kw.text = "updater_kw_min"
    min_kw.strategy_mode = KeywordStrategyMode.MIN_CPA
    min_kw.target_place = None

    opt_kw = MagicMock()
    opt_kw.text = "updater_kw_opt"
    opt_kw.strategy_mode = KeywordStrategyMode.OPTIMUM
    opt_kw.target_place = None

    max_kw = MagicMock()
    max_kw.text = "updater_kw_max"
    max_kw.strategy_mode = KeywordStrategyMode.MAX_CONVERSION
    max_kw.target_place = None

    off_kw = MagicMock()
    off_kw.text = "updater_kw_off"
    off_kw.strategy_mode = KeywordStrategyMode.OFF
    off_kw.target_place = 99

    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [off_kw, min_kw, opt_kw, max_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    # RK ratio без CH wb_common_stat (sync вызывает load_campaign_orders_per_cart_7d).
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_campaign_orders_per_cart_7d",
        AsyncMock(return_value=RK_ORDERS_PER_CART_TEST),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123
    adv.complex_adv = MagicMock()
    adv.complex_adv.adv_setting = MagicMock()
    adv.complex_adv.adv_setting.nmids = [TEST_NMID]

    expected = target_places_for_v3_modes(
        base_profile,
        rk_orders_per_cart=RK_ORDERS_PER_CART_TEST,
    )

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles=profiles,
        calculated_by_text={
            "updater_kw_off": _calc_kw(
                ks_id=1,
                text="updater_kw_off",
                mode=KeywordStrategyMode.OFF,
                conv=0.01,
                cpm_set_bid=200,
            ),
            "updater_kw_min": _calc_kw(
                ks_id=2,
                text="updater_kw_min",
                mode=KeywordStrategyMode.MIN_CPA,
                conv=0.01,
                cpm_set_bid=200,
            ),
            "updater_kw_opt": _calc_kw(
                ks_id=3,
                text="updater_kw_opt",
                mode=KeywordStrategyMode.OPTIMUM,
                conv=0.01,
                cpm_set_bid=200,
            ),
            "updater_kw_max": _calc_kw(
                ks_id=4,
                text="updater_kw_max",
                mode=KeywordStrategyMode.MAX_CONVERSION,
                conv=0.01,
                cpm_set_bid=200,
            ),
        },
    )

    # OFF: прокси MIN_CPA из профиля (RK CPO), не сохранённое 99
    assert off_kw.target_place == expected[KeywordStrategyMode.MIN_CPA]
    assert min_kw.target_place == expected[KeywordStrategyMode.MIN_CPA]
    assert opt_kw.target_place == expected[KeywordStrategyMode.OPTIMUM]
    assert max_kw.target_place == expected[KeywordStrategyMode.MAX_CONVERSION]
    assert_ladder_positions_distinct_and_ordered(
        min_kw.target_place,
        opt_kw.target_place,
        max_kw.target_place,
        keyword="updater_kw_*",
    )


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_v3_strategy_order_for_db_keyword_texts(v3_db_keyword_samples) -> None:
    """Для текстов ключей из Postgres резолвер + лестница V3 дают упорядоченную лестницу."""
    ts = datetime.now()
    checked = 0
    for sample in v3_db_keyword_samples[:10]:
        profiles = _profiles_for_db_keyword(sample.keyword_text, ts)
        profile = resolve_keyword_bid_profile(profiles, sample.keyword_text)
        if profile is None:
            continue
        places = target_places_for_v3_modes(profile)
        if any(v is None for v in places.values()):
            continue
        pos_min = places[KeywordStrategyMode.MIN_CPA]
        pos_opt = places[KeywordStrategyMode.OPTIMUM]
        pos_max = places[KeywordStrategyMode.MAX_CONVERSION]
        assert_ladder_positions_distinct_and_ordered(
            pos_min,
            pos_opt,
            pos_max,
            keyword=sample.keyword_text,
        )
        # На синтетическом профиле ожидаем ровно 1 / 2 / 3
        assert (pos_max, pos_opt, pos_min) == (1, 2, 3), (
            f"{sample.keyword_text!r}: ожидалось MAX=1, OPT=2, MIN=3"
        )
        checked += 1
    assert checked >= 1, "ни один образец из БД не прошёл резолв профиля"


@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_v3_get_keyword_bid_profiles_ch_integration_ordered(
    clickhouse_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E2E CH: bid_profiles → target_place по режимам, лестница MAX<=OPT<=MIN."""
    patch_get_clickhouse_client(monkeypatch, [bids_ch_module], clickhouse_client)
    patch_get_clickhouse_client(
        monkeypatch,
        [predict_ch_module],
        clickhouse_client,
        attr="get_client",
    )
    await _ensure_predict_tables(clickhouse_client)
    ts = datetime.now()
    norm_query = "kw_ch_ladder"
    async with anti_ch_crash_semaphore:
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.bid_decision_log")
        await clickhouse_client.command(
            "TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.clusters_adv_deltas_5m"
        )
        await clickhouse_client.command(
            "TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.pos_priors_category"
        )

        # bid/conv согласованы с _synthetic_ladder_profile (MAX=1, OPT=2, MIN=3)
        bids_rows = [
            (1, TEST_NMID, norm_query, "Electronics", 1.0, 1, 100, 10.0, 500.0, 1.0, 90, 9.0, 500.0, 1.0, 500.0, "cpm", ts, ts, 1),
            (1, TEST_NMID, norm_query, "Electronics", 2.0, 2, 80, 8.0, 80.0, 2.0, 70, 7.0, 80.0, 2.0, 80.0, "cpm", ts, ts, 2),
            (1, TEST_NMID, norm_query, "Electronics", 3.0, 3, 60, 6.0, 60.0, 3.0, 50, 5.0, 60.0, 3.0, 60.0, "cpm", ts, ts, 3),
        ]
        await clickhouse_client.insert(
            "test_adv_bot_clickhouse.bid_decision_log",
            [list(r) for r in bids_rows],
            column_names=[
                "adv_id", "nmid", "norm_query", "wb_category", "pos_final",
                "pos_final_bucket", "views_curr", "spend_curr", "cpm_curr", "pos_curr",
                "views_prev", "spend_prev", "cpm_prev", "pos_prev", "final_bid",
                "decision_source", "stats_max_timestamp", "decision_time", "version",
            ],
        )
        deltas = []
        for pos_bin, cpm in ((1, 500.0), (2, 80.0), (3, 60.0)):
            deltas.append(
                [
                    1, TEST_NMID, "Electronics", norm_query, ts,
                    50, 5, 0, 0, pos_bin, cpm, 5.0, 0, 0, ts, 1,
                ]
            )
        await clickhouse_client.insert(
            "test_adv_bot_clickhouse.clusters_adv_deltas_5m",
            deltas,
            column_names=[
                "adv_id", "nmid", "wb_category", "norm_query", "ts5",
                "dviews", "dcarts", "dclicks", "dorders", "pos_bin", "cpm_mid",
                "dspend_est", "gap_minutes", "is_reset", "src_ts", "version",
            ],
        )
        conv_priors = [
            ["Electronics", 1, 0.40, 50, ts],
            ["Electronics", 2, 0.25, 40, ts],
            ["Electronics", 3, 0.22, 30, ts],
        ]
        await clickhouse_client.insert(
            "test_adv_bot_clickhouse.pos_priors_category",
            conv_priors,
            column_names=["wb_category", "pos_bin", "p_14d", "views_14d", "calculated_at"],
        )

    predictor = build_predict_keywords_target_place()
    adv = _make_adv_mock(nmid=TEST_NMID, min_bid=40)
    profiles = await predictor.get_keyword_bid_profiles(adv, positions_size=10)
    assert norm_query in profiles or norm_query.lower() in {k.lower() for k in profiles}
    profile = resolve_keyword_bid_profile(profiles, norm_query)
    assert profile is not None
    places = target_places_for_v3_modes(profile)
    assert_ladder_positions_distinct_and_ordered(
        places[KeywordStrategyMode.MIN_CPA],
        places[KeywordStrategyMode.OPTIMUM],
        places[KeywordStrategyMode.MAX_CONVERSION],
        keyword=norm_query,
    )
