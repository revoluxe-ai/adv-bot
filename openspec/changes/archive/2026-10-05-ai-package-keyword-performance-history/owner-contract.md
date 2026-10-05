# Owner Contract

## Что хотим получить

Одна deterministic AI Package выгрузка через существующий `ExportService` должна
содержать максимально полную и удобную для LLM историю эффективности поисковых
запросов/ключей и позиций: canonical daily facts, готовые analytical windows,
current state, change/comparison deltas, coverage и отдельный root `DATA_MAP.json`
(с сохранением существующих manifest-конвенций).

WB Sky собирает и детерминированно подготавливает данные; LLM получает уже
готовые analytical datasets и не восстанавливает daily history, окна, semantics
позиции или missing vs zero самостоятельно. Готовые окна не заменяют canonical
daily evidence.

## Зачем

Сейчас query-level daily history, позиции и cluster stats живут в ClickHouse и
bot/scripts/UI, но не входят в AI Package v1. UI-пути агрегируют физические
`adv_id`, смешивают Auto/Search, реконструируют spend и подменяют missing
позиции. Сильной LLM после одной выгрузки нельзя честно ответить «что было
вчера / за 7–365 дней / YTD / за всю доступную историю» без ручного join десятков
неописанных источников.

## Что должно остаться неизменным

- `ExportService` остаётся единственным authority для сборки AI Package
  (reuse pattern как у `campaign_settings_snapshot`).
- Auto (shelf) и Search (keywords) campaign ids остаются раздельными original
  rows; silent merge запрещён.
- Физический `adv_id` и leg/placement identity (где доказуемо) сохраняются в
  export grain.
- Telegram/graph presentation path (`graphic_positions_creator`, nearest-day fill,
  jitter, zero→max_pos) категорически не является canonical export source.
- Export path остаётся read-only: без WB API writes, collectors, PG/Redis/
  control-plane writes.
- Существующие v1 datasets (`campaign_full_stat`, `complex_adv_funnel`,
  `campaign_settings_snapshot`, `shop_product_orders_sales`) не ломаются.
- Domain contract не смешивается с `CampaignResourceSnapshotV1`, Control Plane A1,
  Redis snapshot DTO, Telegram/UI models.

## Чего сейчас не делаем

- Store DRR, shop-wide sales, campaign discovery, campaign settings history,
  prices, stocks, promo, finance, Control Plane, ChangeSet, recommendations.
- Automated bid writes, campaign management, production WB writes.
- Второй exporter или Excel как canonical format.
- AI labels (GOOD/BAD/INCREASE_BID/STOP) — только факты и deltas.
- Causal claims («bid increase caused position improvement»).
- Merge, push, PR, deploy в рамках planning hop.

## Как поймём, что получилось

После одной выгрузки LLM без нового запроса к WB Sky может ответить по
стандартным периодам (1d…365d, MTD/QTD/YTD, previous comparable, all available)
и определить рост/падение queries, ranking, CTR, CPO (где доказано), bid без
результата, появление/исчезновение ключей, недостаточность данных.

Acceptance (observable):

1. Daily query history сохраняется на strict grain (shop × logical resource ×
   physical `adv_id` × leg where proven × nmid × normalized query × date).
2. Экспортируется вся реально доступная история, не обрезанная UI pagination
   7/30 днями; `ExportPeriod` caller bounds документированы отдельно в DATA_MAP.
