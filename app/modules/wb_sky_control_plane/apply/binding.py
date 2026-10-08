"""Binding hint comparison (non-authoritative client hints)."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.apply.enums import ApplyReasonCode
from app.modules.wb_sky_control_plane.apply.models.binding import ApplyBindingHintsV1


def binding_hint_mismatches(
    hints: ApplyBindingHintsV1 | None,
    *,
    semantic_digest: str,
    preview_digest: str,
) -> ApplyReasonCode | None:
    """Return mismatch reason if client hint disagrees with server recompute."""
    if hints is None:
        return None
    if hints.semantic_digest is not None and hints.semantic_digest != semantic_digest:
        return ApplyReasonCode.CHANGESET_DIGEST_MISMATCH
    if hints.preview_digest is not None and hints.preview_digest != preview_digest:
        return ApplyReasonCode.PREVIEW_DIGEST_MISMATCH
    return None
