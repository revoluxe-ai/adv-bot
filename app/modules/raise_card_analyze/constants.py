"""Constants for raise card analyze module (release 1, no "or" variants)."""

# Clipping
POS_CAP = 2000
BID_CAP = 1_000_000

# Tail mode
TAIL_MODE_THRESHOLD = 0.30  # tail_share > 0.3 or median_pos > POS_CAP*0.7 on last period
TAIL_TREND_THRESHOLD = 0.15  # ±15% verdict threshold when tail_mode

# Spread (by rows)
SPREAD_MIN_ROWS = 200  # if rows_recent < 200 → spread_used_recent=None

# Weak reasons: wrong_sign and flat_k only when rows_used >= these
MIN_ROWS_FOR_SIGN = 200
MIN_ROWS_FOR_K = 200

# Corr (aggregates by (norm_query, day))
CORR_MIN_SUM_D = 10  # min sum(d_views) per point (key, day)
CORR_MIN_POINTS = 200  # corr only if number of points >= 200

# Quality gate
SUM_D_WEEK_FAIL = 100  # fail if sum_d_week < 100
ROWS_WEEK_WARN = 30  # warn if rows_week < 30 (when sum_d >= 100)

# Resolve k thresholds
K_MIN_ABS = 0.05  # flat_k if abs(k) < this
SPREAD_OK_MIN = 1.2  # spread_ok for choosing k level
LOW_CORR_ABS = 0.05  # low_corr if abs(corr) < this (when corr_ln is not None)

# Trend verdict (base, not tail_mode)
TREND_VERDICT_THRESHOLD = 0.10  # ±10% for "стоит" vs "растёт"/"падает"

# Windows
WINDOW_DAYS_FOR_K_NORMAL = 60
WINDOW_DAYS_FOR_K_COLD = 14
SERIES_DAYS_COLD = 14
SERIES_WEEKS_NORMAL = 8
SPREAD_RECENT_DAYS = 14  # last 14 days for spread_used_recent

# Min d_views
MIN_D_VIEWS_NORMAL = 3
MIN_D_VIEWS_COLD = 2
