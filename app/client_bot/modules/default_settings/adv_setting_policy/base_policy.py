"""Base class for declarative ``AdvSetting`` policies."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

from .field_policy import FieldPolicy


class AdvSettingDefaultsPolicy:
    """Base class for declarative ``AdvSetting`` policies."""

    name: str
    rules: tuple[FieldPolicy, ...] = ()

    @classmethod
    def apply(cls, adv_setting: AdvSetting, wb_cabinet: WBCabinet) -> None:
        """Apply all rules to the provided campaign settings row."""
        cls.validate_rules()

        for policy in cls.rules:
            policy.apply(adv_setting, wb_cabinet)

    @classmethod
    def field_names(cls) -> set[str]:
        """Return the set of field names touched by this policy."""
        return {rule.field_name for rule in cls.rules}

    @classmethod
    def validate_rules(cls) -> None:
        """Ensure the policy has no duplicate fields and all reasons are set."""
        seen: set[str] = set()
        duplicates: set[str] = set()

        for rule in cls.rules:
            if rule.field_name in seen:
                duplicates.add(rule.field_name)
            seen.add(rule.field_name)

            if not rule.reason:
                raise RuntimeError(
                    f"Default policy {cls.name} field {rule.field_name} "
                    "has empty reason"
                )

        if duplicates:
            raise RuntimeError(
                f"Default policy {cls.name} has duplicate fields: "
                f"{sorted(duplicates)}"
            )
