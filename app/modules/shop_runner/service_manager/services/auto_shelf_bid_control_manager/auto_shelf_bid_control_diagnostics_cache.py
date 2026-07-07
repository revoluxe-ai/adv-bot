"""Redis cache manager for Auto Shelf diagnostics shown in Telegram UI."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager

from .dto.selected_cpo_contract import AutoShelfBidSelectedCpoContract

AUTO_SHELF_DIAGNOSTICS_CACHE_TTL_SEC = int(timedelta(minutes=5).total_seconds())


class AutoShelfBidDiagnosticsDTO(BaseModel):
    """Минимальный снимок Auto Shelf для UI-диагностики."""

    bid_rub: float | None = Field(default=None, description="Ставка Auto Shelf в рублях")
    cpo_rub: float | None = Field(default=None, description="CPO в рублях")
    updated_at: datetime | None = Field(
        default=None,
        description="Время последнего обновления",
    )
    source: str = Field(default="unknown", description="Источник данных")

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_selected_cpo_contract(
        cls,
        contract: AutoShelfBidSelectedCpoContract,
    ) -> "AutoShelfBidDiagnosticsDTO":
        """Собрать DTO из selected CPO contract."""
        return cls(
            bid_rub=(
                float(contract.selected_bid_minor) / 100.0
                if contract.selected_bid_minor is not None
                else None
            ),
            cpo_rub=contract.selected_cpo_rub,
            updated_at=contract.updated_at,
            source=contract.source,
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
        contract: AutoShelfBidSelectedCpoContract,
        *,
        ttl: int | None = None,
    ) -> None:
        """Сохранить selected CPO contract как UI-диагностику."""
        await self.set(
            adv_setting_id,
            AutoShelfBidDiagnosticsDTO.from_selected_cpo_contract(contract),
            ttl=ttl,
        )


__all__ = [
    "AUTO_SHELF_DIAGNOSTICS_CACHE_TTL_SEC",
    "AutoShelfBidDiagnosticsCacheManager",
    "AutoShelfBidDiagnosticsDTO",
]

