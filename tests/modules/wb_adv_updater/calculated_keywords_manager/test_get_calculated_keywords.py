"""Тесты для метода CalculatedKeywordsManager.__get_calculated_keywords.

Метод имеет два основных алгоритма:
1. Без белого списка: все ключевые слова -> BAD (LESS_THEN_RATING_BY_ORDERS), best_keyword_status=False
2. С белым списком: фильтрация по rating_by_orders и hard_status (при white_list_mode=ABOVE_MIN_RATING)

Это unit-тесты, не требующие базы данных. Порог МС использует complex_adv.target_pay_for_order
(как после батча PlanFact в WBShopDataManager) либо resolve_target_cost по полям adv_setting.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock

import pytest

import app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager as ckm_module
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import PlanFactSummary
from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_cooldown_entry import (
    AboveTargetCooldownEntry,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_min_bid_cooldown import (
    COOLDOWN_RETEST_DISPLAY_TAG,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager import (
    CalculatedKeywordsManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.pre_calculated_keyword import (
    PreCalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.above_target_min_bid_diagnostic import (
    AboveTargetMinBidDiagnosticState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.client_bot.user_interface.views.above_target_min_bid_ui import format_ms_rule_line
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus

from tests.factories.keyword_pipeline import (
    PreCalculatedKeywordFactory,
    HardStatus,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _stub_plan_fact_reader_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Отключить Redis/CH I/O PlanFactReader в unit-сьюте этого модуля.

    ``__get_calculated_keywords`` всегда вызывает ``PlanFactReader().get_latest_plan_fact``;
    без стаба каждый тест ждёт timeout Redis/CH (~4s) и только потом падает в except.
    Тесты с явным ``monkeypatch.setattr(... get_latest_plan_fact ...)`` переопределяют стаб.
    """
    monkeypatch.setattr(
        ckm_module.PlanFactReader,
        "get_latest_plan_fact",
        AsyncMock(return_value=None),
    )


@pytest.fixture
def complex_adv_mock():
    """Мок для ComplexAdv (для тестов с белым списком)."""
    mock = MagicMock()
    mock.hard_min_ctr = None
    mock.rec_system_promotion_mode_active = False
    mock.auto_add_only_relevant_phrase = False
    mock.target_pay_for_order = None
    adv_setting = MagicMock()
    adv_setting.plan_for_sales_for_day = 10
    adv_setting.target_price_for_order = 50.0
    # Низкий max при «план не выполнен», чтобы дефолтный CPO ключа (≈2) был выше target.
    adv_setting.max_price_for_order = 1.0
    mock.adv_setting = adv_setting
    return mock


@pytest.fixture
def complex_adv_mock_whitelist(complex_adv_mock):
    """Мок для ComplexAdv с white_list_mode=ABOVE_MIN_RATING (тесты с белым списком)."""
    complex_adv_mock.white_list_mode = WhiteListMode.ABOVE_MIN_RATING
    return complex_adv_mock


@pytest.fixture
def complex_adv_with_hard_min_ctr():
    """Мок для ComplexAdv с заданным hard_min_ctr (для тестов без белого списка)."""
    mock = MagicMock()
    mock.hard_min_ctr = 0.05  # 5%
    mock.rec_system_promotion_mode_active = False
    return mock


# ============================================================================
# Тесты без белого списка (все -> BAD, best_keyword_status=False)
# ============================================================================


@pytest.mark.asyncio
async def test_no_whitelist_all_keywords_pass_ctr(complex_adv_with_hard_min_ctr):
    """Без белого списка: все ключевые слова -> BAD (LESS_THEN_RATING_BY_ORDERS)."""
    adv_id = 12345
    pre_keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=100,
            cluster_stat__final_rating=50.0 + i,
            cluster_stat__norm_query=f"keyword_{i}",
            bidder_keyword_status=BidderKeywordStatus.GOOD,
        )
        for i in range(3)
    ]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, pre_keywords
    )

    assert len(result) == 3
    result_by_text = {kw.text: kw for kw in result}
    for i in (0, 1, 2):
        assert result_by_text[f"keyword_{i}"].status == KeywordStatus.BAD
        assert result_by_text[f"keyword_{i}"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
        assert result_by_text[f"keyword_{i}"].best_keyword_status is False


@pytest.mark.asyncio
async def test_no_whitelist_always_on_gets_good(complex_adv_with_hard_min_ctr):
    """Без белого списка: ключ с hard_status=4 (фикс.фразы) -> GOOD, ALWAYS_ON."""
    adv_id = 12345
    pre_keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.ALWAYS_ON,
            keyword_setting__text="fixed_phrase",
            cluster_stat__views=500,
            cluster_stat__clicks=10,
            cluster_stat__final_rating=30.0,
            cluster_stat__norm_query="fixed_phrase",
            bidder_keyword_status=BidderKeywordStatus.GOOD,
        ),
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text="in_test_phrase",
            cluster_stat__views=500,
            cluster_stat__clicks=10,
            cluster_stat__final_rating=20.0,
            cluster_stat__norm_query="in_test_phrase",
            bidder_keyword_status=BidderKeywordStatus.GOOD,
        ),
    ]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, pre_keywords
    )

    assert len(result) == 2
    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["fixed_phrase"].status == KeywordStatus.GOOD
    assert result_by_text["fixed_phrase"].reason == KeywordStatusReason.ALWAYS_ON
    assert result_by_text["in_test_phrase"].status == KeywordStatus.BAD
    assert result_by_text["in_test_phrase"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS


@pytest.mark.asyncio
async def test_no_whitelist_some_keywords_fail_ctr(complex_adv_with_hard_min_ctr):
    """Без белого списка: оба ключевых слова -> BAD."""
    adv_id = 12345
    good_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="good_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=60.0,
        cluster_stat__norm_query="good_keyword",
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )
    bad_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="bad_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=20,
        cluster_stat__final_rating=40.0,
        cluster_stat__norm_query="bad_keyword",
    )
    pre_keywords = [good_kw, bad_kw]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, pre_keywords
    )

    assert len(result) == 2
    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["good_keyword"].status == KeywordStatus.BAD
    assert result_by_text["good_keyword"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert result_by_text["good_keyword"].best_keyword_status is False
    assert result_by_text["bad_keyword"].status == KeywordStatus.BAD
    assert result_by_text["bad_keyword"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert result_by_text["bad_keyword"].best_keyword_status is False


@pytest.mark.asyncio
async def test_no_whitelist_two_keywords_best_by_rating(complex_adv_mock):
    """Без белого списка: оба слова -> BAD."""
    adv_id = 12345
    good_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="good_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=50,
        cluster_stat__final_rating=60.0,
        cluster_stat__norm_query="good_keyword",
    )
    bad_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="bad_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=10,
        cluster_stat__final_rating=40.0,
        cluster_stat__norm_query="bad_keyword",
    )
    pre_keywords = [good_kw, bad_kw]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock, pre_keywords
    )

    assert len(result) == 2
    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["good_keyword"].status == KeywordStatus.BAD
    assert result_by_text["good_keyword"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert result_by_text["bad_keyword"].status == KeywordStatus.BAD
    assert result_by_text["bad_keyword"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS


@pytest.mark.asyncio
async def test_no_whitelist_best_keyword_by_rating(complex_adv_with_hard_min_ctr):
    """Без белого списка: оба ключевых слова -> BAD, best_keyword_status=False."""
    adv_id = 12345
    best_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="best_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=150,
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="best_keyword",
    )
    normal_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="normal_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=60.0,
        cluster_stat__norm_query="normal_keyword",
    )
    pre_keywords = [best_kw, normal_kw]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["normal_keyword"].best_keyword_status is False
    assert result_by_text["normal_keyword"].status == KeywordStatus.BAD
    assert result_by_text["best_keyword"].best_keyword_status is False
    assert result_by_text["best_keyword"].status == KeywordStatus.BAD


