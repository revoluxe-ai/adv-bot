"""White-list mode constants for FREE/PAID default overlays."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode

FREE_SAFE_WHITE_LIST_MODES = frozenset(
    {
        WhiteListMode.ABOVE_MIN_RATING,
        WhiteListMode.ACTIVE_ONLY_WHITE_LIST,
    }
)
