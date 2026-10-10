"""Порты read-only runtime. Транспорт подставляется провайдерами."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence

from app.modules.attribution_facts.domain.models import (
    AttributionQueryResult,
    AttributionScope,
    DateWindow,
)


class SupplierOrdersPagePort(Protocol):
    """Одна страница ``ReportsManager.get_supplier_orders`` (flag=0)."""

    async def get_supplier_orders(
        self,
        *,
        date_from: str,
        flag: int = 0,
    ) -> Sequence[object]:
        """Вернуть сырые строки statistics-api. Пустой список — естественный хвост."""
        ...


class ShopAdvIdPort(Protocol):
    """Список physical adv id. ``None`` — чтение не удалось."""

    async def list_adv_ids(self, shop_id: str) -> tuple[int, ...] | None:
        """Успешный пустой набор — ``()``, ошибка чтения — ``None``."""
        ...


class ShopSpendPort(Protocol):
    """Сумма ``full_adv_wb_stat.spend`` по adv id и окну. ``None`` — сбой чтения."""

    async def sum_spend_by_adv(
        self,
        adv_ids: tuple[int, ...],
        window: DateWindow,
    ) -> dict[int, Decimal] | None:
        """Ключи — adv id, по которым в окне есть строки. Нет строки = ноль у вызывающего."""
        ...


class AttributionQueryPort(Protocol):
    """Узкий фасад ``AttributionFactsReader.query``."""

    async def query(
        self,
        scope: AttributionScope,
        window: DateWindow,
    ) -> AttributionQueryResult:
        """DIRECT/LINKED facts за окно. Supplier-order строки сюда не входят."""
        ...


class ResolverContextSource(Protocol):
    """Уже собранные контексты резолвера (persistence снаружи)."""

    async def load_contexts(
        self,
        shop_id: str,
        advert_ids: tuple[int, ...],
    ) -> tuple[object, ...]:
        """Вернуть ``ResolverContext`` на каждую кампанию. Пустой набор допустим."""
        ...


def window_date_bounds(window: DateWindow) -> tuple[date, date]:
    """Включительные границы окна."""
    return window.start, window.end
