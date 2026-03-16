"""Resolve current CPM bids from cascade: Redis set_bid → WB API → bid_decision_log → stats. Returns dict[str, int]."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv


class _AdvForTimestamp:
    """Minimal adapter for get_set_bid_map timestamp lookup (AdvProtocol)."""

    def __init__(self, adv_id: int) -> None:
        self._adv_id = adv_id

    @property
    def adv_id(self) -> int:
        return self._adv_id


class CpmSourcesResolver:
    """Resolves current bid (CPM) per norm_query from cache, WB API, and ClickHouse sources."""

    async def get_current_bids(
        self,
        complex_adv: ComplexAdv,
        texts: list[str],
        stats_cpm_by_text: dict[str, float] | None = None,
    ) -> dict[str, int]:
        """
        Resolve current bid per text from cascade: set_bid (Redis) → WB API → bid_log (bid_decision_log) → stats.
        Returns only keys for which a value was resolved; caller may fall back to cluster_stat.cpm for the rest.
        """
        if not texts:
            return {}
        api_bids: dict[str, int] = {}
        try:
            from app.core.di.wb_manager_hub import WBManagerHubFactory

            hub = WBManagerHubFactory.get_wb_manager_from_context()
            wb_data_manager = hub.wb_data_manager
            bids = await wb_data_manager.get_current_bids_for_advs([complex_adv])
            if bids:
                for dto in bids:
                    q = dto.norm_query
                    b = dto.bid
                    if q not in api_bids:
                        api_bids[q] = b
                    else:
                        api_bids[q] = max(api_bids[q], b)
        except Exception:  # noqa: BLE001
            api_bids = {}
        search_adv_id = getattr(complex_adv, "search_adv_id", None)
        nmids = complex_adv.nmids
        set_bid_map: dict[str, tuple[float, object]] = {}
        bid_log_map: dict[str, tuple[float, object]] = {}
        if search_adv_id is not None and nmids:
            from app.modules.keyword_bid_from_log import get_latest_keyword_bids
            from app.modules.cluster_bids_redis import get_redis_client, get_set_bid_map

            bid_log_map = cast(
                dict[str, tuple[float, object]],
                await get_latest_keyword_bids(search_adv_id, nmids, texts),
            )
            try:
                redis_client = get_redis_client()
                adv_for_ts = _AdvForTimestamp(search_adv_id)
                set_bid_map = cast(
                    dict[str, tuple[float, object]],
                    await get_set_bid_map(
                        search_adv_id, nmids, texts, adv_for_ts, redis_client
                    ),
                )
            except Exception:  # noqa: BLE001
                set_bid_map = {}
        stats = stats_cpm_by_text or {}
        result: dict[str, int] = {}
        for text in texts:
            val = None
            if text in set_bid_map:
                val = set_bid_map[text][0]
            elif text in api_bids:
                val = float(api_bids[text])
            elif text in bid_log_map:
                val = bid_log_map[text][0]
            elif text in stats:
                val = stats[text]
            if val is not None:
                result[text] = int(round(val))
        return result
