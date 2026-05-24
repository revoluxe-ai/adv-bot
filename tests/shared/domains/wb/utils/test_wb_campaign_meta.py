"""Unit-тесты хелперов wb_campaign_meta."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.domains.wb.utils.wb_campaign_meta import (
    apply_wb_campaign_meta_from_legacy_adv_data,
    wb_campaign_meta_known,
    wb_is_manual_shelf_only,
    wb_supports_normquery_minus_phrases,
)


def _adv_setting(**kwargs: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "wb_bid_type": None,
        "wb_placement_search": None,
        "wb_placement_recommendations": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.unit
def test_apply_wb_campaign_meta_from_legacy_adv_data() -> None:
    adv_setting = _adv_setting()
    apply_wb_campaign_meta_from_legacy_adv_data(
        adv_setting,  # type: ignore[arg-type]
        {
            "bidType": "manual",
            "autoParams": {"active": {"search": False, "recom": True}},
        },
    )
    assert adv_setting.wb_bid_type == "manual"
    assert adv_setting.wb_placement_search is False
    assert adv_setting.wb_placement_recommendations is True


@pytest.mark.unit
@pytest.mark.parametrize(
    ("bid_type", "search", "recommendations", "known", "shelf_only", "supports_normquery"),
    [
        (None, None, None, False, False, False),
        ("unified", True, True, True, False, False),
        ("manual", True, False, True, False, True),
        ("manual", False, True, True, True, False),
        ("manual", False, False, True, False, False),
    ],
)
def test_wb_campaign_meta_matrix(
    bid_type: str | None,
    search: bool | None,
    recommendations: bool | None,
    known: bool,
    shelf_only: bool,
    supports_normquery: bool,
) -> None:
    adv = _adv_setting(
        wb_bid_type=bid_type,
        wb_placement_search=search,
        wb_placement_recommendations=recommendations,
    )
    assert wb_campaign_meta_known(adv) is known  # type: ignore[arg-type]
    assert wb_is_manual_shelf_only(adv) is shelf_only  # type: ignore[arg-type]
    assert wb_supports_normquery_minus_phrases(adv) is supports_normquery  # type: ignore[arg-type]
