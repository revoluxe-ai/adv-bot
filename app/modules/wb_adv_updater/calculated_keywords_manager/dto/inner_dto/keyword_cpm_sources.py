"""DTO for CPM sources (set bid, API, bid_decision_log, stats) with resolved_cpm()."""

from datetime import datetime

from pydantic import BaseModel


class KeywordCpmSources(BaseModel):
    """Holds CPM from Redis (set bid), WB API, bid_decision_log, and get_clusters_stats."""

    cpm_set_bid: int | None = None
    cpm_set_bid_date: datetime | None = None
    cpm_from_api: int | None = None
    cpm_from_bid_log: float | None = None
    cpm_from_bid_log_date: datetime | None = None
    cpm_from_stats: float | None = None
    cpm_from_stats_date: datetime | None = None

    def resolved_cpm(self) -> float | None:
        """First non-None by priority: set_bid → api → from_bid_log → from_stats."""
        if self.cpm_set_bid is not None:
            return float(self.cpm_set_bid)
        if self.cpm_from_api is not None:
            return float(self.cpm_from_api)
        if self.cpm_from_bid_log is not None:
            return self.cpm_from_bid_log
        if self.cpm_from_stats is not None:
            return self.cpm_from_stats
        return None
