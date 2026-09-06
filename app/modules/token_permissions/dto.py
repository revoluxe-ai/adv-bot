"""Data Transfer Objects for token permissions validation."""

from __future__ import annotations
from dataclasses import dataclass
import datetime


@dataclass
class PermissionStatus:
    """Status of a single permission."""

    name: str
    has_jwt_claim: bool
    api_probe_success: bool | None

    @property
    def is_available(self) -> bool:
        """Check if permission is available.

        Logic:
        - If no API probe was performed (api_probe_success is None), rely on JWT claim.
        - If API probe succeeded (True), permission is confirmed available.
        - If API probe failed with 403 (False), permission is definitely unavailable.
        - For network/transient errors, _probe_api returns None, so we fall back to JWT claim.
        """
        if self.api_probe_success is None:
            # No probe performed, or probe had network error → trust JWT claim
            return self.has_jwt_claim
        # Probe was performed and returned definitive result (True or False)
        return self.has_jwt_claim and self.api_probe_success


@dataclass
class ValidationResult:
    """Result of token validation."""

    is_valid_jwt: bool
    shop_id: str | None
    is_personal: bool
    is_read_only: bool
    is_expired: bool
    expires: datetime.datetime | None
    permissions: dict[str, PermissionStatus]

    @property
    def missing_required(self) -> set[str]:
        """Get set of missing required permissions."""
        from .validator import TokenPermissionsValidator

        required = TokenPermissionsValidator.REQUIRED_RIGHTS
        available = {name for name, perm in self.permissions.items() if perm.is_available}
        return required - available

    @property
    def can_be_used_for_free(self) -> bool:
        """Check if token can be used for free analytics/read-only flows."""
        return (
            self.is_valid_jwt
            and self.is_personal
            and not self.is_expired
            and len(self.missing_required) == 0
        )

    @property
    def can_be_used_for_pay(self) -> bool:
        """Check if token can be used for paid management flows."""
        return (
            self.can_be_used_for_free
            and not self.is_read_only
            and len(self.missing_required) == 0
        )


    @property
    def error_message(self) -> str | None:
        """Get human-readable error message if token cannot be used."""
        if not self.is_valid_jwt:
            return "Токен не валиден"
        if not self.is_personal:
            return "Токен не персональный"
        if self.is_read_only:
            return "Токен только для чтения"
        if self.is_expired:
            return "Токен истёк"
        if self.missing_required:
            missing = ", ".join(sorted(self.missing_required))
            return f"Отсутствуют права: {missing}"
        return None
