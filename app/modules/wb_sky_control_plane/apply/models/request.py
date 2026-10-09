"""ApplyRequestV1 — недоверенный client intent."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.modules.wb_sky_control_plane.apply.models.binding import ApplyBindingHintsV1
from app.modules.wb_sky_control_plane.models.changeset import ChangeSetV1

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class ApplyRequestV1(BaseModel):
    """Семантический intent apply: ChangeSet + ссылка на dry-run receipt.

    Не содержит authoritative principal/shop auth — только server context.
    """

    model_config = _FROZEN

    contract_version: str
    idempotency_key: str
    changeset: ChangeSetV1
    dry_run_receipt_id: str
    binding_hints: ApplyBindingHintsV1 | None = None

    def scope_shop_id(self) -> str:
        """Shop id из changeset scope (для idempotency key)."""
        return self.changeset.scope.shop_id
