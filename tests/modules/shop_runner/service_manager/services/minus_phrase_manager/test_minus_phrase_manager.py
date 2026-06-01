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


def _make_state_manager() -> SimpleNamespace:
    return SimpleNamespace(
        get_invalid_norm_queries=AsyncMock(return_value=[]),
        add_invalid_norm_queries=AsyncMock(return_value=[]),
        set_one=AsyncMock(return_value=None),
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
        update_redis_timestamp_manager=_make_state_manager(),
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
        update_redis_timestamp_manager=_make_state_manager(),
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
        update_redis_timestamp_manager=_make_state_manager(),
    )

    await manager.update_minus_phrases(_make_complex_adv())

    assert wb_modifier.get_minus_phrases_for_adv.await_count == 0
    wb_modifier.set_minus_phrases_with_fallback_for_adv.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_minus_skips_set_when_wb_already_matches_target() -> None:
    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=["bad_for_11"]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(),
    )
    wb_hub = SimpleNamespace(wb_modifier=wb_modifier)
    click_house = SimpleNamespace(
        get_cluster_texts_for_adv_nmid=AsyncMock(
            side_effect=[["bad_for_11"], ["unrelated_22"]]
        )
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=wb_hub,
        click_house_manager=click_house,
        update_redis_timestamp_manager=_make_state_manager(),
    )

    await manager.update_minus_phrases(_make_complex_adv())

    wb_modifier.set_minus_phrases_with_fallback_for_adv.assert_not_awaited()
    assert wb_modifier.get_minus_phrases_for_adv.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_uses_known_invalid_between_runs() -> None:
    class _State:
        def __init__(self) -> None:
            self.invalid: dict[tuple[int, int], list[str]] = {}

        async def get_invalid_norm_queries(self, adv_id: int, nmid: int) -> list[str]:
            return list(self.invalid.get((adv_id, nmid), []))

        async def add_invalid_norm_queries(
            self, adv_id: int, nmid: int, phrases: list[str]
        ) -> list[str]:
            current = self.invalid.get((adv_id, nmid), [])
            merged = list(dict.fromkeys([*current, *phrases]))
            self.invalid[(adv_id, nmid)] = merged
            return merged

        async def set_one(self, adv_id: int) -> None:
            return None

    state = _State()
    set_calls: list[list[str]] = []

    async def _fake_set_minus(**kwargs: object) -> SimpleNamespace:
        phrases = list(kwargs["phrases"])  # type: ignore[index]
        set_calls.append(phrases)
        if "bad_for_11" in phrases:
            return SimpleNamespace(
                dropped_invalid_phrases=["bad_for_11"],
                applied_phrases=["bad_for_22"],
            )
        return SimpleNamespace(dropped_invalid_phrases=[], applied_phrases=phrases)

    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(side_effect=[[], ["bad_for_22"]]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(side_effect=_fake_set_minus),
    )
    wb_hub = SimpleNamespace(wb_modifier=wb_modifier)
    click_house = SimpleNamespace(
        get_cluster_texts_for_adv_nmid=AsyncMock(
            side_effect=[["bad_for_11", "bad_for_22"], ["bad_for_11", "bad_for_22"]]
        )
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=wb_hub,
        click_house_manager=click_house,
        update_redis_timestamp_manager=state,  # type: ignore[arg-type]
    )

    complex_adv = SimpleNamespace(
        shop_id="shop-x",
        adv_id=555,
        auto_adv_id=777,
        search_adv=None,
        adv_setting=SimpleNamespace(nmids=[11]),
        get_keywords=_make_complex_adv().get_keywords,
    )

    await manager.update_minus_phrases(complex_adv)
    await manager.update_minus_phrases(complex_adv)

    assert len(set_calls) == 1
    assert set(set_calls[0]) == {"bad_for_11", "bad_for_22"}
    assert state.invalid[(777, 11)] == ["bad_for_11"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_logs_warning_for_dropped_invalid(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("WARNING")
    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=[]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(
            return_value=SimpleNamespace(
                dropped_invalid_phrases=["bad_for_11"],
                applied_phrases=["bad_for_22"],
            )
        ),
    )
    wb_hub = SimpleNamespace(wb_modifier=wb_modifier)
    click_house = SimpleNamespace(
        get_cluster_texts_for_adv_nmid=AsyncMock(
            side_effect=[["bad_for_11", "bad_for_22"], ["unrelated_22"]]
        )
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=wb_hub,
        click_house_manager=click_house,
        update_redis_timestamp_manager=_make_state_manager(),
    )

    await manager.update_minus_phrases(_make_complex_adv())

    assert "fallback" in caplog.text
    assert "отброшено" in caplog.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_processes_search_adv() -> None:
    async def _get_keywords() -> list[SimpleNamespace]:
        return [SimpleNamespace(text="bad", status=KeywordStatus.BAD)]

    complex_adv = SimpleNamespace(
        shop_id="shop-x",
        adv_id=555,
        auto_adv_id=777,
        search_adv=SimpleNamespace(adv_id=888, nmids=[33]),
        adv_setting=SimpleNamespace(nmids=[11]),
        get_keywords=_get_keywords,
    )
    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=[]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(
            return_value=SimpleNamespace(
                dropped_invalid_phrases=[],
                applied_phrases=["bad"],
            )
        ),
    )
    wb_hub = SimpleNamespace(wb_modifier=wb_modifier)
    click_house = SimpleNamespace(
        get_cluster_texts_for_adv_nmid=AsyncMock(side_effect=[["bad"], ["bad"]])
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=wb_hub,
        click_house_manager=click_house,
        update_redis_timestamp_manager=_make_state_manager(),
    )

    await manager.update_minus_phrases(complex_adv)

    assert click_house.get_cluster_texts_for_adv_nmid.await_args_list[0].args == (777, 11)
    assert click_house.get_cluster_texts_for_adv_nmid.await_args_list[1].args == (888, 33)
    assert wb_modifier.set_minus_phrases_with_fallback_for_adv.await_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_minus_truncates_to_1000_phrases() -> None:
    huge_phrases = [f"bad_{i}" for i in range(1200)]

    async def _get_keywords() -> list[SimpleNamespace]:
        return [SimpleNamespace(text=text, status=KeywordStatus.BAD) for text in huge_phrases]

    complex_adv = SimpleNamespace(
        shop_id="shop-x",
        adv_id=555,
        auto_adv_id=777,
        search_adv=None,
        adv_setting=SimpleNamespace(nmids=[11]),
        get_keywords=_get_keywords,
    )
    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=[]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(
            return_value=SimpleNamespace(
                dropped_invalid_phrases=[],
                applied_phrases=huge_phrases[:1000],
            )
        ),
    )
    wb_hub = SimpleNamespace(wb_modifier=wb_modifier)
    click_house = SimpleNamespace(
        get_cluster_texts_for_adv_nmid=AsyncMock(return_value=huge_phrases)
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=wb_hub,
        click_house_manager=click_house,
        update_redis_timestamp_manager=_make_state_manager(),
    )

    await manager.update_minus_phrases(complex_adv)

    sent_phrases = wb_modifier.set_minus_phrases_with_fallback_for_adv.await_args.kwargs[
        "phrases"
    ]
    assert len(sent_phrases) == 1000


