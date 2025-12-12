"""Тесты для метода CalculatedKeywordsManager.__get_calculated_keywords.

Метод имеет два основных алгоритма:
1. Без белого списка: фильтрация по CTR
2. С белым списком: фильтрация по rating_by_orders и hard_status

Это unit-тесты, не требующие базы данных.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager import (
    CalculatedKeywordsManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus

from tests.factories.keyword_pipeline import (
    PreCalculatedKeywordFactory,
    HardStatus,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def complex_adv_mock():
    """Мок для ComplexAdv с hard_min_ctr=None (используется DEFAULT_MIN_CTR)."""
    mock = MagicMock()
    mock.hard_min_ctr = None
    return mock


@pytest.fixture
def complex_adv_with_hard_min_ctr():
    """Мок для ComplexAdv с заданным hard_min_ctr."""
    mock = MagicMock()
    mock.hard_min_ctr = 0.05  # 5%
    return mock


# ============================================================================
# Тесты без белого списка (фильтрация по CTR)
# ============================================================================


@pytest.mark.asyncio
async def test_no_whitelist_all_keywords_pass_ctr(complex_adv_with_hard_min_ctr):
    """Тест: без белого списка, все ключевые слова проходят по CTR.
    
    Условия:
    - Нет ключевых слов с hard_status=2 (whitelist)
    - Все ключевые слова имеют CTR >= hard_min_ctr
    
    Ожидание:
    - Все ключевые слова получают статус GOOD
    - Причина: MORE_THEN_HARD_MIN_CTR
    """
    adv_id = 12345
    # CTR = clicks / views, hard_min_ctr = 0.05 (5%)
    # Создаём ключевые слова с высоким CTR (views=1000, clicks=100 -> CTR=10%)
    pre_keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=100,  # CTR = 10%
            cluster_stat__final_rating=50.0 + i,
            cluster_stat__norm_query=f"keyword_{i}",
            bidder_keyword_status=BidderKeywordStatus.GOOD

        )
        for i in range(3)
    ]
    
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, pre_keywords
    )
    
    assert len(result) == 3
    for kw in result:
        assert kw.status == KeywordStatus.GOOD
        assert kw.reason == KeywordStatusReason.MORE_THEN_HARD_MIN_CTR


@pytest.mark.asyncio
async def test_no_whitelist_some_keywords_fail_ctr(complex_adv_with_hard_min_ctr):
    """Тест: без белого списка, часть ключевых слов отсеивается по CTR.
    
    Условия:
    - Нет ключевых слов с hard_status=2 (whitelist)
    - Часть ключевых слов имеет CTR < hard_min_ctr
    
    Ожидание:
    - Ключевые слова с CTR >= hard_min_ctr получают статус GOOD
    - Ключевые слова с CTR < hard_min_ctr получают статус BAD
    """
    adv_id = 12345
    # hard_min_ctr = 0.05 (5%)
    
    # Хорошее ключевое слово: CTR = 10%
    good_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="good_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,  # CTR = 10%
        cluster_stat__final_rating=60.0,
        cluster_stat__norm_query="good_keyword",
        bidder_keyword_status=BidderKeywordStatus.GOOD
    )
    
    # Плохое ключевое слово: CTR = 2%
    bad_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="bad_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=20,  # CTR = 2%
        cluster_stat__final_rating=40.0,
        cluster_stat__norm_query="bad_keyword",
    )
    
    pre_keywords = [good_kw, bad_kw]
    
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, pre_keywords
    )
    
    assert len(result) == 2
    
    # Находим результаты по тексту
    result_by_text = {kw.text: kw for kw in result}
    
    assert result_by_text["good_keyword"].status == KeywordStatus.GOOD
    assert result_by_text["good_keyword"].reason == KeywordStatusReason.MORE_THEN_HARD_MIN_CTR
    
    assert result_by_text["bad_keyword"].status == KeywordStatus.BAD
    assert result_by_text["bad_keyword"].reason == KeywordStatusReason.LESS_THEN_HARD_MIN_CTR


@pytest.mark.asyncio
async def test_no_whitelist_uses_default_min_ctr(complex_adv_mock):
    """Тест: без белого списка, используется DEFAULT_MIN_CTR из settings.
    
    Условия:
    - complex_adv.hard_min_ctr = None
    - Должен использоваться settings.DEFAULT_MIN_CTR
    """
    adv_id = 12345
    default_min_ctr = 0.03  # 3%
    
    # Хорошее ключевое слово: CTR = 5%
    good_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="good_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=50,  # CTR = 5%
        cluster_stat__final_rating=60.0,
        cluster_stat__norm_query="good_keyword",
    )
    
    # Плохое ключевое слово: CTR = 1%
    bad_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="bad_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=10,  # CTR = 1%
        cluster_stat__final_rating=40.0,
        cluster_stat__norm_query="bad_keyword",
    )
    
    pre_keywords = [good_kw, bad_kw]
    
    with patch(
        "app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager.settings"
    ) as settings_mock:
        settings_mock.DEFAULT_MIN_CTR = default_min_ctr
        
        result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
            complex_adv_mock, pre_keywords
        )
    
    assert len(result) == 2
    
    result_by_text = {kw.text: kw for kw in result}
    
    assert result_by_text["good_keyword"].status == KeywordStatus.GOOD
    assert result_by_text["bad_keyword"].status == KeywordStatus.BAD


@pytest.mark.asyncio
async def test_no_whitelist_best_keyword_by_ctr(complex_adv_with_hard_min_ctr):
    """Тест: без белого списка, best_keyword определяется по максимальному CTR.
    
    Ожидание:
    - Ключевое слово с максимальным CTR получает best_keyword_status=True
    - Остальные получают best_keyword_status=False
    """
    adv_id = 12345
    
    # Лучшее ключевое слово: CTR = 15%
    best_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="best_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=150,  # CTR = 15%
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="best_keyword",
    )
    
    # Обычное ключевое слово: CTR = 10%
    normal_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="normal_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,  # CTR = 10%
        cluster_stat__final_rating=60.0,
        cluster_stat__norm_query="normal_keyword",
    )
    
    pre_keywords = [best_kw, normal_kw]
    
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, pre_keywords
    )
    
    result_by_text = {kw.text: kw for kw in result}
    
    assert result_by_text["best_keyword"].best_keyword_status is True
    assert result_by_text["normal_keyword"].best_keyword_status is False


# ============================================================================
# Тесты без белого списка с разным количеством слов
# ============================================================================


@pytest.mark.asyncio
async def test_no_whitelist_single_keyword(complex_adv_with_hard_min_ctr):
    """Тест: без БС, 1 ключевое слово.
    
    Условия:
    - 1 слово в тестировании (hard_status=1)
    - CTR >= hard_min_ctr
    
    Ожидание:
    - Единственное слово -> GOOD и best_keyword_status=True
    """
    adv_id = 12345
    
    single_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="single_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,  # CTR = 10% >= 5%
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="single_keyword",
    )
    
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, [single_kw]
    )
    
    assert len(result) == 1
    assert result[0].status == KeywordStatus.GOOD
    assert result[0].reason == KeywordStatusReason.MORE_THEN_HARD_MIN_CTR
    assert result[0].best_keyword_status is True


@pytest.mark.asyncio
async def test_no_whitelist_ten_keywords_mixed_ctr(complex_adv_with_hard_min_ctr):
    """Тест: без БС, 10 ключевых слов с разным CTR.
    
    Условия:
    - 10 слов в тестировании
    - hard_min_ctr = 5%
    - CTR от 1% до 10%
    
    Ожидание:
    - CTR >= 5% -> GOOD (5 слов: 5%, 6%, 7%, 8%, 9%, 10%)
    - CTR < 5% -> BAD (4 слова: 1%, 2%, 3%, 4%)
    - Best = слово с максимальным CTR (10%)
    """
    adv_id = 12345
    
    # 10 слов с CTR от 1% до 10%
    keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=10 + i * 10,  # CTR: 1%, 2%, 3%, ..., 10%
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
    
    # CTR < 5% -> BAD (keyword_0: 1%, keyword_1: 2%, keyword_2: 3%, keyword_3: 4%)
    for i in range(4):
        assert result_by_text[f"keyword_{i}"].status == KeywordStatus.BAD
        assert result_by_text[f"keyword_{i}"].reason == KeywordStatusReason.LESS_THEN_HARD_MIN_CTR
    
    # CTR >= 5% -> GOOD (keyword_4: 5%, ..., keyword_9: 10%)
    for i in range(4, 10):
        assert result_by_text[f"keyword_{i}"].status == KeywordStatus.GOOD
        assert result_by_text[f"keyword_{i}"].reason == KeywordStatusReason.MORE_THEN_HARD_MIN_CTR
    
    # Best = keyword_9 с максимальным CTR (10%)
    assert result_by_text["keyword_9"].best_keyword_status is True
    for i in range(9):
        assert result_by_text[f"keyword_{i}"].best_keyword_status is False


@pytest.mark.asyncio
async def test_no_whitelist_twenty_keywords_all_good(complex_adv_with_hard_min_ctr):
    """Тест: без БС, 20 ключевых слов, все проходят по CTR.
    
    Условия:
    - 20 слов в тестировании
    - Все с CTR >= hard_min_ctr (5%)
    
    Ожидание:
    - Все 20 слов -> GOOD
    - Best = слово с максимальным CTR
    """
    adv_id = 12345
    
    # 20 слов с CTR от 6% до 25%
    keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=60 + i * 10,  # CTR: 6%, 7%, ..., 25%
            cluster_stat__final_rating=50.0,
            cluster_stat__norm_query=f"keyword_{i}",
        )
        for i in range(20)
    ]
    
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, keywords
    )
    
    assert len(result) == 20
    result_by_text = {kw.text: kw for kw in result}
    
    # Все -> GOOD
    for i in range(20):
        assert result_by_text[f"keyword_{i}"].status == KeywordStatus.GOOD
    
    # Best = keyword_19 с максимальным CTR (25%)
    assert result_by_text["keyword_19"].best_keyword_status is True


@pytest.mark.asyncio
async def test_no_whitelist_twenty_keywords_all_bad(complex_adv_with_hard_min_ctr):
    """Тест: без БС, 20 ключевых слов, все НЕ проходят по CTR.
    
    Условия:
    - 20 слов в тестировании
    - Все с CTR < hard_min_ctr (5%)
    
    Ожидание:
    - Все 20 слов -> BAD
    - Best всё равно определяется (слово с максимальным CTR)
    """
    adv_id = 12345
    
    # 20 слов с низким CTR от 0.1% до 2%
    keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=1 + i,  # CTR: 0.1%, 0.2%, ..., 2%
            cluster_stat__final_rating=50.0,
            cluster_stat__norm_query=f"keyword_{i}",
        )
        for i in range(20)
    ]
    
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, keywords
    )
    
    assert len(result) == 20
    result_by_text = {kw.text: kw for kw in result}
    
    # Все -> BAD (CTR < 5%)
    for i in range(20):
        assert result_by_text[f"keyword_{i}"].status == KeywordStatus.BAD
        assert result_by_text[f"keyword_{i}"].reason == KeywordStatusReason.LESS_THEN_HARD_MIN_CTR
    
    # Best = keyword_19 с максимальным CTR (2%)
    assert result_by_text["keyword_19"].best_keyword_status is True


@pytest.mark.asyncio
async def test_no_whitelist_fifty_keywords(complex_adv_with_hard_min_ctr):
    """Тест: без БС, 50 ключевых слов - большой набор.
    
    Условия:
    - 50 слов в тестировании
    - hard_min_ctr = 5%
    - CTR распределён от 1% до 15%
    
    Ожидание:
    - Корректная фильтрация по CTR
    - Best = слово с максимальным CTR
    """
    adv_id = 12345
    
    # 50 слов с CTR от 1% до ~15%
    keywords = [
        PreCalculatedKeywordFactory(
            adv_id=adv_id,
            keyword_setting__hard_status=HardStatus.IN_TEST,
            keyword_setting__text=f"keyword_{i}",
            cluster_stat__views=1000,
            cluster_stat__clicks=10 + i * 3,  # CTR: 1%, 1.3%, 1.6%, ..., ~15.7%
            cluster_stat__final_rating=50.0,
            cluster_stat__norm_query=f"keyword_{i}",
        )
        for i in range(50)
    ]
    
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, keywords
    )
    
    assert len(result) == 50
    result_by_text = {kw.text: kw for kw in result}
    
    # Подсчитаем GOOD и BAD
    good_count = sum(1 for kw in result if kw.status == KeywordStatus.GOOD)
    bad_count = sum(1 for kw in result if kw.status == KeywordStatus.BAD)
    
    # CTR >= 5% (50 кликов) -> GOOD
    # 10 + i * 3 >= 50 -> i >= 13.33 -> i >= 14
    # Значит keyword_0 до keyword_13 -> BAD (14 штук)
    # keyword_14 до keyword_49 -> GOOD (36 штук)
    assert bad_count == 14
    assert good_count == 36
    
    # Best = keyword_49 с максимальным CTR
    assert result_by_text["keyword_49"].best_keyword_status is True


@pytest.mark.asyncio
async def test_no_whitelist_with_blacklist_keywords(complex_adv_with_hard_min_ctr):
    """Тест: без БС, но есть слова в blacklist.
    
    Условия:
    - Нет слов с hard_status=2 (whitelist) -> алгоритм без БС
    - Есть слова с hard_status=0 (blacklist)
    - Есть слова с hard_status=1 (in_test)
    
    Важно: алгоритм без БС НЕ проверяет blacklist!
    Он просто фильтрует по CTR.
    """
    adv_id = 12345
    
    # Blacklist слово с высоким CTR
    blacklist_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.BLACKLIST,
        keyword_setting__text="blacklist_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=100,  # CTR = 10%
        cluster_stat__final_rating=50.0,
        cluster_stat__norm_query="blacklist_keyword",
    )
    
    # IN_TEST слово
    in_test_kw = PreCalculatedKeywordFactory(
        adv_id=adv_id,
        keyword_setting__hard_status=HardStatus.IN_TEST,
        keyword_setting__text="in_test_keyword",
        cluster_stat__views=1000,
        cluster_stat__clicks=80,  # CTR = 8%
        cluster_stat__final_rating=60.0,
        cluster_stat__norm_query="in_test_keyword",
    )
    
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv_with_hard_min_ctr, [blacklist_kw, in_test_kw]
    )
    
    assert len(result) == 2
    result_by_text = {kw.text: kw for kw in result}
    
    # В режиме без БС - фильтрация только по CTR!
    # Blacklist слово тоже получит GOOD, т.к. CTR >= 5%
    assert result_by_text["blacklist_keyword"].status == KeywordStatus.GOOD
    assert result_by_text["blacklist_keyword"].reason == KeywordStatusReason.MORE_THEN_HARD_MIN_CTR
    
    assert result_by_text["in_test_keyword"].status == KeywordStatus.GOOD
    
    # Best = blacklist_keyword с максимальным CTR (10%)
    assert result_by_text["blacklist_keyword"].best_keyword_status is True


# ============================================================================
# Тесты с белым списком (фильтрация по rating_by_orders и hard_status)
# ============================================================================


@pytest.mark.asyncio
async def test_whitelist_hard_status_whitelist(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    result_by_text = {kw.text: kw for kw in result}
    
    assert result_by_text["whitelist_keyword"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_keyword"].reason == KeywordStatusReason.WHITE_LIST


@pytest.mark.asyncio
async def test_whitelist_hard_status_blacklist(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    result_by_text = {kw.text: kw for kw in result}
    
    assert result_by_text["blacklist_keyword"].status == KeywordStatus.BAD
    assert result_by_text["blacklist_keyword"].reason == KeywordStatusReason.BLACK_LIST


@pytest.mark.asyncio
async def test_whitelist_hard_status_turn_off(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    result_by_text = {kw.text: kw for kw in result}
    
    assert result_by_text["turn_off_keyword"].status == KeywordStatus.BAD
    assert result_by_text["turn_off_keyword"].reason == KeywordStatusReason.TURN_OFF


@pytest.mark.asyncio
async def test_whitelist_rating_by_orders_filtering(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    result_by_text = {kw.text: kw for kw in result}
    
    # Whitelist всегда GOOD
    assert result_by_text["whitelist_low"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_high"].status == KeywordStatus.GOOD
    
    # IN_TEST зависит от сравнения с худшим whitelist
    assert result_by_text["in_test_good"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_good"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    
    assert result_by_text["in_test_bad"].status == KeywordStatus.BAD
    assert result_by_text["in_test_bad"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS


@pytest.mark.asyncio
async def test_whitelist_best_keyword_by_rating(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    result_by_text = {kw.text: kw for kw in result}
    
    assert result_by_text["best_keyword"].best_keyword_status is True
    assert result_by_text["whitelist_low"].best_keyword_status is False
    assert result_by_text["normal_keyword"].best_keyword_status is False


# ============================================================================
# Тесты с разным количеством слов в белом списке
# ============================================================================


@pytest.mark.asyncio
async def test_whitelist_single_keyword(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
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
async def test_whitelist_three_keywords_different_ratings(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    result_by_text = {kw.text: kw for kw in result}
    
    # Все whitelist -> GOOD
    assert result_by_text["whitelist_low"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_mid"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_high"].status == KeywordStatus.GOOD
    
    # IN_TEST между -> GOOD (выше порога)
    assert result_by_text["in_test_between"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_between"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    
    # IN_TEST ниже -> BAD
    assert result_by_text["in_test_lowest"].status == KeywordStatus.BAD
    assert result_by_text["in_test_lowest"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS


@pytest.mark.asyncio
async def test_whitelist_five_keywords_all_same_rating(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    result_by_text = {kw.text: kw for kw in result}
    
    # Все whitelist -> GOOD
    for i in range(5):
        assert result_by_text[f"whitelist_{i}"].status == KeywordStatus.GOOD
    
    assert result_by_text["in_test_equal"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_below"].status == KeywordStatus.BAD


@pytest.mark.asyncio
async def test_whitelist_ten_keywords_large_spread(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    result_by_text = {kw.text: kw for kw in result}
    
    # Все whitelist -> GOOD
    for i in range(10):
        assert result_by_text[f"whitelist_{i}"].status == KeywordStatus.GOOD
        assert result_by_text[f"whitelist_{i}"].reason == KeywordStatusReason.WHITE_LIST
    
    # IN_TEST mid -> GOOD
    assert result_by_text["in_test_mid"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_mid"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    
    # IN_TEST lowest -> BAD
    assert result_by_text["in_test_lowest"].status == KeywordStatus.BAD
    assert result_by_text["in_test_lowest"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    
    # IN_TEST highest -> GOOD и best
    assert result_by_text["in_test_highest"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_highest"].best_keyword_status is True


@pytest.mark.asyncio
async def test_whitelist_mixed_with_all_hard_statuses(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    assert len(result) == 10
    result_by_text = {kw.text: kw for kw in result}
    
    # Whitelist -> GOOD
    assert result_by_text["whitelist_1"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_1"].reason == KeywordStatusReason.WHITE_LIST
    assert result_by_text["whitelist_2"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_3"].status == KeywordStatus.GOOD
    
    # Blacklist -> BAD
    assert result_by_text["blacklist_1"].status == KeywordStatus.BAD
    assert result_by_text["blacklist_1"].reason == KeywordStatusReason.BLACK_LIST
    assert result_by_text["blacklist_2"].status == KeywordStatus.BAD
    assert result_by_text["blacklist_2"].reason == KeywordStatusReason.BLACK_LIST
    
    # Turn_off -> BAD
    assert result_by_text["turn_off"].status == KeywordStatus.BAD
    assert result_by_text["turn_off"].reason == KeywordStatusReason.TURN_OFF
    
    # IN_TEST good -> GOOD
    assert result_by_text["in_test_good_1"].status == KeywordStatus.GOOD
    assert result_by_text["in_test_good_1"].reason == KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_good_2"].status == KeywordStatus.GOOD
    
    # IN_TEST bad -> BAD
    assert result_by_text["in_test_bad_1"].status == KeywordStatus.BAD
    assert result_by_text["in_test_bad_1"].reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
    assert result_by_text["in_test_bad_2"].status == KeywordStatus.BAD


@pytest.mark.asyncio
async def test_whitelist_only_whitelist_keywords(complex_adv_mock):
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
        complex_adv_mock, whitelist_keywords
    )
    
    assert len(result) == 5
    result_by_text = {kw.text: kw for kw in result}
    
    # Все whitelist -> GOOD
    for i in range(5):
        assert result_by_text[f"whitelist_{i}"].status == KeywordStatus.GOOD
        assert result_by_text[f"whitelist_{i}"].reason == KeywordStatusReason.WHITE_LIST
    
    # Best - с максимальным рейтингом (whitelist_4 с рейтингом 80)
    assert result_by_text["whitelist_4"].best_keyword_status is True
    for i in range(4):
        assert result_by_text[f"whitelist_{i}"].best_keyword_status is False


@pytest.mark.asyncio
async def test_whitelist_many_in_test_few_whitelist(complex_adv_mock):
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
        complex_adv_mock, pre_keywords
    )
    
    assert len(result) == 22
    result_by_text = {kw.text: kw for kw in result}
    
    # Whitelist -> GOOD
    assert result_by_text["whitelist_low"].status == KeywordStatus.GOOD
    assert result_by_text["whitelist_high"].status == KeywordStatus.GOOD
    
    # IN_TEST: рейтинг >= 25 -> GOOD, < 25 -> BAD
    # in_test_0: 5 < 25 -> BAD
    # in_test_1: 10 < 25 -> BAD
    # in_test_2: 15 < 25 -> BAD
    # in_test_3: 20 < 25 -> BAD
    # in_test_4: 25 >= 25 -> GOOD
    # ...
    for i in range(4):
        assert result_by_text[f"in_test_{i}"].status == KeywordStatus.BAD
    
    for i in range(4, 20):
        assert result_by_text[f"in_test_{i}"].status == KeywordStatus.GOOD
    
    # Best - in_test_19 с рейтингом 100
    assert result_by_text["in_test_19"].best_keyword_status is True