3. Auto/Search identity не смешивается; physical `adv_id` на каждой строке.
4. Rebound/rebind history не теряется; rebind sets доказывают membership only.
5. Нет duplicate logical counting при query в нескольких legs/campaigns.
6. Missing row ≠ zero (views/orders/position).
7. Missing position не заменяется synthetic max или coalesce-to-zero.
8. Telegram/random graph code не используется как source.
9. Position direction documented: меньшее число = лучше; delta convention в DATA_MAP.
10. Standard windows корректны; calendar year ≠ rolling 365d.
11. Previous comparable windows корректны; insufficient history → partial coverage.
12. Current-state row выбирается deterministic.
13. Derived metrics reproducible; window weighting/null/zero/comparability documented.
14. Spend не fabricated; `QUERY_SPEND_STATUS` explicit per field.
15. UNKNOWN/UNSUPPORTED/FAILED/AMBIGUOUS joins explicit в coverage и DATA_MAP.
16. Deterministic serialization и ZIP/sha256; tampered package detectable.
17. Cross-shop leakage forbidden.
18. `DATA_MAP.json` описывает grain, joins, semantics, bounds, limitations.
19. `ExportService` остаётся single exporter authority.
20. Retrospective bid/decision logs не маскируются под executed actions.
21. Keyword position/nmid observations сохраняют собственный grain без unsafe
    many-to-many campaign assignment.
22. No PG/Redis/control-plane write from export path.
23. Production writes: NONE.

## Решения Owner

- **D-001 Grain:** Canonical daily export grain — shop × logical campaign/resource
  identity × **physical `adv_id`** × **leg/type where proven** × nmid × normalized
  query × date. Silent cross-adv_id или cross-leg aggregation запрещена. UI rollup
  (`KeywordDailyHistoryManager` GROUP BY date only) не является export authority.
  `keyword_daily` MUST emit Owner §6 factual/derived field set per grain row:
  date, shop_id, logical resource identity, adv_id, leg/type where proven, nmid,
  **raw query where source provides it**, normalized query, views, clicks,
  add_to_cart, orders, CPM, CPC (if source supports), CTR, average position,
  source, coverage/status; spend and CPO only per D-003 when semantics proven.
  Derived deterministic metrics: CTR, views→cart, cart→order, views→order.

- **D-002 Full history vs ExportPeriod:** Keyword performance datasets MUST
  export **всю реально доступную историю** из persisted sources (`first_available` /
  `last_available` из фактических MIN/MAX). Caller `ExportPeriod` — отдельный
  bounded context; DATA_MAP MUST document explicit separate bounds. Не обрезать
  history только из-за ExportPeriod или ZIP size без отдельного Owner decision.
  Physical partition/chunking (by year, resource, dataset family) permitted when
  needed for volume; DATA_MAP MUST present unified logical dataset semantics
  regardless of physical layout.

- **D-003 Spend semantics (conservative):** Raw `spend_rub` — только factual с
  доказанной WB→storage lineage (`clusters_adv_stats.spend` when non-null from
  ingest). Default: `null` / `UNAVAILABLE`. Не экспортировать
  `CPM × views / 1000` как factual spend. CPO только при доказанном spend.
  Per-field `QUERY_SPEND_STATUS`: `FACTUAL | DERIVED_VALID | ESTIMATE_ONLY |
  UNAVAILABLE`. UI-derived spend — не factual.

- **D-004 Position semantics:** Field naming отражает **доказанный** source type
  (`avr_pos` cluster stat, `keyword_position_from_api`, etc.) — не называть
  `organic_position` без доказательства. Missing observation ≠ zero ≠ max position.
  Меньшее число = лучше; delta convention — в DATA_MAP.

- **D-005 Rebind/rebound:** Redis rebind sets (`get_rebound_wb_adv_ids`) доказывают
  **membership only**, не temporal transition dates и не guessed rebind intervals.
  Physical `adv_id` provenance на каждой historical row обязателен. Export scope
  MUST expand rebound adv_ids для полной keyword history (не только current
  auto/search ids из `ExportScopeAdv`).

- **D-006 DATA_MAP & coverage:** Отдельный root `DATA_MAP.json` + `coverage.json`
  по existing AI Package conventions. MUST expose unsupported, failed, ambiguous
  joins. Coverage dimensions include: requested, returned, observed, missing,
  confirmed_zero, unsupported, failed, first/last available, freshness, coverage_pct.
  Missing ≠ zero.