def _adv_setting_with_meta(
    *,
    wb_bid_type: str | None = None,
    wb_placement_search: bool | None = None,
    wb_placement_recommendations: bool | None = None,
    nmids: list[int] | None = None,
    adv_id: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        adv_id=adv_id,
        nmids=nmids or [11],
        wb_bid_type=wb_bid_type,
        wb_placement_search=wb_placement_search,
        wb_placement_recommendations=wb_placement_recommendations,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_skips_manual_shelf_only_auto_adv() -> None:
    async def _get_keywords() -> list[SimpleNamespace]:
        return [SimpleNamespace(text="bad_for_11", status=KeywordStatus.BAD)]

    complex_adv = SimpleNamespace(
        shop_id="shop-x",
        adv_id=555,
        auto_adv_id=32824944,
        search_adv=None,
        adv_setting=_adv_setting_with_meta(
            wb_bid_type="manual",
            wb_placement_search=False,
            wb_placement_recommendations=True,
        ),
        get_keywords=_get_keywords,
    )
    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=[]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(),
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=SimpleNamespace(wb_modifier=wb_modifier),
        click_house_manager=SimpleNamespace(
            get_cluster_texts_for_adv_nmid=AsyncMock(return_value=["bad_for_11"])
        ),
        update_redis_timestamp_manager=_make_state_manager(),
    )

    await manager.update_minus_phrases(complex_adv)

    wb_modifier.set_minus_phrases_with_fallback_for_adv.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_skips_search_adv_without_search_placement() -> None:
    async def _get_keywords() -> list[SimpleNamespace]:
        return [SimpleNamespace(text="bad", status=KeywordStatus.BAD)]

    complex_adv = SimpleNamespace(
        shop_id="shop-x",
        adv_id=555,
        auto_adv_id=777,
        search_adv=_adv_setting_with_meta(
            adv_id=888,
            nmids=[33],
            wb_bid_type="manual",
            wb_placement_search=False,
            wb_placement_recommendations=True,
        ),
        adv_setting=_adv_setting_with_meta(
            wb_bid_type="unified",
            wb_placement_search=True,
            wb_placement_recommendations=True,
        ),
        get_keywords=_get_keywords,
    )
    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=[]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(
            return_value=SimpleNamespace(
                dropped_invalid_phrases=[],
                applied_phrases=["bad"],
                skipped_unsupported_campaign=False,
            )
        ),
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=SimpleNamespace(wb_modifier=wb_modifier),
        click_house_manager=SimpleNamespace(
            get_cluster_texts_for_adv_nmid=AsyncMock(
                side_effect=[["bad"], ["bad"]]
            )
        ),
        update_redis_timestamp_manager=_make_state_manager(),
    )

    await manager.update_minus_phrases(complex_adv)

    assert wb_modifier.set_minus_phrases_with_fallback_for_adv.await_count == 1
    assert (
        wb_modifier.set_minus_phrases_with_fallback_for_adv.await_args.kwargs["adv_id"]
        == 777
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auto_nmid_exception_does_not_abort_search_path() -> None:
    """Ошибка set-minus на одном nmid авто не валит search (return_exceptions в __update_minus_phrases)."""
    async def _get_keywords() -> list[SimpleNamespace]:
        return [SimpleNamespace(text="bad", status=KeywordStatus.BAD)]

    complex_adv = SimpleNamespace(
        shop_id="shop-x",
        adv_id=555,
        auto_adv_id=777,
        search_adv=SimpleNamespace(
            adv_id=888,
            nmids=[33],
            wb_bid_type="manual",
            wb_placement_search=True,
            wb_placement_recommendations=False,
        ),
        adv_setting=SimpleNamespace(
            nmids=[11],
            wb_bid_type="unified",
            wb_placement_search=True,
            wb_placement_recommendations=True,
        ),
        get_keywords=_get_keywords,
    )

    ok_result = SimpleNamespace(
        dropped_invalid_phrases=[],
        applied_phrases=["bad"],
        skipped_unsupported_campaign=False,
    )

    async def _maybe_fail(**kwargs: object) -> SimpleNamespace:
        if kwargs.get("adv_id") == 777:
            raise RuntimeError("auto-nmid-failed")
        return ok_result

    wb_modifier = SimpleNamespace(
        get_minus_phrases_for_adv=AsyncMock(return_value=[]),
        set_minus_phrases_with_fallback_for_adv=AsyncMock(side_effect=_maybe_fail),
    )
    manager = MinusPhraseManager(
        wb_api_manager_hub=SimpleNamespace(wb_modifier=wb_modifier),
        click_house_manager=SimpleNamespace(
            get_cluster_texts_for_adv_nmid=AsyncMock(return_value=["bad"])
        ),
        update_redis_timestamp_manager=_make_state_manager(),
    )

    await manager.update_minus_phrases(complex_adv)

    assert wb_modifier.set_minus_phrases_with_fallback_for_adv.await_count == 2
    search_calls = [
        c.kwargs["adv_id"]
        for c in wb_modifier.set_minus_phrases_with_fallback_for_adv.await_args_list
    ]
    assert 888 in search_calls
