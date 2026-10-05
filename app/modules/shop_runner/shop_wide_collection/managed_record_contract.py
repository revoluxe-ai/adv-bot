"""Контракт managed RECORD path: universe через loader §B.1.

Spec: ``connected-shop-campaign-ad-data-collection`` (design §A, §B.1).
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Задачи 5.1–5.3. Legacy ``CoroutinesManager`` RECORD-корутины не расширяют
universe за пределы ``get_complex_advs(only_bot_active=False)`` с post-filter
непустых ``nmids``. Collection ownership задаёт resolver/loader, не ``bot_active``.
Модуль — read-only контракт для tick/tests; side effects не выполняет.
"""

from __future__ import annotations

# Имена managed RECORD coroutines, которые ``WBShop.run`` ставит с ``only_bot_active=False``.
MANAGED_RECORD_COROUTINE_NAMES: tuple[str, ...] = (
    "update_full_adv_stat",
    "update_clusters_adv_stats_today",
    "update_clusters_adv_stats_history",
)

# Unmanaged shop-wide tick в ``WBShop.run`` при ``DUAL_PATH_ACTIVE`` (задача 8.1).
SHOP_WIDE_UNMANAGED_COROUTINE_NAME = "collect_shop_wide_campaign_advertising"


def managed_complex_advs_loader_kwargs() -> dict[str, bool]:
    """Kwargs ``get_complex_advs`` для managed RECORD collectors.

    Returns:
        ``only_bot_active=False`` включает ``refused`` (§B.1); ``load_extras=False``
        — только nmids без enrich, как в production RECORD path.
    """
    return {"only_bot_active": False, "load_extras": False}
