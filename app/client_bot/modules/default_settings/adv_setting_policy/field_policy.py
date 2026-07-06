"""Single-field policy declarations for ``AdvSetting`` defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

DefaultPredicate = Callable[[AdvSetting, WBCabinet], bool]
DefaultValueFactory = Callable[[AdvSetting, WBCabinet], Any]


@dataclass(frozen=True)
class FieldPolicy:
    """Single declarative rule for one ``AdvSetting`` ORM field."""

    field: InstrumentedAttribute
    apply_if: DefaultPredicate
    value: DefaultValueFactory
    reason: str

    @property
    def field_name(self) -> str:
        """Return the mapped SQLAlchemy field name."""
        return self.field.key

    def apply(self, adv_setting: AdvSetting, wb_cabinet: WBCabinet) -> None:
        """Apply the policy to the given ``AdvSetting`` if its predicate matches."""
        if not self.apply_if(adv_setting, wb_cabinet):
            return

        setattr(
            adv_setting,
            self.field_name,
            self.value(adv_setting, wb_cabinet),
        )