# ============================================================================
# Тесты без белого списка с разным количеством слов
# ============================================================================


@pytest.mark.asyncio
async def test_no_whitelist_single_keyword(complex_adv_with_hard_min_ctr):
    """Без БС, 1 ключевое слово -> BAD (LESS_THEN_RATING_BY_ORDERS)."""
    adv_id = 12345
    single_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="single_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="single_keyword",
    )

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, [single_kw]
    )

    assert len(result) == 1
    assert result[0].status == KeywordStatus.BAD
    assert result[0].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert result[0].best_keyword_status is False


@pytest.mark.asyncio
async def test_no_whitelist_ten_keywords_mixed_ctr(complex_adv_with_hard_min_ctr):
    """Без БС, 10 слов: все -> BAD."""
    adv_id = 12345
    keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=10 + i * 10,
            cluster_stat__final_rating=50.0 + i,
            cluster_stat__norm_query=f"keyword_{i}",
        )
        for i in range(10)
    ]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, keywords
    )

    assert len(result) == 10
    result_by_text = {kw.text: kw for kw in result}
    for i in range(10):
        assert result_by_text[f"keyword_{i}"].status == KeywordStatus.BAD
        assert result_by_text[f"keyword_{i}"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
        assert result_by_text[f"keyword_{i}"].best_keyword_status is False


@pytest.mark.asyncio
async def test_no_whitelist_twenty_keywords_all_good(complex_adv_with_hard_min_ctr):
    """Без БС, 20 слов: все -> BAD."""
    adv_id = 12345
    keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=60 + i * 10,
            cluster_stat__final_rating=50.0,
            cluster_stat__norm_query=f"keyword_{i}",
        )
        for i in range(20)
    ]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, keywords
    )

    assert len(result) == 20
    good_count = sum(1 for kw in result if kw.status == KeywordStatus.GOOD)
    bad_count = sum(1 for kw in result if kw.status == KeywordStatus.BAD)
    assert good_count == 0
    assert bad_count == 20
    for kw in result:
        assert kw.best_keyword_status is False
        assert kw.reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS


@pytest.mark.asyncio
async def test_no_whitelist_twenty_keywords_all_bad(complex_adv_with_hard_min_ctr):
    """Без БС, 20 слов: все -> BAD."""
    adv_id = 12345
    keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=1 + i,
            cluster_stat__final_rating=50.0,
            cluster_stat__norm_query=f"keyword_{i}",
        )
        for i in range(20)
    ]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, keywords
    )

    assert len(result) == 20
    good_count = sum(1 for kw in result if kw.status == KeywordStatus.GOOD)
    bad_count = sum(1 for kw in result if kw.status == KeywordStatus.BAD)
    assert good_count == 0
    assert bad_count == 20
    for kw in result:
        assert kw.reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
        assert kw.best_keyword_status is False


@pytest.mark.asyncio
async def test_no_whitelist_fifty_keywords(complex_adv_with_hard_min_ctr):
    """Без БС, 50 слов: все -> BAD."""
    adv_id = 12345
    keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=10 + i * 3,
            cluster_stat__final_rating=50.0,
            cluster_stat__norm_query=f"keyword_{i}",
        )
        for i in range(50)
    ]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, keywords
    )

    assert len(result) == 50
    good_count = sum(1 for kw in result if kw.status == KeywordStatus.GOOD)
    bad_count = sum(1 for kw in result if kw.status == KeywordStatus.BAD)
    assert good_count == 0
    assert bad_count == 50
    for kw in result:
        assert kw.best_keyword_status is False
        assert kw.reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS


@pytest.mark.asyncio
async def test_no_whitelist_with_blacklist_keywords(complex_adv_with_hard_min_ctr):
    """Без БС: оба слова -> BAD (нет ни одного в белом списке)."""
    adv_id = 12345
    blacklist_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.BLACKLIST,
        keyword_setting__text="blacklist_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="blacklist_keyword",
    )
    in_test_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=80,
        cluster_stat__final_rating=60.0,
        cluster_stat__norm_query="in_test_keyword",
    )

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, [blacklist_kw, in_test_kw]
    )

    assert len(result) == 2
    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["in_test_keyword"].status == KeywordStatus.BAD
    assert result_by_text["in_test_keyword"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_keyword"].best_keyword_status is False
    assert result_by_text["blacklist_keyword"].status == KeywordStatus.BAD
    assert result_by_text["blacklist_keyword"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert result_by_text["blacklist_keyword"].best_keyword_status is False


# ============================================================================
# Тесты с белым списком (фильтрация по rating_by_orders и hard_status)
# ============================================================================


@pytest.mark.asyncio
async def test_whitelist_hard_status_whitelist(complex_adv_mock_whitelist):
    """Тест: с белым списком, hard_status=2 (WHITELIST) -> GOOD.

    Условия:
    - Есть хотя бы одно ключевое слово с hard_status=2
    - Проверяем, что ключевые слова с hard_status=2 получают статус GOOD
    """
    adv_id = 12345

    whitelist_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="whitelist_keyword",
    )

    in_test_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=60.0,  # Выше, чем у whitelist
        cluster_stat__norm_query="in_test_keyword",
    )

    pre_keywords = [whitelist_kw, in_test_kw]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["whitelist_keyword"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_keyword"].reason == KeywordStatusReason.WHITE_LIST


@pytest.mark.asyncio
async def test_whitelist_hard_status_blacklist(complex_adv_mock_whitelist):
    """Тест: с белым списком, hard_status=0 (BLACKLIST) -> BAD.

    Условия:
    - Есть хотя бы одно ключевое слово с hard_status=2 (активирует алгоритм с whitelist)
    - Проверяем, что ключевые слова с hard_status=0 получают статус BAD
    """
    adv_id = 12345

    whitelist_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="whitelist_keyword",
    )

    blacklist_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.BLACKLIST,
        keyword_setting__text="blacklist_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=100.0,  # Даже высокий рейтинг не поможет
        cluster_stat__norm_query="blacklist_keyword",
    )

    pre_keywords = [whitelist_kw, blacklist_kw]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["blacklist_keyword"].status == KeywordStatus.BAD
    assert result_by_text["blacklist_keyword"].reason == KeywordStatusReason.BLACK_LIST


