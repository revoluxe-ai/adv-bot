"""Redis cache derived promo state. Не source of truth: live WB + PG journals."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Mapping, cast

from app.core.redis_manager_v2.redis_client import RedisClient

_PREFIX = "shop-promo-state"
_TTL = int(timedelta(hours=48).total_seconds())
_STALE_AFTER = timedelta(minutes=15)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return default
    return int(text)


def _as_decimal(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def _parse_updated_at(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class CachedCampaignPromoState:
    """Derived per-campaign overlay inputs."""

    remaining: int
    fraction: Decimal
    expires_at: str | None
    usable: bool
    effective_fraction: Decimal
    pool_usable: bool
    campaign_usable: bool


@dataclass(frozen=True, slots=True)
class CachedShopPromoState:
    """Shop-level derived promo overlay.

    ``overlay_trusted`` is false when refresh could not verify one of the
    live inputs used to derive the snapshot. Such a snapshot may preserve
    ingest watermarks, but readers must not apply its overlay.
    """

    updated_at: datetime | None
    topup_amount: int
    pool_usable: bool
    pool_amount: int
    pool_fraction: Decimal
    campaigns: dict[int, CachedCampaignPromoState]
    # Последний момент успешного ingest UPD; не влияет на freshness overlay.
    upd_ingested_at: datetime | None = None
    # Нижняя граница исторического UPD-backfill, подтверждённая этим snapshot.
    upd_coverage_from: datetime | None = None
    # Старый snapshot после ошибки refresh нельзя использовать как доверенный.
    overlay_trusted: bool = True

    @property
    def is_stale(self) -> bool:
        """True если cache отсутствует по времени или старше freshness window."""
        if self.updated_at is None:
            return True
        return (_now_utc() - self.updated_at) > _STALE_AFTER


class RedisPromoStateManager:
    """Stores derived promo availability for runtime overlay."""

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis_client = redis_client

    @staticmethod
    def _key(shop_id: str | int) -> str:
        return f"{_PREFIX}:{shop_id}"

    async def set(
        self,
        shop_id: str | int,
        *,
        topup_amount: int,
        pool_usable: bool,
        pool_amount: int,
        pool_fraction: Decimal,
        campaigns: Mapping[int, CachedCampaignPromoState],
        upd_ingested_at: datetime | None = None,
        upd_coverage_from: datetime | None = None,
        overlay_trusted: bool = True,
    ) -> None:
        """Записать derived state и границы покрытия UPD.

        ``upd_ingested_at`` позволяет следующему refresh запросить только
        инкрементальную часть UPD, не заменяя live WB balance как источник
        common-pool. ``upd_coverage_from`` доказывает, что исторический
        backfill начинался не позже этой даты; без него старый Redis snapshot
        повторно проходит recovery. ``overlay_trusted=False`` сохраняет эти
        cursors, но запрещает readers применять derived overlay после ошибки
        refresh.
        """
        payload: dict[str, Any] = {
            "updated_at": _now_utc().isoformat(),
            "upd_ingested_at": (
                upd_ingested_at.astimezone(timezone.utc).isoformat()
                if upd_ingested_at is not None
                else None
            ),
            "upd_coverage_from": (
                upd_coverage_from.astimezone(timezone.utc).isoformat()
                if upd_coverage_from is not None
                else None
            ),
            "topup_amount": int(topup_amount),
            "pool_usable": bool(pool_usable),
            "pool_amount": int(pool_amount),
            "pool_fraction": str(pool_fraction),
            "overlay_trusted": bool(overlay_trusted),
            "campaigns": {
                str(adv_id): {
                    "remaining": state.remaining,
                    "fraction": str(state.fraction),
                    "expires_at": state.expires_at,
                    "usable": state.usable,
                    "effective_fraction": str(state.effective_fraction),
                    "pool_usable": state.pool_usable,
                    "campaign_usable": state.campaign_usable,
                }
                for adv_id, state in campaigns.items()
            },
        }
        _ = await self._redis_client.set(
            self._key(shop_id), json.dumps(payload), ex=_TTL
        )

    async def get(self, shop_id: str | int) -> CachedShopPromoState | None:
        """Прочитать derived state. None при miss/invalid."""
        raw = await self._redis_client.get(self._key(shop_id))
        if not raw:
            return None
        try:
            loaded: object = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
        if not isinstance(loaded, dict):
            return None
        data = cast(dict[str, object], loaded)
        campaigns_raw: object = data.get("campaigns") or {}
        campaigns: dict[int, CachedCampaignPromoState] = {}
        if isinstance(campaigns_raw, dict):
            campaigns_map = cast(dict[str, object], campaigns_raw)
            for key, value in campaigns_map.items():
                if not isinstance(value, dict):
                    continue
                campaign_map = cast(dict[str, object], value)
                try:
                    adv_id = int(key)
                    expires_raw = campaign_map.get("expires_at")
                    campaigns[adv_id] = CachedCampaignPromoState(
                        remaining=_as_int(campaign_map.get("remaining"), 0),
                        fraction=_as_decimal(campaign_map.get("fraction")),
                        expires_at=str(expires_raw) if expires_raw else None,
                        usable=bool(campaign_map.get("usable")),
                        effective_fraction=_as_decimal(
                            campaign_map.get("effective_fraction")
                        ),
                        pool_usable=bool(campaign_map.get("pool_usable")),
                        campaign_usable=bool(campaign_map.get("campaign_usable")),
                    )
                except (TypeError, ValueError):
                    continue
        try:
            return CachedShopPromoState(
                updated_at=_parse_updated_at(data.get("updated_at")),
                topup_amount=_as_int(data.get("topup_amount"), 0),
                pool_usable=bool(data.get("pool_usable")),
                pool_amount=_as_int(data.get("pool_amount"), 0),
                pool_fraction=_as_decimal(data.get("pool_fraction")),
                campaigns=campaigns,
                upd_ingested_at=_parse_updated_at(data.get("upd_ingested_at")),
                upd_coverage_from=_parse_updated_at(
                    data.get("upd_coverage_from")
                ),
                # Legacy payloads predate the trust marker and remain trusted.
                overlay_trusted=bool(data.get("overlay_trusted", True)),
            )
        except (TypeError, ValueError):
            return None
