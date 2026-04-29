from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.shop_runner.service_manager.services.minus_phrase_manager.minus_phrase_manager import (
    MinusPhraseManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus


def _make_complex_adv() -> SimpleNamespace:
    async def _get_keywords() -> list[SimpleNamespace]:
        return [
            SimpleNamespace(text="bad_for_11", status=KeywordStatus.BAD),
            SimpleNamespace(text="bad_for_22", status=KeywordStatus.BAD),
        ]

    return SimpleNamespace(
        shop_id="shop-x",
        adv_id=555,
        auto_adv_id=777,
        search_adv=None,
        adv_setting=SimpleNamespace(nmids=[11, 22]),
        get_keywords=_get_keywords,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_uses_adv_plus_nmid_scope() -> None:
    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=[]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(
            side_effect=[
                SimpleNamespace(
                    dropped_invalid_phrases=[],
                    applied_phrases=["bad_for_11"],
                ),
                SimpleNamespace(
                    dropped_invalid_phrases=[],
                    applied_phrases=["bad_for_22"],
                ),
            ]
        ),
    )
    wb_hub = SimpleNamespace(wb_modifier=wb_modifier)
    click_house = SimpleNamespace(
        get_cluster_texts_for_adv_nmid=AsyncMock(
            side_effect=[["bad_for_11"], ["bad_for_22"]]
        )
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=wb_hub,
        click_house_manager=click_house,
        update_redis_timestamp_manager=SimpleNamespace(),
    )

    await manager.update_minus_phrases(_make_complex_adv())

    assert click_house.get_cluster_texts_for_adv_nmid.await_args_list[0].args == (777, 11)
    assert click_house.get_cluster_texts_for_adv_nmid.await_args_list[1].args == (777, 22)
    assert wb_modifier.set_minus_phrases_with_fallback_for_adv.await_args_list[0].kwargs[
        "phrases"
    ] == ["bad_for_11"]
    assert wb_modifier.set_minus_phrases_with_fallback_for_adv.await_args_list[1].kwargs[
        "phrases"
    ] == ["bad_for_22"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_isolates_nmid_failures(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("ERROR")

    async def _fake_set_minus(**kwargs: object) -> SimpleNamespace:
        if kwargs["nmid"] == 11:
            raise RuntimeError("nmid-11-failed")
        return SimpleNamespace(
            dropped_invalid_phrases=[],
            applied_phrases=["bad_for_22"],
        )

    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=[]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(side_effect=_fake_set_minus),
    )
    wb_hub = SimpleNamespace(wb_modifier=wb_modifier)
    click_house = SimpleNamespace(
        get_cluster_texts_for_adv_nmid=AsyncMock(
            side_effect=[["bad_for_11"], ["bad_for_22"]]
        )
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=wb_hub,
        click_house_manager=click_house,
        update_redis_timestamp_manager=SimpleNamespace(),
    )

    await manager.update_minus_phrases(_make_complex_adv())

    assert wb_modifier.set_minus_phrases_with_fallback_for_adv.await_count == 2
    assert "Ошибка обновления РК по nmid" in caplog.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_does_not_clear_when_nmid_has_no_overlap() -> None:
    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=["already_exists"]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(),
    )
    wb_hub = SimpleNamespace(wb_modifier=wb_modifier)
    click_house = SimpleNamespace(
        get_cluster_texts_for_adv_nmid=AsyncMock(
            side_effect=[["unrelated_11"], ["unrelated_22"]]
        )
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=wb_hub,
        click_house_manager=click_house,
        update_redis_timestamp_manager=SimpleNamespace(),
    )

    await manager.update_minus_phrases(_make_complex_adv())

    assert wb_modifier.get_minus_phrases_for_adv.await_count == 0
    wb_modifier.set_minus_phrases_with_fallback_for_adv.assert_not_awaited()