@pytest.mark.asyncio
async def test_whitelist_hard_status_turn_off(complex_adv_mock_whitelist):
    """Тест: с белым списком, hard_status=3 (TURN_OFF) -> BAD.

    Условия:
    - Есть хотя бы одно ключевое слово с hard_status=2 (активирует алгоритм с whitelist)
    - Проверяем, что ключевые слова с hard_status=3 получают статус BAD
    """
    adv_id = 12345

    whitelist_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="whitelist_keyword",
    )

    turn_off_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.TURN_OFF,
        keyword_setting__text="turn_off_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=100.0,  # Даже высокий рейтинг не поможет
        cluster_stat__norm_query="turn_off_keyword",
    )

    pre_keywords = [whitelist_kw, turn_off_kw]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["turn_off_keyword"].status == KeywordStatus.BAD
    assert result_by_text["turn_off_keyword"].reason == KeywordStatusReason.TURN_OFF


@pytest.mark.asyncio
async def test_whitelist_rating_by_orders_filtering(complex_adv_mock_whitelist):
    """Тест: с белым списком, фильтрация по rating_by_orders.

    Условия:
    - Есть ключевые слова с hard_status=2 (whitelist)
    - Ключевые слова с hard_status=1 (IN_TEST) сравниваются с худшим из whitelist

    Ожидание:
    - IN_TEST с rating >= worst_whitelist_rating получают статус GOOD
    - IN_TEST с rating < worst_whitelist_rating получают статус BAD
    """
    adv_id = 12345

    # Whitelist с низким рейтингом (будет "худшим" в whitelist)
    whitelist_low = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_low",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=30.0,  # Низкий рейтинг
        cluster_stat__norm_query="whitelist_low",
    )

    # Whitelist с высоким рейтингом
    whitelist_high = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_high",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=80.0,  # Высокий рейтинг
        cluster_stat__norm_query="whitelist_high",
    )

    # IN_TEST с рейтингом выше худшего whitelist -> GOOD
    in_test_good = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_good",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,  # 50 >= 30 -> GOOD
        cluster_stat__norm_query="in_test_good",
    )

    # IN_TEST с рейтингом ниже худшего whitelist -> BAD
    in_test_bad = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_bad",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=20.0,  # 20 < 30 -> BAD
        cluster_stat__norm_query="in_test_bad",
    )

    pre_keywords = [whitelist_low, whitelist_high, in_test_good, in_test_bad]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["whitelist_low"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_high"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_good"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_good"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_bad"].status == KeywordStatus.BAD
    assert result_by_text["in_test_bad"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS


@pytest.mark.asyncio
async def test_whitelist_best_keyword_by_rating(complex_adv_mock_whitelist):
    """Тест: с белым списком, best_keyword определяется по максимальному rating_by_orders.

    Ожидание:
    - Ключевое слово с максимальным rating_by_orders получает best_keyword_status=True
    - Остальные получают best_keyword_status=False
    """
    adv_id = 12345

    # Whitelist с низким рейтингом
    whitelist_low = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_low",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=30.0,
        cluster_stat__norm_query="whitelist_low",
    )

    # IN_TEST с максимальным рейтингом (должен быть best)
    best_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="best_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=100.0,  # Максимальный рейтинг
        cluster_stat__norm_query="best_keyword",
    )

    # Обычное ключевое слово
    normal_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="normal_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="normal_keyword",
    )

    pre_keywords = [whitelist_low, best_kw, normal_kw]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["best_keyword"].best_keyword_status is True
    assert result_by_text["whitelist_low"].best_keyword_status is False
    assert result_by_text["normal_keyword"].best_keyword_status is False


# ============================================================================
# Тесты с разным количеством слов в белом списке
# ============================================================================


@pytest.mark.asyncio
async def test_whitelist_single_keyword(complex_adv_mock_whitelist):
    """Тест: белый список с 1 ключевым словом.

    Условия:
    - 1 слово в whitelist
    - Несколько слов в тестировании

    Ожидание:
    - Порог rating_by_orders = рейтинг единственного whitelist слова
    - IN_TEST с rating >= порога -> GOOD
    - IN_TEST с rating < порога -> BAD
    """
    adv_id = 12345

    # Единственное слово в whitelist (устанавливает порог)
    whitelist_single = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_single",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,  # Порог = 50.0
        cluster_stat__norm_query="whitelist_single",
    )

    # IN_TEST выше порога
    in_test_above = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_above",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=60.0,  # 60 >= 50 -> GOOD
        cluster_stat__norm_query="in_test_above",
    )

    # IN_TEST на уровне порога (равно)
    in_test_equal = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_equal",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,  # 50 >= 50 -> GOOD
        cluster_stat__norm_query="in_test_equal",
    )

    # IN_TEST ниже порога
    in_test_below = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_below",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=40.0,  # 40 < 50 -> BAD
        cluster_stat__norm_query="in_test_below",
    )

    pre_keywords = [whitelist_single, in_test_above, in_test_equal, in_test_below]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["whitelist_single"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_single"].reason == KeywordStatusReason.WHITE_LIST
    assert result_by_text["in_test_above"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_above"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_equal"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_equal"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_below"].status == KeywordStatus.BAD
    assert result_by_text["in_test_below"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS


@pytest.mark.asyncio
async def test_whitelist_three_keywords_different_ratings(complex_adv_mock_whitelist):
    """Тест: белый список с 3 ключевыми словами с разными рейтингами.

    Условия:
    - 3 слова в whitelist с рейтингами 20, 50, 80
    - Порог = min(20, 50, 80) = 20

    Ожидание:
    - Все whitelist слова -> GOOD
    - IN_TEST с rating >= 20 -> GOOD
    - IN_TEST с rating < 20 -> BAD
    """
    adv_id = 12345

    # Whitelist слова с разными рейтингами
    whitelist_low = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_low",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=20.0,  # Худший в whitelist -> порог
        cluster_stat__norm_query="whitelist_low",
    )

    whitelist_mid = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_mid",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="whitelist_mid",
    )

    whitelist_high = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_high",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=80.0,
        cluster_stat__norm_query="whitelist_high",
    )

    # IN_TEST между низким и средним whitelist
    in_test_between = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_between",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=35.0,  # 35 >= 20 -> GOOD
        cluster_stat__norm_query="in_test_between",
    )

    # IN_TEST ниже всех whitelist
    in_test_lowest = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_lowest",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=10.0,  # 10 < 20 -> BAD
        cluster_stat__norm_query="in_test_lowest",
    )

    pre_keywords = [whitelist_low, whitelist_mid, whitelist_high, in_test_between, in_test_lowest]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["whitelist_low"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_mid"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_high"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_between"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_between"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_lowest"].status == KeywordStatus.BAD
    assert result_by_text["in_test_lowest"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS


@pytest.mark.asyncio
async def test_whitelist_five_keywords_all_same_rating(complex_adv_mock_whitelist):
    """Тест: белый список с 5 ключевыми словами с одинаковым рейтингом.

    Условия:
    - 5 слов в whitelist с одинаковым рейтингом 40
    - Порог = 40
    """
    adv_id = 12345

    # 5 whitelist слов с одинаковым рейтингом
    whitelist_keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.WHITELIST,
            keyword_setting__text=f"whitelist_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=100,
            cluster_stat__final_rating=40.0,  # Все с рейтингом 40
            cluster_stat__norm_query=f"whitelist_{i}",
        )
        for i in range(5)
    ]

    # IN_TEST ровно на пороге
    in_test_equal = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_equal",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=40.0,  # 40 >= 40 -> GOOD
        cluster_stat__norm_query="in_test_equal",
    )

    # IN_TEST чуть ниже порога
    in_test_below = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_below",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=39.9,  # 39.9 < 40 -> BAD
        cluster_stat__norm_query="in_test_below",
    )

    pre_keywords = whitelist_keywords + [in_test_equal, in_test_below]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    for i in range(5):
        assert result_by_text[f"whitelist_{i}"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_equal"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_below"].status == KeywordStatus.BAD


