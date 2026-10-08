"""ApplyInvocationContext — server-built trusted boundary."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.wb_sky_control_plane.apply.enums import TransportChannel

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class PrincipalRefV1(BaseModel):
    """Opaque principal identity (не из client JSON)."""

    model_config = _FROZEN

    kind: Literal["wb_user", "service_account", "internal"]
    principal_id: str


class ShopAuthorizationV1(BaseModel):
    """Результат server policy: principal может действовать в shop."""

    model_config = _FROZEN

    shop_id: str
    authorized: bool
    reason_code: str = "OK"


class PermissionGrantsV1(BaseModel):
    """Server-resolved mutation permissions (отдельно от domain capability)."""

    model_config = _FROZEN

    apply_campaign_settings: bool = False


class ApplyInvocationContext(BaseModel):
    """Trusted adapter context для ApplyAuthorityService.apply."""

    model_config = _FROZEN

    principal_ref: PrincipalRefV1
    shop_authorization: ShopAuthorizationV1
    permission_grants: PermissionGrantsV1
    transport_channel: TransportChannel
    auth_proof_ref: str = Field(
        ...,
        description="Opaque internal session/token handle; never client-supplied proof bytes",
    )

    def is_authorized_for_shop(self, shop_id: str) -> bool:
        """Principal authorized для shop и apply grant."""
        return (
            self.shop_authorization.shop_id == shop_id
            and self.shop_authorization.authorized
            and self.permission_grants.apply_campaign_settings
        )
