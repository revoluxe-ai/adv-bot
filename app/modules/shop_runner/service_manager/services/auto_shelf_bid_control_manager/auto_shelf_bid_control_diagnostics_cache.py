"""Redis cache manager for Auto Shelf diagnostics shown in Telegram UI."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager

from .dto.control_view_dto import AutoShelfBidControlViewDTO
from .dto.selected_cpo_contract import AutoShelfBidSelectedCpoContract

AUTO_SHELF_DIAGNOSTICS_CACHE_TTL_SEC = int(timedelta(minutes=5).total_seconds())


class AutoShelfBidDiagnosticsDTO(BaseModel):
    """Минимальный снимок Auto Shelf для UI-диагностики."""

    best_cpo_bid_rub: float | None = Field(
        default=None,
        description="Лучшая/рекомендованная ставка по CPO в рублях",
    )
    current_bid_rub: float | None = Field(
        default=None,
        description="Текущая ставка WB в рублях",
    )
    expected_bid_rub: float | None = Field(
        default=None,
        description="Целевая ставка бота в рублях",
    )
    selected_cpo_rub: float | None = Field(
        default=None,
        description="Выбранный CPO в рублях, если контракт доступен",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Время последнего обновления",
    )
    source: str = Field(default="unknown", description="Источник данных")
    unavailable_reason: str | None = Field(
        default=None,
        description="Почему выбранный CPO-контракт неполный",
    )

    model_config = ConfigDict(extra="forbid")

    @property
    def bid_rub(self) -> float | None:
        """Backward-compatible alias for the best recommended CPO bid."""
        return self.best_cpo_bid_rub

    @property
    def cpo_rub(self) -> float | None:
        """Backward-compatible alias for the selected CPO value."""
        return self.selected_cpo_rub

    @classmethod
    def from_selected_cpo_contract(
        cls,
        view: AutoShelfBidControlViewDTO,
        contract: AutoShelfBidSelectedCpoContract,
    ) -> "AutoShelfBidDiagnosticsDTO":
        """Собрать DTO из view/selected CPO contract без потери семантики."""

        def _bid_minor_to_rub(value: int | None) -> float | None:
            if value is None:
                return None
            return float(value) / 100.0

        return cls(
            best_cpo_bid_rub=_bid_minor_to_rub(contract.selected_bid_minor),
            current_bid_rub=_bid_minor_to_rub(view.actual_bid_minor),
            expected_bid_rub=_bid_minor_to_rub(view.expected_enforced_bid_minor),
            selected_cpo_rub=contract.selected_cpo_rub,
            updated_at=contract.updated_at,
            source=contract.source,
            unavailable_reason=contract.unavailable_reason,
        )


class AutoShelfBidDiagnosticsCacheManager(BaseRedisManager):
    """Redis-менеджер для мини-диагностики Auto Shelf."""

    prefix = "auto_shelf:diagnostics"
    default_ttl = AUTO_SHELF_DIAGNOSTICS_CACHE_TTL_SEC

    def _get_key(self, adv_setting_id: int) -> str:
        """Сформировать ключ Redis для `adv_setting_id`."""
        return f"{self.prefix}:{int(adv_setting_id)}"

    async def set(
        self,
        adv_setting_id: int,
        value: AutoShelfBidDiagnosticsDTO,
        *,
        ttl: int | None = None,
    ) -> None:
        """Сохранить DTO в Redis с TTL по умолчанию 5 минут."""
        key = self._get_key(adv_setting_id)
        effective_ttl = self._resolve_ttl(ttl)
        payload = value.model_dump_json()
        if effective_ttl is None:
            await self._client.set(key, payload)
        else:
            await self._client.set(key, payload, ex=effective_ttl)

    async def get(self, adv_setting_id: int) -> AutoShelfBidDiagnosticsDTO | None:
        """Загрузить DTO из Redis; при отсутствии или ошибке вернуть None."""
        key = self._get_key(adv_setting_id)
        raw = await self._client.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            return AutoShelfBidDiagnosticsDTO.model_validate_json(raw)
        except ValidationError:
            return None

    async def set_selected_cpo_contract(
        self,
        adv_setting_id: int,
        view: AutoShelfBidControlViewDTO,
        contract: AutoShelfBidSelectedCpoContract,
        *,
        ttl: int | None = None,
    ) -> None:
        """Сохранить selected CPO contract как UI-диагностику."""
        await self.set(
            adv_setting_id,
            AutoShelfBidDiagnosticsDTO.from_selected_cpo_contract(view, contract),
            ttl=ttl,
        )


__all__ = [
    "AUTO_SHELF_DIAGNOSTICS_CACHE_TTL_SEC",
    "AutoShelfBidDiagnosticsCacheManager",
    "AutoShelfBidDiagnosticsDTO",
]