@pytest.mark.asyncio
async def test_whitelist_ten_keywords_large_spread(complex_adv_mock_whitelist):
    """Тест: белый список с 10 ключевыми словами с большим разбросом рейтингов.

    Условия:
    - 10 слов в whitelist с рейтингами от 10 до 100
    - Порог = min = 10
    """
    adv_id = 12345

    # 10 whitelist слов с рейтингами 10, 20, 30, ..., 100
    whitelist_keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.WHITELIST,
            keyword_setting__text=f"whitelist_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=100,
            cluster_stat__final_rating=10.0 + i * 10,  # 10, 20, 30, ..., 100
            cluster_stat__norm_query=f"whitelist_{i}",
        )
        for i in range(10)
    ]

    # IN_TEST с рейтингом между минимальным и максимальным whitelist
    in_test_mid = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_mid",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=55.0,  # 55 >= 10 -> GOOD
        cluster_stat__norm_query="in_test_mid",
    )

    # IN_TEST с рейтингом ниже минимального whitelist
    in_test_lowest = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_lowest",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=5.0,  # 5 < 10 -> BAD
        cluster_stat__norm_query="in_test_lowest",
    )

    # IN_TEST с рейтингом выше максимального whitelist
    in_test_highest = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_highest",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__final_rating=150.0,  # 150 >= 10 -> GOOD (и будет best)
        cluster_stat__norm_query="in_test_highest",
    )

    pre_keywords = whitelist_keywords + [in_test_mid, in_test_lowest, in_test_highest]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    result_by_text = {kw.text: kw for kw in result}
    for i in range(10):
        assert result_by_text[f"whitelist_{i}"].status == KeywordStatus.GOOD
        assert result_by_text[f"whitelist_{i}"].reason == KeywordStatusReason.WHITE_LIST
    assert result_by_text["in_test_mid"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_mid"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_lowest"].status == KeywordStatus.BAD
    assert result_by_text["in_test_lowest"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_highest"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_highest"].best_keyword_status is True


@pytest.mark.asyncio
async def test_whitelist_mixed_with_all_hard_statuses(complex_adv_mock_whitelist):
    """Тест: комплексный сценарий со всеми типами hard_status.

    Условия:
    - 3 слова в whitelist (hard_status=2)
    - 2 слова в blacklist (hard_status=0)
    - 1 слово turn_off (hard_status=3)
    - 4 слова в тестировании (hard_status=1)

    Ожидание:
    - Whitelist -> GOOD
    - Blacklist -> BAD (независимо от рейтинга)
    - Turn_off -> BAD (независимо от рейтинга)
    - IN_TEST -> зависит от сравнения с худшим whitelist
    """
    adv_id = 12345

    # Whitelist слова
    whitelist_1 = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_1",
        cluster_stat__final_rating=30.0,  # Худший в whitelist -> порог
        cluster_stat__norm_query="whitelist_1",
    )
    whitelist_2 = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_2",
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="whitelist_2",
    )
    whitelist_3 = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_3",
        cluster_stat__final_rating=70.0,
        cluster_stat__norm_query="whitelist_3",
    )

    # Blacklist слова (даже с высоким рейтингом -> BAD)
    blacklist_1 = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.BLACKLIST,
        keyword_setting__text="blacklist_1",
        cluster_stat__final_rating=100.0,  # Высокий рейтинг не поможет
        cluster_stat__norm_query="blacklist_1",
    )
    blacklist_2 = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.BLACKLIST,
        keyword_setting__text="blacklist_2",
        cluster_stat__final_rating=5.0,
        cluster_stat__norm_query="blacklist_2",
    )

    # Turn_off слово
    turn_off = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.TURN_OFF,
        keyword_setting__text="turn_off",
        cluster_stat__final_rating=80.0,  # Высокий рейтинг не поможет
        cluster_stat__norm_query="turn_off",
    )

    # IN_TEST слова
    in_test_good_1 = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_good_1",
        cluster_stat__final_rating=45.0,  # >= 30 -> GOOD
        cluster_stat__norm_query="in_test_good_1",
    )
    in_test_good_2 = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_good_2",
        cluster_stat__final_rating=30.0,  # == 30 -> GOOD
        cluster_stat__norm_query="in_test_good_2",
    )
    in_test_bad_1 = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_bad_1",
        cluster_stat__final_rating=25.0,  # < 30 -> BAD
        cluster_stat__norm_query="in_test_bad_1",
    )
    in_test_bad_2 = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_bad_2",
        cluster_stat__final_rating=10.0,  # < 30 -> BAD
        cluster_stat__norm_query="in_test_bad_2",
    )

    pre_keywords = [
        whitelist_1, whitelist_2, whitelist_3,
        blacklist_1, blacklist_2,
        turn_off,
        in_test_good_1, in_test_good_2, in_test_bad_1, in_test_bad_2,
    ]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    assert len(result) == 10
    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["whitelist_1"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_1"].reason == KeywordStatusReason.WHITE_LIST
    assert result_by_text["whitelist_2"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_3"].status == KeywordStatus.GOOD
    assert result_by_text["blacklist_1"].status == KeywordStatus.BAD
    assert result_by_text["blacklist_1"].reason == KeywordStatusReason.BLACK_LIST
    assert result_by_text["blacklist_2"].status == KeywordStatus.BAD
    assert result_by_text["blacklist_2"].reason == KeywordStatusReason.BLACK_LIST
    assert result_by_text["turn_off"].status == KeywordStatus.BAD
    assert result_by_text["turn_off"].reason == KeywordStatusReason.TURN_OFF
    assert result_by_text["in_test_good_1"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_good_1"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_good_2"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_bad_1"].status == KeywordStatus.BAD
    assert result_by_text["in_test_bad_1"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_bad_2"].status == KeywordStatus.BAD


@pytest.mark.asyncio
async def test_whitelist_only_whitelist_keywords(complex_adv_mock_whitelist):
    """Тест: только слова в белом списке, без IN_TEST.

    Условия:
    - 5 слов в whitelist
    - Нет слов в тестировании

    Ожидание:
    - Все whitelist -> GOOD
    - Best определяется по максимальному rating_by_orders
    """
    adv_id = 12345

    whitelist_keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.WHITELIST,
            keyword_setting__text=f"whitelist_{i}",
            cluster_stat__final_rating=20.0 + i * 15,  # 20, 35, 50, 65, 80
            cluster_stat__norm_query=f"whitelist_{i}",
        )
        for i in range(5)
    ]

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, whitelist_keywords
    )

    assert len(result) == 5
    result_by_text = {kw.text: kw for kw in result}
    for i in range(5):
        assert result_by_text[f"whitelist_{i}"].status == KeywordStatus.GOOD
        assert result_by_text[f"whitelist_{i}"].reason == KeywordStatusReason.WHITE_LIST
    assert result_by_text["whitelist_4"].best_keyword_status is True
    for i in range(4):
        assert result_by_text[f"whitelist_{i}"].best_keyword_status is False


@pytest.mark.asyncio
async def test_whitelist_many_in_test_few_whitelist(complex_adv_mock_whitelist):
    """Тест: много слов в тестировании, мало в белом списке.

    Условия:
    - 2 слова в whitelist
    - 20 слов в тестировании с разными рейтингами

    Ожидание:
    - Whitelist -> GOOD
    - IN_TEST фильтруются по порогу (худший whitelist)
    """
    adv_id = 12345

    # 2 whitelist слова
    whitelist_low = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_low",
        cluster_stat__final_rating=25.0,  # Порог
        cluster_stat__norm_query="whitelist_low",
    )
    whitelist_high = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="whitelist_high",
        cluster_stat__final_rating=75.0,
        cluster_stat__norm_query="whitelist_high",
    )

    # 20 IN_TEST слов с рейтингами от 5 до 100
    in_test_keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"in_test_{i}",
            cluster_stat__final_rating=5.0 + i * 5,  # 5, 10, 15, ..., 100
            cluster_stat__norm_query=f"in_test_{i}",
        )
        for i in range(20)
    ]

    pre_keywords = [whitelist_low, whitelist_high] + in_test_keywords

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist, pre_keywords
    )

    assert len(result) == 22
    result_by_text = {kw.text: kw for kw in result}
    assert result_by_text["whitelist_low"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_high"].status == KeywordStatus.GOOD
    for i in range(4):
        assert result_by_text[f"in_test_{i}"].status == KeywordStatus.BAD
    for i in range(4, 20):
        assert result_by_text[f"in_test_{i}"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_19"].best_keyword_status is True


# ============================================================================
# Правило «выше цели при мин. ставке» (24ч заморозка + 1ч + окно перетеста 25–26ч)
# ============================================================================


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


def _pre_kw_above_target_at_min(
    *,
    adv_id: int = 12345,
    text: str = "above_kw",
    hard_status: HardStatus = HardStatus.IN_TEST,
    target_place: int | None = 20,
    position: float = 5.0,
    cpm: float = 100.0,
    views: int = 1000,
) -> PreCalculatedKeyword:
    return PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=hard_status,
        keyword_setting__text=text,
        keyword_setting__target_place=target_place,
        cluster_stat__norm_query=text,
        cluster_stat__position=position,
        cluster_stat__cpm=cpm,
        cluster_stat__views=views,
        cluster_stat__clicks=100,
        cluster_stat__conv_views_to_orders=0.05,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )


# ============================================================================
# resolved_target_cost (complex_adv.target_pay_for_order) для порога МС
# ============================================================================


@pytest.mark.asyncio
async def test_resolved_target_pay_on_complex_adv_tightens_min_bid_cooldown_gate(
    complex_adv_mock_whitelist,
    fixed_now,
) -> None:
    """Как PreComplexAdv.resolved_target_pay_for_order: цель 50 ₽ режет МС; max 200 — нет."""
    adv_id = 999
    complex_adv_mock_whitelist.adv_id = adv_id
    complex_adv_mock_whitelist.adv_setting = SimpleNamespace(
        plan_for_sales_for_day=10,
        target_price_for_order=50,
        max_price_for_order=200,
    )
    # CPM ≤ min_bid (100) нужен для условия МС; conv подобран так, чтобы CPO ≈ 75 ₽.
    _conv_for_pay_75 = 100_000 / 75_000_000
    pre_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="ch_gate",
        keyword_setting__target_place=20,
        cluster_stat__norm_query="ch_gate",
        cluster_stat__position=5.0,
        cluster_stat__cpm=100.0,
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__conv_views_to_orders=_conv_for_pay_75,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )
    summary = PlanFactSummary(
        adv_id=adv_id,
        plan_orders=10,
        fact_predict_orders=15.0,
        fact_pay_for_order=None,
    )
    updates_ch: dict[str, AboveTargetCooldownEntry | None] = {}
    complex_adv_mock_whitelist.target_pay_for_order = 50.0
    result_ch = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates_ch,
        now=fixed_now,
    )
    assert result_ch[0].status == KeywordStatus.BAD
    assert result_ch[0].reason == KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID

    updates_stub: dict[str, AboveTargetCooldownEntry | None] = {}
    complex_adv_mock_whitelist.target_pay_for_order = 200.0
    result_stub = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates_stub,
        now=fixed_now,
    )
    assert result_stub[0].status == KeywordStatus.GOOD
    assert result_stub[0].reason == KeywordStatusReason.WHITE_LIST