- **D-007 Ready windows:** Deterministic window engine с Owner catalog: 1d, 3d, 7d,
  14d, 30d, 90d, 180d, 365d; month_to_date, previous_month; quarter_to_date,
  previous_quarter; year_to_date, previous_year, year_before_previous;
  all_available; plus comparable prev windows (3d vs prev 3d, …, MTD/QTD/YTD vs
  comparable previous). Partial coverage when history shorter than window. Window
  averages/rates MUST define weighting, null, zero, missing-day behavior.
  `keyword_windows` (and related window outputs) MUST emit Owner §10 metric
  families per query/resource/nmid/window: **Traffic** — views, clicks, CTR;
  **Funnel** — carts, orders, views→cart, cart→order, views→order; **Economics**
  — spend, CPM, CPC, CPO only where semantics proven (D-003); **Ranking** —
  position_start, position_end, position_delta, best, worst, average, median
  (if useful and deterministic), observed_days, missing_days. Position direction:
  меньшее число = лучше; delta convention MUST be documented in DATA_MAP (D-004).

- **D-008 Datasets (logical package):** Under `keyword_performance/` (names
  repo-adaptable): `keyword_daily.jsonl` (Owner §6 / D-001 field set),
  `keyword_windows.jsonl` (Owner §9–§10 / D-007),
  `keyword_current_state.jsonl`, `keyword_changes.jsonl`, optional
  `keyword_positions.jsonl` (optional split per §17 if cleaner than embedding
  in daily/windows); root `DATA_MAP.json`, `coverage.json`, existing
  `MANIFEST.json` integration. `keyword_current_state` MUST satisfy Owner §11:
  for each current identity — latest position observation, observation
  timestamp/date, recent/current CPM/bid evidence, strategy/status where
  available, adv_id, nmid, query, resource/leg, freshness, coverage; AI MUST NOT
  need to hunt latest row manually. `keyword_changes` MUST satisfy Owner §12:
  deterministic comparisons (e.g. 7d vs prev7d, 30d vs prev30d, 90d vs prev90d)
  with current, previous, absolute delta, relative delta, percentage-point delta
  where applicable, ranking delta, coverage current/previous; facts and deltas
  only — no AI labels (GOOD/BAD/INCREASE_BID/STOP).

- **D-009 Bid/decision context:** Разделять `OBSERVATION | DECISION | ACTION |
  OBSERVED_POST_STATE`. `bid_decision_log` (retrospectively derived pipeline) MUST
  NOT masquerade as executed bid history or causal timeline. Join only where keys
  доказуемо compatible; иначе mark unsupported/ambiguous.

- **D-010 Position/nmid grain:** Keyword position observations retain own grain
  (date × nmid × query × position_type × source); no unsafe many-to-many campaign
  identity assignment.

- **D-011 Time semantics (planning resolves from evidence):** Day boundary and
  timezone MUST align with persisted CH date columns and existing UTC export
  patterns (`ch_freshness_reader` UTC EOD). Calendar vs rolling windows MUST be
  distinct in DATA_MAP. If repo evidence genuinely conflicts — design records
  precise blocker, не guess.

- **D-012 Lifecycle authorization:** Owner authorizes full OPSX lifecycle through
  `IMPLEMENTATION_COMPLETE + VERIFY_PASS + MERGE_READINESS` without additional
  manual GO tokens. Worktree baseline = **committed local `stage` HEAD verified at
  initial preflight/worktree creation**, documented in inventory `BASE_HEAD` as
  evidence snapshot (initial preflight recorded
  `37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0` on branch
  `ai-package-keyword-performance-history`). This is NOT an obsolete preset SHA
  to reuse automatically when `stage` advances later. Do NOT rebase or silently
  change the created worktree baseline when concurrent `stage` commits appear;
  future merge preflight reconciles divergence against current `stage`.

- **D-013 Live retention:** Production CH retention depth NOT claimed without DB
  reads; `first_available`/`last_available` derived from actual queries per export
  scope only.
