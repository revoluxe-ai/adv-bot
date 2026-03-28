from types import SimpleNamespace

from app.modules.shop_runner.service_manager.services.white_list_trimmer import (
    WhiteListTrimmer,
)


def _kw(
    *,
    kid: int,
    hard_status: int,
    above_rec_conversion: bool | None = True,
    relevant: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        keyword_setting_original_id=kid,
        hard_status=hard_status,
        above_rec_conversion=above_rec_conversion,
        relevant=relevant,
    )


def test_replacement_skips_below_rec_when_shelf_activation_allowed() -> None:
    """Align with KeywordsManager: block полочные keys only when shelf traffic dominates."""
    complex_adv = SimpleNamespace(
        auto_add_only_relevant_phrase=False,
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=True,
        is_shelf_activation_allowed=True,
    )
    # One WL row remains above trim window; below_rec candidate sits after start_index.
    keywords = [
        _kw(kid=1, hard_status=2),
        _kw(kid=200, hard_status=1, above_rec_conversion=False),
    ]
    result = WhiteListTrimmer._collect_replacement_candidates(
        complex_adv=complex_adv,
        keywords=keywords,
        removed_ids={999},
        removed_count=1,
    )
    assert result == []


def test_replacement_allows_below_rec_when_organic_dominates() -> None:
    complex_adv = SimpleNamespace(
        auto_add_only_relevant_phrase=False,
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=True,
        is_shelf_activation_allowed=False,
    )
    keywords = [
        _kw(kid=1, hard_status=2),
        _kw(kid=200, hard_status=1, above_rec_conversion=False),
    ]
    result = WhiteListTrimmer._collect_replacement_candidates(
        complex_adv=complex_adv,
        keywords=keywords,
        removed_ids={999},
        removed_count=1,
    )
    assert result == [200]