@pytest.mark.asyncio
async def test_plan_fact_reader_failure_is_logged(
    complex_adv_mock_whitelist,
    fixed_now,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import logging

    complex_adv_mock_whitelist.adv_id = 4242
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    monkeypatch.setattr(
        ckm_module.PlanFactReader,
        "get_latest_plan_fact",
        AsyncMock(side_effect=RuntimeError("clickhouse unavailable")),
    )
    with caplog.at_level(
        logging.ERROR,
        logger="app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager",
    ):
        _ = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
            complex_adv_mock_whitelist,
            [
                _pre_kw_above_target_at_min(
                    text="log_kw", hard_status=HardStatus.WHITELIST
                )
            ],
            min_bid_for_adv=100,
            cooldown_map={},
            cooldown_updates=updates,
            now=fixed_now,
        )
    assert "PlanFactReader.get_latest_plan_fact failed" in caplog.text
    assert "4242" in caplog.text


@pytest.mark.asyncio
async def test_ch_null_fact_does_not_override_complex_adv_fallback_target(
    complex_adv_mock_whitelist,
    fixed_now,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Incomplete CH row must not overwrite safe fallback target from complex_adv."""
    adv_id = 111
    complex_adv_mock_whitelist.adv_id = adv_id
    complex_adv_mock_whitelist.adv_setting = SimpleNamespace(
        plan_for_sales_for_day=10,
        target_price_for_order=30.0,
        max_price_for_order=95.0,
    )
    complex_adv_mock_whitelist.target_pay_for_order = 30.0
    pre_kw = _pre_kw_above_target_at_min(
        text="null_fact_preserve_fallback",
        hard_status=HardStatus.WHITELIST,
    )
    monkeypatch.setattr(
        ckm_module.PlanFactReader,
        "get_latest_plan_fact",
        AsyncMock(
            return_value=PlanFactSummary(
                adv_id=adv_id,
                plan_orders=10,
                fact_predict_orders=None,
                fact_pay_for_order=None,
            )
        ),
    )

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates={},
        now=fixed_now,
    )

    assert result[0].above_target_min_bid is not None
    assert result[0].above_target_min_bid.resolved_target_cost == 30.0


@pytest.mark.asyncio
async def test_complete_ch_row_still_overrides_fallback_by_existing_resolve_formula(
    complex_adv_mock_whitelist,
    fixed_now,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv_id = 112
    complex_adv_mock_whitelist.adv_id = adv_id
    complex_adv_mock_whitelist.adv_setting = SimpleNamespace(
        plan_for_sales_for_day=10,
        target_price_for_order=30.0,
        max_price_for_order=95.0,
    )
    complex_adv_mock_whitelist.target_pay_for_order = 30.0
    pre_kw = _pre_kw_above_target_at_min(
        text="complete_ch_override",
        hard_status=HardStatus.WHITELIST,
    )
    monkeypatch.setattr(
        ckm_module.PlanFactReader,
        "get_latest_plan_fact",
        AsyncMock(
            return_value=PlanFactSummary(
                adv_id=adv_id,
                plan_orders=10,
                fact_predict_orders=5.0,
                fact_pay_for_order=None,
            )
        ),
    )

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates={},
        now=fixed_now,
    )

    assert result[0].above_target_min_bid is not None
    assert result[0].above_target_min_bid.resolved_target_cost == 95.0


@pytest.mark.asyncio
async def test_no_ch_row_keeps_complex_adv_fallback_target(
    complex_adv_mock_whitelist,
    fixed_now,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv_id = 113
    complex_adv_mock_whitelist.adv_id = adv_id
    complex_adv_mock_whitelist.adv_setting = SimpleNamespace(
        plan_for_sales_for_day=10,
        target_price_for_order=30.0,
        max_price_for_order=95.0,
    )
    complex_adv_mock_whitelist.target_pay_for_order = 30.0
    pre_kw = _pre_kw_above_target_at_min(
        text="no_ch_row_keep_fallback",
        hard_status=HardStatus.WHITELIST,
    )
    monkeypatch.setattr(
        ckm_module.PlanFactReader,
        "get_latest_plan_fact",
        AsyncMock(return_value=None),
    )

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates={},
        now=fixed_now,
    )

    assert result[0].above_target_min_bid is not None
    assert result[0].above_target_min_bid.resolved_target_cost == 30.0


@pytest.mark.asyncio
async def test_missing_plan_fields_do_not_allow_ch_override(
    complex_adv_mock_whitelist,
    fixed_now,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv_id = 114
    complex_adv_mock_whitelist.adv_id = adv_id
    complex_adv_mock_whitelist.adv_setting = SimpleNamespace(
        plan_for_sales_for_day=None,
        target_price_for_order=30.0,
        max_price_for_order=95.0,
    )
    complex_adv_mock_whitelist.target_pay_for_order = 30.0
    pre_kw = _pre_kw_above_target_at_min(
        text="missing_plan_fields_keep_fallback",
        hard_status=HardStatus.WHITELIST,
    )
    monkeypatch.setattr(
        ckm_module.PlanFactReader,
        "get_latest_plan_fact",
        AsyncMock(
            return_value=PlanFactSummary(
                adv_id=adv_id,
                plan_orders=None,
                fact_predict_orders=5.0,
                fact_pay_for_order=None,
            )
        ),
    )

    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates={},
        now=fixed_now,
    )

    assert result[0].above_target_min_bid is not None
    assert result[0].above_target_min_bid.resolved_target_cost == 30.0


# ============================================================================
# resolved_target_cost (complex_adv.target_pay_for_order) для порога МС
# ============================================================================


@pytest.mark.asyncio
async def test_resolved_target_pay_on_complex_adv_tightens_min_bid_cooldown_gate(
    complex_adv_mock_whitelist,
    fixed_now,
) -> None:
    """Как PreComplexAdv.resolved_target_pay_for_order: цель 50 ₽ режет МС; max 200 — нет."""
    adv_id = 999
    complex_adv_mock_whitelist.adv_id = adv_id
    complex_adv_mock_whitelist.adv_setting = SimpleNamespace(
        plan_for_sales_for_day=10,
        target_price_for_order=50,
        max_price_for_order=200,
    )
    # CPM ≤ min_bid (100) нужен для условия МС; conv подобран так, чтобы CPO ≈ 75 ₽.
    _conv_for_pay_75 = 100_000 / 75_000_000
    pre_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="ch_gate",
        keyword_setting__target_place=20,
        cluster_stat__norm_query="ch_gate",
        cluster_stat__position=5.0,
        cluster_stat__cpm=100.0,
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__conv_views_to_orders=_conv_for_pay_75,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )
    updates_ch: dict[str, AboveTargetCooldownEntry | None] = {}
    complex_adv_mock_whitelist.target_pay_for_order = 50.0
    result_ch = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates_ch,
        now=fixed_now,
    )
    assert result_ch[0].status == KeywordStatus.BAD
    assert result_ch[0].reason == KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID

    updates_stub: dict[str, AboveTargetCooldownEntry | None] = {}
    complex_adv_mock_whitelist.target_pay_for_order = 200.0
    result_stub = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates_stub,
        now=fixed_now,
    )
    assert result_stub[0].status == KeywordStatus.GOOD
    assert result_stub[0].reason == KeywordStatusReason.WHITE_LIST


@pytest.mark.asyncio
async def test_above_target_min_bid_first_disable(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """Нет last_disabled: условие выполнено -> BAD МС, в updates время и показы."""
    pre_kw = _pre_kw_above_target_at_min(text="k1", hard_status=HardStatus.WHITELIST)
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert len(result) == 1
    assert result[0].status == KeywordStatus.BAD
    assert result[0].reason == KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
    assert updates.get("k1") == AboveTargetCooldownEntry(fixed_now, 1000)


@pytest.mark.asyncio
async def test_above_target_min_bid_keeps_active_when_pay_below_or_equal_target(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """МС-условие true, но себестоимость ключа <= target: ключ остается активным, cooldown очищаем."""
    complex_adv_mock_whitelist.target_pay_for_order = 2.0
    pre_kw = _pre_kw_above_target_at_min(text="k_allow", hard_status=HardStatus.WHITELIST)
    last = fixed_now - timedelta(hours=3)
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"k_allow": AboveTargetCooldownEntry(last, 1000)},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].status == KeywordStatus.GOOD
    assert result[0].reason == KeywordStatusReason.WHITE_LIST
    assert updates.get("k_allow") is None


@pytest.mark.asyncio
async def test_above_target_min_bid_stays_bad_when_pay_above_target(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """МС-условие true и pay_for_order выше target: текущая BAD/МС логика сохраняется."""
    complex_adv_mock_whitelist.target_pay_for_order = 1.0
    pre_kw = _pre_kw_above_target_at_min(text="k_deny", hard_status=HardStatus.WHITELIST)
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].status == KeywordStatus.BAD
    assert result[0].reason == KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
    assert updates.get("k_deny") == AboveTargetCooldownEntry(fixed_now, 1000)


@pytest.mark.asyncio
async def test_above_target_min_bid_fallback_when_pay_for_order_unavailable(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """Если pay_for_order не вычисляется, gate не срабатывает и остается BAD/МС."""
    complex_adv_mock_whitelist.target_pay_for_order = 100.0
    pre_kw = PreCalculatedKeywordFactory(
        adv_id=12345,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="k_no_pay",
        keyword_setting__target_place=20,
        cluster_stat__norm_query="k_no_pay",
        cluster_stat__position=5.0,
        cluster_stat__cpm=100.0,
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__conv_views_to_orders=0.0,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].status == KeywordStatus.BAD
    assert result[0].reason == KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
    assert updates.get("k_no_pay") == AboveTargetCooldownEntry(fixed_now, 1000)


@pytest.mark.asyncio
async def test_above_target_min_bid_within_24h_no_redis_touch(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    last = fixed_now - timedelta(hours=12)
    pre_kw = _pre_kw_above_target_at_min(text="k2", hard_status=HardStatus.WHITELIST)
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"k2": last},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert updates == {}


@pytest.mark.asyncio
async def test_above_target_min_bid_retest_tag(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """25–26 ч и показов стало больше: обычная логика + метка Т."""
    last = fixed_now - timedelta(hours=25, minutes=30)
    pre_kw = PreCalculatedKeywordFactory(
        adv_id=12345,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="wl_above",
        keyword_setting__target_place=20,
        cluster_stat__norm_query="wl_above",
        cluster_stat__position=5.0,
        cluster_stat__cpm=100.0,
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__conv_views_to_orders=0.05,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"wl_above": AboveTargetCooldownEntry(last, 900)},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].status == KeywordStatus.GOOD
    assert result[0].reason == KeywordStatusReason.WHITE_LIST
    assert result[0].cooldown_display_tag == COOLDOWN_RETEST_DISPLAY_TAG
    assert updates == {}


@pytest.mark.asyncio
async def test_above_target_min_bid_after_25h_new_cycle(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    last = fixed_now - timedelta(hours=26)
    pre_kw = _pre_kw_above_target_at_min(text="k3", hard_status=HardStatus.WHITELIST)
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"k3": last},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].reason == KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
    assert updates.get("k3") == AboveTargetCooldownEntry(fixed_now, 1000)


@pytest.mark.asyncio
async def test_above_target_min_bid_clear_when_condition_false(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    last = fixed_now - timedelta(hours=5)
    # место хуже цели: pos 25 > target 20 -> не «выше цели»
    pre_kw = _pre_kw_above_target_at_min(
        text="k4", position=25.0, target_place=20, hard_status=HardStatus.WHITELIST
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"k4": last},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert updates.get("k4") is None


@pytest.mark.asyncio
async def test_above_target_min_bid_not_applied_when_base_not_good(
    complex_adv_with_hard_min_ctr, fixed_now
) -> None:
    """Без белого списка ключ BAD — правило МС не проверяем, даже если метрики «как у МС»."""
    pre_kw = _pre_kw_above_target_at_min(text="inactive_ms")
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].status == KeywordStatus.BAD
    assert result[0].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert updates == {}


@pytest.mark.asyncio
async def test_above_target_min_bid_clears_redis_when_base_not_good(
    complex_adv_with_hard_min_ctr, fixed_now
) -> None:
    """Был cooldown в Redis, базовое состояние стало BAD — удаляем ключ из Redis."""
    last = fixed_now - timedelta(hours=5)
    pre_kw = _pre_kw_above_target_at_min(text="was_active_now_bad")
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"was_active_now_bad": last},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert updates.get("was_active_now_bad") is None


@pytest.mark.asyncio
async def test_above_target_min_bid_skipped_without_target_place(
    complex_adv_with_hard_min_ctr, fixed_now
) -> None:
    pre_kw = _pre_kw_above_target_at_min(text="k5", target_place=None)
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert updates == {}


@pytest.mark.asyncio
async def test_above_target_min_bid_skipped_zero_cpm(
    complex_adv_with_hard_min_ctr, fixed_now
) -> None:
    pre_kw = _pre_kw_above_target_at_min(text="k6", cpm=0.0)
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert updates == {}


@pytest.mark.asyncio
async def test_above_target_min_bid_retest_window_no_extra_views(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """25–26 ч, но показы не выросли — BAD МС, без метки Т."""
    last = fixed_now - timedelta(hours=25, minutes=30)
    pre_kw = _pre_kw_above_target_at_min(
        text="k_no_extra", hard_status=HardStatus.WHITELIST
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"k_no_extra": AboveTargetCooldownEntry(last, 1000)},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert updates == {}


@pytest.mark.asyncio
async def test_above_target_min_bid_views_drop_updates_baseline(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """Показы упали (сброс суток в CH) — в Redis пишем актуальное v, таймер не сбрасываем."""
    last = fixed_now - timedelta(hours=12)
    pre_kw = _pre_kw_above_target_at_min(
        text="k_drop", position=5.0, views=400, hard_status=HardStatus.WHITELIST
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"k_drop": AboveTargetCooldownEntry(last, 1000)},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert updates.get("k_drop") == AboveTargetCooldownEntry(last, 400)


@pytest.mark.asyncio
async def test_above_target_min_bid_does_not_override_always_on(
    complex_adv_with_hard_min_ctr, fixed_now
) -> None:
    pre_kw = _pre_kw_above_target_at_min(
        text="fixed", hard_status=HardStatus.ALWAYS_ON, target_place=20, position=5.0
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].status == KeywordStatus.GOOD
    assert result[0].reason == KeywordStatusReason.ALWAYS_ON
    assert updates == {}


# ============================================================================
# Diagnostic MS (above_target_min_bid) — mirror factual apply outcome
# ============================================================================


@pytest.mark.asyncio
async def test_ms_diagnostic_pass_by_cost(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    complex_adv_mock_whitelist.target_pay_for_order = 200.0
    pre_kw = _pre_kw_above_target_at_min(text="ms_pass", hard_status=HardStatus.WHITELIST)
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    diag = result[0].above_target_min_bid
    assert diag is not None
    assert diag.state == AboveTargetMinBidDiagnosticState.PASS_BY_COST
    assert result[0].status == KeywordStatus.GOOD
    assert diag.cost_gate_evaluated is True
    assert diag.cost_condition_pass is True


@pytest.mark.asyncio
async def test_ms_diagnostic_blocked_by_cost(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    complex_adv_mock_whitelist.target_pay_for_order = 1.0
    pre_kw = _pre_kw_above_target_at_min(text="ms_block", hard_status=HardStatus.WHITELIST)
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    diag = result[0].above_target_min_bid
    assert diag is not None
    assert diag.state == AboveTargetMinBidDiagnosticState.BLOCKED
    assert result[0].status == KeywordStatus.BAD
    assert result[0].reason == KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID
    assert diag.cost_gate_evaluated is True
    assert diag.cost_condition_pass is False


@pytest.mark.asyncio
async def test_ms_diagnostic_inactive_position_above_target(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    pre_kw = _pre_kw_above_target_at_min(
        text="ms_inactive_pos",
        hard_status=HardStatus.WHITELIST,
        target_place=5,
        position=10.0,
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    diag = result[0].above_target_min_bid
    assert diag is not None
    assert diag.state == AboveTargetMinBidDiagnosticState.INACTIVE
    assert diag.position_condition_pass is False
    assert result[0].status == KeywordStatus.GOOD


@pytest.mark.asyncio
async def test_ms_diagnostic_inactive_cpm_above_min(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    pre_kw = _pre_kw_above_target_at_min(
        text="ms_inactive_cpm",
        hard_status=HardStatus.WHITELIST,
        cpm=150.0,
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    diag = result[0].above_target_min_bid
    assert diag is not None
    assert diag.state == AboveTargetMinBidDiagnosticState.INACTIVE
    assert diag.min_bid_condition_pass is False


@pytest.mark.asyncio
async def test_ms_diagnostic_temporary_recheck(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    last = fixed_now - timedelta(hours=25, minutes=30)
    pre_kw = PreCalculatedKeywordFactory(
        adv_id=12345,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="ms_retest",
        keyword_setting__target_place=20,
        cluster_stat__norm_query="ms_retest",
        cluster_stat__position=5.0,
        cluster_stat__cpm=100.0,
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__conv_views_to_orders=0.05,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"ms_retest": AboveTargetCooldownEntry(last, 900)},
        cooldown_updates=updates,
        now=fixed_now,
    )
    diag = result[0].above_target_min_bid
    assert diag is not None
    assert diag.state == AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK
    assert result[0].status == KeywordStatus.GOOD
    assert result[0].cooldown_display_tag == COOLDOWN_RETEST_DISPLAY_TAG
    assert diag.cost_gate_evaluated is True
    assert diag.cost_condition_pass is False
    ui_line = format_ms_rule_line(diag)
    assert ui_line.startswith("МС: тест")
    assert ">" in ui_line


@pytest.mark.asyncio
async def test_ms_diagnostic_temporary_recheck_missing_threshold(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """Retest при отсутствии threshold: cost gate не оценён."""
    complex_adv_mock_whitelist.target_pay_for_order = None
    complex_adv_mock_whitelist.adv_setting.target_price_for_order = None
    complex_adv_mock_whitelist.adv_setting.max_price_for_order = None
    last = fixed_now - timedelta(hours=25, minutes=30)
    pre_kw = PreCalculatedKeywordFactory(
        adv_id=12345,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="ms_retest_no_thr",
        keyword_setting__target_place=20,
        cluster_stat__norm_query="ms_retest_no_thr",
        cluster_stat__position=5.0,
        cluster_stat__cpm=100.0,
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__conv_views_to_orders=0.05,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={"ms_retest_no_thr": AboveTargetCooldownEntry(last, 900)},
        cooldown_updates=updates,
        now=fixed_now,
    )
    diag = result[0].above_target_min_bid
    assert diag is not None
    assert diag.state == AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK
    assert diag.cost_gate_evaluated is False
    assert diag.reason_no_data == "нет threshold"
    ui_line = format_ms_rule_line(diag)
    assert "threshold н/д" in ui_line
    assert "cost gate не оценён" in ui_line
    assert ">" not in ui_line


@pytest.mark.asyncio
async def test_ms_diagnostic_temporary_recheck_cost_gate_pass_fields(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """Diagnostic fields: pay<=threshold при retest (unit parity через apply helper)."""
    from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_min_bid_cooldown import (
        _ms_gate_snapshot,
        _retest_diagnostic_context,
    )
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
        KeywordState,
    )

    pre_kw = _pre_kw_above_target_at_min(text="ms_retest_pass_fields")
    gates = _ms_gate_snapshot(pre_kw, 100)
    returned = KeywordState(
        status=KeywordStatus.GOOD,
        reason=KeywordStatusReason.WHITE_LIST,
        best_keyword_status=True,
        cooldown_display_tag=COOLDOWN_RETEST_DISPLAY_TAG,
    )
    diag = _retest_diagnostic_context(
        gates=gates,
        keyword_pay_for_order=74.0,
        resolved_target_cost=550.0,
        returned_state=returned,
        cooldown_elapsed_hours=25.5,
    )
    assert diag.state == AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK
    assert diag.cost_gate_evaluated is True
    assert diag.cost_condition_pass is True
    ui_line = format_ms_rule_line(diag)
    assert "≤" in ui_line
    assert ">" not in ui_line.split("PFO")[-1]


@pytest.mark.asyncio
async def test_ms_diagnostic_blocked_without_pfo_no_cost_gate(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    complex_adv_mock_whitelist.target_pay_for_order = 100.0
    pre_kw = PreCalculatedKeywordFactory(
        adv_id=12345,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="ms_no_pfo",
        keyword_setting__target_place=20,
        cluster_stat__norm_query="ms_no_pfo",
        cluster_stat__position=5.0,
        cluster_stat__cpm=100.0,
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__conv_views_to_orders=0.0,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    diag = result[0].above_target_min_bid
    assert diag is not None
    assert diag.state == AboveTargetMinBidDiagnosticState.BLOCKED
    assert result[0].status == KeywordStatus.BAD
    assert diag.cost_gate_evaluated is False
    assert diag.reason_no_data == "нет PFO"
    ui_line = format_ms_rule_line(diag)
    assert "PFO н/д" in ui_line
    assert "100" in ui_line  # threshold из target_pay_for_order=100
    assert "cost gate не оценён: нет PFO" in ui_line
    assert ">" not in ui_line.split("PFO")[-1]


@pytest.mark.asyncio
async def test_ms_diagnostic_prod_like_korea_cosmetics_pass(
    complex_adv_mock_whitelist, fixed_now
) -> None:
    """Кейс adv 32824944: pos 38 < target 71, CPM 510≤510, PFO 74 ≤ threshold 550."""
    complex_adv_mock_whitelist.target_pay_for_order = 550.0
    _conv_for_pay_74 = (1000.0 * 510.0) / (74.0 * 1_000_000.0)
    pre_kw = PreCalculatedKeywordFactory(
        adv_id=32824944,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="косметика женская корея",
        keyword_setting__target_place=71,
        cluster_stat__norm_query="косметика женская корея",
        cluster_stat__position=38.0,
        cluster_stat__cpm=510.0,
        cluster_stat__views=5000,
        cluster_stat__clicks=200,
        cluster_stat__conv_views_to_orders=_conv_for_pay_74,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_mock_whitelist,
        [pre_kw],
        min_bid_for_adv=510,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    kw = result[0]
    diag = kw.above_target_min_bid
    assert diag is not None
    assert diag.state == AboveTargetMinBidDiagnosticState.PASS_BY_COST
    assert kw.status == KeywordStatus.GOOD
    assert kw.reason == KeywordStatusReason.WHITE_LIST
    assert diag.position_condition_pass is True
    assert diag.min_bid_condition_pass is True
    ui_line = format_ms_rule_line(diag)
    assert ui_line.startswith("МС: pass")
    assert "38" in ui_line and "71" in ui_line
    assert "510" in ui_line


def test_ms_diagnostic_no_data_user_facing_reason(fixed_now) -> None:
    """NO_DATA: reason_no_data без имён аргументов apply (cooldown_map и т.п.)."""
    from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_min_bid_cooldown import (
        apply_above_target_min_bid_cooldown,
    )
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
        KeywordState,
    )

    pre_kw = _pre_kw_above_target_at_min(text="ms_no_inputs")
    base = KeywordState(
        status=KeywordStatus.GOOD,
        reason=KeywordStatusReason.WHITE_LIST,
        best_keyword_status=True,
    )
    state = apply_above_target_min_bid_cooldown(
        pre_kw=pre_kw,
        base_state=base,
        min_bid_for_adv=None,
        keyword_pay_for_order=100.0,
        resolved_target_cost=550.0,
        cooldown_map={},
        cooldown_updates={},
        now=fixed_now,
    )
    diag = state.above_target_min_bid
    assert diag is not None
    assert diag.state == AboveTargetMinBidDiagnosticState.NO_DATA
    assert diag.reason_no_data == "нет мин. ставки WB"
    ui_line = format_ms_rule_line(diag)
    assert "cooldown_map" not in ui_line
    assert "cooldown_updates" not in ui_line
    assert "мин. ставки WB" in ui_line
