"""Pure apply request validation helpers (Slice A)."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.enums import ApplyReasonCode
from app.modules.wb_sky_control_plane.apply.models.request import ApplyRequestV1


def unsupported_contract_version(request: ApplyRequestV1) -> ApplyReasonCode | None:
    """Fail closed on unknown apply contract version (S20)."""
    if request.contract_version != APPLY_CONTRACT_VERSION:
        return ApplyReasonCode.VALIDATION_REJECTED
    return None
