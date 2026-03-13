"""Data Transfer Objects for token permissions validation."""

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
        """Check if permission is available."""
        if self.api_probe_success is None:
            return self.has_jwt_claim
        return self.has_jwt_claim and self.api_probe_success


@dataclass
class ValidationResult:
    """Result of token validation."""

    is_valid_jwt: bool
    shop_id: str | None
    is_read_only: bool
    is_expired: bool
    expires: datetime.datetime | None
    permissions: dict[str, PermissionStatus]

    @property
    def missing_required(self) -> set[str]:
        """Get set of missing required permissions."""
        required = {"Контент", "Статистика", "Аналитика", "Продвижение"}
        available = {name for name, perm in self.permissions.items() if perm.is_available}
        return required - available

    @property
    def can_be_used(self) -> bool:
        """Check if token can be used (valid, not read-only, not expired, has all required permissions)."""
        return (
            self.is_valid_jwt
            and not self.is_read_only
            and not self.is_expired
            and len(self.missing_required) == 0
        )

    @property
    def error_message(self) -> str | None:
        """Get human-readable error message if token cannot be used."""
        if not self.is_valid_jwt:
            return "Токен не валиден"
        if self.is_read_only:
            return "Токен только для чтения"
        if self.is_expired:
            return "Токен истёк"
        if self.missing_required:
            missing = ", ".join(sorted(self.missing_required))
            return f"Отсутствуют права: {missing}"
        return None
