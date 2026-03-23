"""Тесты FirstKeyUpdater: ворота 1/2/4 и кандидаты через KeywordsManager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.first_key_updater.first_key_updater import (
    FirstKeyUpdater,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)

MODULE = (
    "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater"
    ".modules.first_key_updater.first_key_updater"
)


def _calc_kw(
    *,
    ks_id: int,
    text: str,
    hard_status: int,
    rating: float,
    status: KeywordStatus,
    views: int = 10,
    relevant: bool = True,
    above_rec: bool | None = True,
) -> CalculatedKeyword:
    stat = make_zero_keyword_stat(text).model_copy(update={"views": views})
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=text,
            relevant=relevant,
            hard_status=hard_status,
            id=ks_id,
        ),
        cluster_stat=stat,
        state=KeywordState(
            status=status,
            reason=KeywordStatusReason.BIDDER_BAD_STATUS,
            best_keyword_status=False,
        ),
        rating=rating,
        target_pay_for_order=None,
        above_rec_conversion=above_rec,
    )


@pytest.fixture
def adv_setting() -> AdvSetting:
    adv = MagicMock(spec=AdvSetting)
    adv.auto_add_only_relevant_phrase = False
    return adv


@pytest.mark.asyncio
async def test_gate_top_white_skips_without_fetching_candidates(adv_setting: AdvSetting) -> None:
    keywords = [
        _calc_kw(ks_id=1, text="a", hard_status=2, rating=100.0, status=KeywordStatus.BAD),
        _calc_kw(ks_id=2, text="b", hard_status=1, rating=50.0, status=KeywordStatus.BAD),
    ]
    complex_adv = MagicMock()
    complex_adv.get_keywords = AsyncMock(return_value=keywords)

    with patch(f"{MODULE}.KeywordsManager.get_candidates_to_white_list", new_callable=AsyncMock) as get_cand:
        await FirstKeyUpdater(adv_setting).top_key_auto_update(complex_adv)
        get_cand.assert_not_called()


@pytest.mark.asyncio
async def test_gate_top_fixed_skips_without_fetching_candidates(adv_setting: AdvSetting) -> None:
    keywords = [
        _calc_kw(ks_id=1, text="a", hard_status=4, rating=100.0, status=KeywordStatus.BAD),
        _calc_kw(ks_id=2, text="b", hard_status=1, rating=50.0, status=KeywordStatus.BAD),
    ]
    complex_adv = MagicMock()
    complex_adv.get_keywords = AsyncMock(return_value=keywords)

    with patch(f"{MODULE}.KeywordsManager.get_candidates_to_white_list", new_callable=AsyncMock) as get_cand:
        await FirstKeyUpdater(adv_setting).top_key_auto_update(complex_adv)
        get_cand.assert_not_called()


@pytest.mark.asyncio
async def test_no_candidates_no_db_session(adv_setting: AdvSetting) -> None:
    keywords = [
        _calc_kw(ks_id=1, text="a", hard_status=1, rating=10.0, status=KeywordStatus.BAD),
    ]
    complex_adv = MagicMock()
    complex_adv.get_keywords = AsyncMock(return_value=keywords)

    session_mock = MagicMock()
    session_mock.execute = AsyncMock()
    session_mock.commit = AsyncMock()
    maker_mock = MagicMock()
    maker_mock.__aenter__ = AsyncMock(return_value=session_mock)
    maker_mock.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            f"{MODULE}.KeywordsManager.get_candidates_to_white_list",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(f"{MODULE}.sm", return_value=maker_mock),
    ):
        await FirstKeyUpdater(adv_setting).top_key_auto_update(complex_adv)
    session_mock.execute.assert_not_called()


@pytest.mark.asyncio
async def test_promotes_best_candidate(adv_setting: AdvSetting) -> None:
    keywords = [
        _calc_kw(ks_id=1, text="a", hard_status=1, rating=10.0, status=KeywordStatus.BAD),
    ]
    best = _calc_kw(ks_id=99, text="best", hard_status=1, rating=5.0, status=KeywordStatus.BAD)
    complex_adv = MagicMock()
    complex_adv.get_keywords = AsyncMock(return_value=keywords)

    session_mock = MagicMock()
    session_mock.execute = AsyncMock()
    session_mock.commit = AsyncMock()
    maker_mock = MagicMock()
    maker_mock.__aenter__ = AsyncMock(return_value=session_mock)
    maker_mock.__aexit__ = AsyncMock(return_value=None)

    ts_instance = MagicMock()
    ts_instance.set_timestamp = AsyncMock()

    with (
        patch(
            f"{MODULE}.KeywordsManager.get_candidates_to_white_list",
            new_callable=AsyncMock,
            return_value=[best],
        ),
        patch(f"{MODULE}.sm", return_value=maker_mock),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater"
            ".modules.first_key_updater.timestamp_update_redis_cache.LastUpdateFirstPhrase",
            return_value=ts_instance,
        ),
    ):
        await FirstKeyUpdater(adv_setting).top_key_auto_update(complex_adv)

    session_mock.execute.assert_called_once()
    ts_instance.set_timestamp.assert_awaited_once()
