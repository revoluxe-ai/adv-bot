"""Совместимый импорт синтетики из ``tests.rec_system_bid_math``."""

from tests.rec_system_bid_math.synthetic_cases import (
    SyntheticTruth,
    format_rankings,
    make_bad_neighbors_good_night_spike_obs,
    make_local_peak_bad_daily_obs,
    make_one_night_hour_candidate_obs,
    make_sparse_confirmed_best_obs,
    print_rankings,
    synthetic_hour_profile,
)

__all__ = [
    "SyntheticTruth",
    "format_rankings",
    "make_bad_neighbors_good_night_spike_obs",
    "make_local_peak_bad_daily_obs",
    "make_one_night_hour_candidate_obs",
    "make_sparse_confirmed_best_obs",
    "print_rankings",
    "synthetic_hour_profile",
]
