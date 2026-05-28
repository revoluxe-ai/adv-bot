"""Проверки порядка целевых позиций V3 (M / O / C) через ``build_mode_candidates``."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
    target_place_for_v3_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    profile_points_from_bid_positions,
    resolve_keyword_bid_profile,
)


def target_places_for_v3_modes(
    profile: list[BidPosition],
    *,
    conv_views_to_orders: float = 0.01,
) -> dict[KeywordStrategyMode, int | None]:
    """Целевые позиции M/O/C на одном профиле (лестница V3, не legacy-предиктор)."""
    points = profile_points_from_bid_positions(profile)
    candidates = build_mode_candidates(
        profile=points,
        keyword_text="",
        conv_views_to_orders=conv_views_to_orders,
    )
    return {
        mode: target_place_for_v3_strategy_mode(mode, candidates)
        for mode in (
            KeywordStrategyMode.MIN_CPA,
            KeywordStrategyMode.OPTIMUM,
            KeywordStrategyMode.MAX_CONVERSION,
        )
    }


def assert_ladder_positions_distinct_and_ordered(
    pos_min: int,
    pos_opt: int,
    pos_max: int,
    *,
    keyword: str = "",
) -> None:
    """На WB меньший номер позиции = лучше: MAX лучше OPT, OPT лучше MIN.

    Args:
        pos_min: цель для MIN_CPA (обычно глубже в выдаче).
        pos_opt: цель для OPTIMUM.
        pos_max: цель для MAX_CONVERSION (обычно выше в выдаче).
        keyword: подпись для сообщения об ошибке.
    """
    prefix = f"keyword={keyword!r}: " if keyword else ""
    assert pos_max is not None and pos_opt is not None and pos_min is not None, (
        f"{prefix}все три режима должны вернуть позицию"
    )
    assert pos_max <= pos_opt <= pos_min, (
        f"{prefix}ожидается pos_MAX <= pos_OPT <= pos_MIN, "
        f"получено MAX={pos_max}, OPT={pos_opt}, MIN={pos_min}"
    )
    assert len({pos_min, pos_opt, pos_max}) == 3, (
        f"{prefix}позиции M/O/C должны различаться, "
        f"получено MIN={pos_min}, OPT={pos_opt}, MAX={pos_max}"
    )


def assert_profile_resolves_like_orchestrator(
    profiles: dict[str, list[BidPosition]],
    keyword_text: str,
) -> list[BidPosition]:
    """Профиль найден тем же резолвером, что orchestrator и sync_keyword_target_places_v3."""
    resolved = resolve_keyword_bid_profile(profiles, keyword_text)
    assert resolved is not None, (
        f"профиль не найден для {keyword_text!r}, keys={list(profiles.keys())[:5]}"
    )
    return resolved
