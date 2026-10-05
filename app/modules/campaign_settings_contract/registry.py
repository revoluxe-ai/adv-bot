"""Field/source registry канонического контракта настроек.

Spec: campaign-settings-history.
Этот модуль намеренно не импортирует ORM/settings: registry должен валидироваться
в минимальном CI и служить domain contract, а не transport/storage adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from collections.abc import Mapping
from types import MappingProxyType


class ContractValidationError(ValueError):
    """Ошибка fail-closed validation для campaign-settings-history contract."""


# Backward-compatible name used by AST inventory tests/helpers.
RegistryContractError = ContractValidationError


class SemanticRole(StrEnum):
    SETTING = "setting"
    IDENTITY = "identity"
    WB_FACT = "wb_fact"
    RUNTIME_STATE = "runtime_state"
    DERIVED = "derived"
    TECHNICAL = "technical"


class HistoryPolicy(StrEnum):
    STATE = "state"
    METADATA = "metadata"
    EXCLUDED = "excluded"


class ExcelPolicy(StrEnum):
    EDITABLE = "editable"
    READ_ONLY = "read_only"
    EXCLUDED = "excluded"


class NormalizationPolicy(StrEnum):
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"
    ENUM = "enum"
    INT_LIST = "int_list"
    STRING_LIST = "string_list"
    JSON_OBJECT = "json_object"
    DATE = "date"
    DATETIME = "datetime"


@dataclass(frozen=True, slots=True)
class FieldPolicy:
    """Полная policy одного поля; отсутствие измерения запрещено spec."""

    name: str
    semantic_role: SemanticRole
    history: HistoryPolicy
    excel: ExcelPolicy
    normalization: NormalizationPolicy
    exclusion_reason: str | None = None
    excel_alias: str | None = None

    @property
    def normalizer(self) -> str:
        """Compatibility/readability name для canonical normalization contract."""
        return _normalizer_name(self.name, self.normalization)

    @property
    def allowed_values(self) -> tuple[str, ...]:
        """Явный allowlist для enum/literal settings; пусто для open scalar domain."""
        return _ALLOWED_VALUES.get(self.name, ())


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    """Политика зарегистрированного settings-owned source."""

    name: str
    fields: Mapping[str, FieldPolicy]


def _frozen(fields: dict[str, FieldPolicy]) -> Mapping[str, FieldPolicy]:
    return MappingProxyType(dict(sorted(fields.items())))


def _field(
    name: str,
    *,
    role: SemanticRole,
    history: HistoryPolicy,
    excel: ExcelPolicy,
    normalization: NormalizationPolicy,
    reason: str | None = None,
    alias: str | None = None,
) -> FieldPolicy:
    return FieldPolicy(
        name=name,
        semantic_role=role,
        history=history,
        excel=excel,
        normalization=normalization,
        exclusion_reason=reason,
        excel_alias=alias,
    )

# Reviewed baseline: openspec/changes/campaign-settings-history/field-policy-baseline.md
_STATE_FIELDS: dict[str, frozenset[str]] = {
    "AdvSetting": frozenset({
        "bot_active","black_phrases","relevant_phrases","pass_days","boost","max_cpc",
        "min_views_for_ml_predict","bidder_active","max_cpm","max_place","use_incremental_stats",
        "use_cluster_stats_in_freshness","min_block_position","clusters_mode","target_ctr_mode",
        "hide_small_query_keywords","bidder_coroutine_type","target_ctr_mode_strategy",
        "new_auto_min_ctr_mode","reset_place","bidder_step","exponent_predict_ctr",
        "auction_boost_all_phrase_mode","plan_for_sales_for_day","target_price_for_order",
        "max_price_for_order","substitute_fact_cpo_for_max","raise_plan_on_promobonuses",
        "bidder_for_auto","auto_update_white_list","auto_update_minus_phrases",
        "auto_budget_watchdog_enabled","auto_update_target_place","auto_update_exponent",
        "rec_system_mode","auto_shelf_bid_control_enabled","auto_shelf_bid_control_strategy",
        "hide_zero_views_keywords","max_balance_adding_for_day","auto_budget_daily_limit",
        "search_auto_budget_daily_limit","use_common_budget","common_budget_daily_limit",
        "auto_budget_total_limit","search_auto_budget_total_limit","common_budget_total_limit",
        "auto_adv_target_status","auction_adv_target_status","auto_add_only_relevant_phrase",
        "orders_source_for_auto_mode","predict_ctr_mode","sales_predict_method","aggressiveness",
        "keyword_calibration_max_step","card_ab_hold_mode","card_ab_hold_allowed_phrases_snapshot",
        "card_ab_hold_warmup_duration_hours","card_ab_hold_confirmed_keywords_json",
        "card_ab_hold_confirmed_target_places_json","card_ab_hold_confirmed_auto_participation",
        "card_ab_hold_confirmed_auto_bid","bidder_mode","updater_common_bid_in_search_adv_active_status",
        "white_list_mode","individual_keywords_target_place_mode","min_target_position",
        "target_position_mode","strategy","auto_update_strategy","auto_common_budget",
    }),
    "KeywordSetting": frozenset({"hard_status","strategy_mode","relevant","target_place"}),
    "AutoShelfBidControlSettings": frozenset({
        "max_bid_minor","currency","min_bid_distance_minor","target_test_impressions",
        "target_test_observation_minutes","test_share","retest_interval_days",
    }),
    "AdvTimeSettings": frozenset({"schedule_enabled","date_enabled","date_start","date_end","timezone"}),
    "AdvTimeWeekMask": frozenset({"hours_mask"}),
}

_METADATA_FIELDS: dict[str, frozenset[str]] = {
    "AdvSetting": frozenset({"id","adv_id","name","wb_cabinet_id","nmids","type","_search_adv_id"}),
    "KeywordSetting": frozenset({"text"}),
    "AutoShelfBidControlSettings": frozenset({"nmid"}),
    "AdvTimeSettings": frozenset(),
    "AdvTimeWeekMask": frozenset({"dow"}),
}

_EXCLUDED_FIELD_REASONS: dict[str, dict[str, tuple[SemanticRole, str]]] = {
    "AdvSetting": {
        "active_status": (SemanticRole.WB_FACT, "WB-observed physical campaign status"),
        "automatic_version": (SemanticRole.TECHNICAL, "legacy/deprecated technical field"),
        "wb_bid_type": (SemanticRole.WB_FACT, "WB-observed physical campaign state"),
        "wb_placement_search": (SemanticRole.WB_FACT, "WB-observed placement state"),
        "wb_placement_recommendations": (SemanticRole.WB_FACT, "WB-observed placement state"),
        "hard_min_ctr": (SemanticRole.TECHNICAL, "legacy/deprecated technical field"),
        "parsing_active": (SemanticRole.RUNTIME_STATE, "operational parsing state"),
        "last_update": (SemanticRole.RUNTIME_STATE, "operational bookkeeping timestamp"),
        "cpm": (SemanticRole.WB_FACT, "WB-observed physical bid state"),
        "card_ab_hold_degraded": (SemanticRole.RUNTIME_STATE, "AB hold health/runtime state"),
        "card_ab_hold_phase": (SemanticRole.RUNTIME_STATE, "AB hold workflow state"),
        "card_ab_hold_warmup_started_at": (SemanticRole.RUNTIME_STATE, "AB hold workflow timestamp"),
        "card_ab_hold_generation": (SemanticRole.RUNTIME_STATE, "AB hold workflow generation"),
        "card_ab_hold_wb_sync_idempotency_key": (SemanticRole.RUNTIME_STATE, "WB sync idempotency state"),
        "card_ab_hold_pending_intent_json": (SemanticRole.RUNTIME_STATE, "pending workflow intent"),
        "card_ab_hold_sync_status": (SemanticRole.RUNTIME_STATE, "WB sync workflow state"),
        "card_ab_hold_emergency_latch": (SemanticRole.RUNTIME_STATE, "safety runtime latch"),
        "card_ab_hold_emergency_educated": (SemanticRole.RUNTIME_STATE, "safety runtime acknowledgement"),
    },
    "KeywordSetting": {
        "id": (SemanticRole.TECHNICAL, "relational primary key"),
        "adv_setting_id": (SemanticRole.TECHNICAL, "owner foreign key"),
        "predict_ctr": (SemanticRole.DERIVED, "derived prediction"),
        "added_clicks": (SemanticRole.DERIVED, "derived/statistical adjustment"),
        "added_views": (SemanticRole.DERIVED, "derived/statistical adjustment"),
        "auto_block": (SemanticRole.RUNTIME_STATE, "automation runtime state"),
    },
    "AutoShelfBidControlSettings": {
        "id": (SemanticRole.TECHNICAL, "relational primary key"),
        "created_at": (SemanticRole.TECHNICAL, "persistence timestamp"),
        "updated_at": (SemanticRole.TECHNICAL, "persistence timestamp"),
    },
    "AdvTimeSettings": {
        "id": (SemanticRole.TECHNICAL, "relational primary key"),
        "adv_setting_id": (SemanticRole.TECHNICAL, "owner foreign key"),
        "created_at": (SemanticRole.TECHNICAL, "persistence timestamp"),
        "updated_at": (SemanticRole.TECHNICAL, "persistence timestamp"),
    },
    "AdvTimeWeekMask": {
        "adv_setting_id": (SemanticRole.TECHNICAL, "owner foreign key"),
    },
}

_ALLOWED_VALUES: dict[str, tuple[str, ...]] = {
    "bidder_coroutine_type": ("OLD_UPDATE_CPM_BIDDER", "UPDATE_CLUSTER_BIDS"),
    "auto_shelf_bid_control_strategy": ("cycle_metric", "plan_distance", "ctr", "cpc"),
    "orders_source_for_auto_mode": ("COMMON_STATISTIC", "ADV_SUM"),
    "predict_ctr_mode": ("V1", "V2"),
    "sales_predict_method": ("DIRECT_SALES", "BY_CARTS"),
    "bidder_mode": ("BY_AUTO_MAX_CPM", "BY_POSITIONS"),
    "white_list_mode": (
        "ACTIVE_ONLY_WHITE_LIST",
        "TAIL_TRIMMING",
        "REPLACE_ON_TRIM",
        "ABOVE_MIN_RATING",
    ),
    "target_position_mode": ("MIN_CPA", "MAX_CART_TO_VIEWS_CONV"),
    "strategy": ("MIN_CPO", "OPTIMUM", "MAX_CONV"),
    "strategy_mode": ("OFF", "MIN_CPA", "OPTIMUM", "MAX_CONVERSION"),
    "target_ctr_mode_strategy": ("forward", "keep"),
    "card_ab_hold_mode": ("off", "pending_setup", "active"),
    "currency": ("RUB",),
}

_ENUM_VALUE_FIELDS = frozenset({
    "bidder_coroutine_type",
    "auto_shelf_bid_control_strategy",
})
_ENUM_NAME_FIELDS = frozenset({
    "orders_source_for_auto_mode",
    "predict_ctr_mode",
    "sales_predict_method",
    "bidder_mode",
    "white_list_mode",
    "target_position_mode",
    "strategy",
    "strategy_mode",
})
_LITERAL_STRING_FIELDS = frozenset({
    "target_ctr_mode_strategy",
    "card_ab_hold_mode",
    "currency",
})


def _normalizer_name(field_name: str, policy: NormalizationPolicy) -> str:
    """Stable semantic normalizer name used in tests/audit output."""
    if policy in {NormalizationPolicy.INT, NormalizationPolicy.FLOAT, NormalizationPolicy.BOOL}:
        return "typed_scalar"
    if policy is NormalizationPolicy.INT_LIST:
        return "sorted_unique_int_list"
    if policy is NormalizationPolicy.STRING_LIST:
        if field_name == "card_ab_hold_confirmed_keywords_json":
            return "sorted_unique_str_list_or_null"
        return "sorted_unique_str_list"
    if policy is NormalizationPolicy.JSON_OBJECT:
        return "canonical_json_or_null"
    if policy is NormalizationPolicy.ENUM:
        if field_name in _ENUM_VALUE_FIELDS:
            return "enum_value"
        return "enum_name"
    if policy is NormalizationPolicy.DATE:
        return "date_iso_or_null"
    if policy is NormalizationPolicy.DATETIME:
        return "datetime_iso_or_null"
    if policy is NormalizationPolicy.STRING:
        if field_name == "timezone":
            return "timezone_name"
        if field_name in _LITERAL_STRING_FIELDS:
            return "literal_str"
        return "typed_scalar"
    raise ContractValidationError(
        f"unsupported normalizer mapping field={field_name!r} policy={policy!r}"
    )


_NORMALIZATION_FIELDS: dict[NormalizationPolicy, frozenset[str]] = {
    NormalizationPolicy.FLOAT: frozenset({
        "boost","hard_min_ctr","max_cpc","exponent_predict_ctr","target_price_for_order",
        "card_ab_hold_confirmed_auto_bid","predict_ctr","test_share",
    }),
    NormalizationPolicy.BOOL: frozenset({
        "bot_active","wb_placement_search","wb_placement_recommendations","parsing_active",
        "bidder_active","use_incremental_stats","use_cluster_stats_in_freshness","clusters_mode",
        "target_ctr_mode","new_auto_min_ctr_mode","reset_place","auction_boost_all_phrase_mode",
        "substitute_fact_cpo_for_max","raise_plan_on_promobonuses","bidder_for_auto",
        "auto_update_white_list","auto_update_minus_phrases","auto_budget_watchdog_enabled",
        "auto_update_target_place","auto_update_exponent","rec_system_mode",
        "auto_shelf_bid_control_enabled","hide_zero_views_keywords","use_common_budget",
        "auto_adv_target_status","auction_adv_target_status","auto_add_only_relevant_phrase",
        "card_ab_hold_degraded","card_ab_hold_confirmed_auto_participation",
        "card_ab_hold_emergency_latch","card_ab_hold_emergency_educated",
        "updater_common_bid_in_search_adv_active_status","individual_keywords_target_place_mode",
        "auto_update_strategy","auto_common_budget","relevant","auto_block","schedule_enabled","date_enabled",
    }),
    NormalizationPolicy.STRING: frozenset({
        "name","active_status","wb_bid_type","target_ctr_mode_strategy","card_ab_hold_mode",
        "card_ab_hold_phase","card_ab_hold_wb_sync_idempotency_key","card_ab_hold_sync_status",
        "text","currency","timezone",
    }),
    NormalizationPolicy.ENUM: frozenset({
        "bidder_coroutine_type","auto_shelf_bid_control_strategy","orders_source_for_auto_mode",
        "predict_ctr_mode","sales_predict_method","bidder_mode","white_list_mode",
        "target_position_mode","strategy","strategy_mode",
    }),
    NormalizationPolicy.INT_LIST: frozenset({"nmids"}),
    NormalizationPolicy.STRING_LIST: frozenset({
        "black_phrases","relevant_phrases","card_ab_hold_allowed_phrases_snapshot",
        "card_ab_hold_confirmed_keywords_json",
    }),
    NormalizationPolicy.JSON_OBJECT: frozenset({
        "card_ab_hold_pending_intent_json","card_ab_hold_confirmed_target_places_json",
    }),
    NormalizationPolicy.DATE: frozenset({"date_start","date_end"}),
    NormalizationPolicy.DATETIME: frozenset({
        "last_update","card_ab_hold_warmup_started_at","created_at","updated_at",
    }),
}

_EXCEL_EDITABLE: dict[str, frozenset[str]] = {
    "AdvSetting": frozenset({
        "aggressiveness","auto_add_only_relevant_phrase","auto_budget_daily_limit",
        "auto_budget_total_limit","auto_budget_watchdog_enabled","auto_common_budget",
        "auto_shelf_bid_control_enabled","auto_update_exponent","auto_update_strategy",
        "auto_update_target_place","auto_update_white_list","bidder_coroutine_type",
        "bidder_for_auto","bidder_step","bot_active","clusters_mode","common_budget_daily_limit",
        "common_budget_total_limit","exponent_predict_ctr","hide_small_query_keywords",
        "hide_zero_views_keywords","individual_keywords_target_place_mode",
        "keyword_calibration_max_step","max_cpm","max_place","max_price_for_order",
        "min_views_for_ml_predict","orders_source_for_auto_mode","plan_for_sales_for_day",
        "predict_ctr_mode","raise_plan_on_promobonuses","rec_system_mode","reset_place",
        "sales_predict_method","search_auto_budget_daily_limit","search_auto_budget_total_limit",
        "strategy","substitute_fact_cpo_for_max","target_ctr_mode","target_ctr_mode_strategy",
        "target_position_mode","target_price_for_order",
        "updater_common_bid_in_search_adv_active_status","use_common_budget",
        "use_incremental_stats","white_list_mode",
    }),
    "KeywordSetting": frozenset({"target_place"}),
    "AutoShelfBidControlSettings": frozenset({
        "max_bid_minor","min_bid_distance_minor","target_test_impressions",
        "target_test_observation_minutes","test_share",
    }),
    "AdvTimeSettings": frozenset(),
    "AdvTimeWeekMask": frozenset(),
}

_EXCEL_ALIASES: dict[str, dict[str, str]] = {
    "AdvSetting": {
        "id": "adv_setting_id","adv_id": "adv_id","_search_adv_id": "search_adv_id","nmids": "nmid:first",
    },
    "KeywordSetting": {
        "id": "keyword_id","text": "keyword","target_place": "current_target_place",
    },
    "AutoShelfBidControlSettings": {
        "max_bid_minor": "auto_shelf_max_bid_rub",
        "min_bid_distance_minor": "auto_shelf_min_bid_distance_rub",
        "target_test_impressions": "auto_shelf_target_test_impressions",
        "target_test_observation_minutes": "auto_shelf_target_test_observation_minutes",
        "test_share": "auto_shelf_test_share",
    },
    "AdvTimeSettings": {},
    "AdvTimeWeekMask": {},
}

_EXCLUDED_SOURCES_MUTABLE: dict[str, str] = {
    "WBUserCabinet": "cabinet/account entity, not campaign settings source",
    "WBBalancePayment": "payment entity",
    "WBBonusPayment": "payment entity",
    "WBCategory": "catalog metadata entity",
    "WBToken": "credential/token entity",
    "AdvKeyword": "keyword dictionary/entity, not per-campaign settings state",
    "WBCard": "product/card entity",
    "AutoShelfBidControlState": "runtime state machine, not user configuration",
    "WBAutoBudgetTopUp": "budget top-up transaction/audit entity, not settings authority",
    "WBCabinet": "cabinet/account entity, not campaign settings source",
    "WBCampaignPromoSpend": "campaign promo-spend fact entity, not settings configuration",
}
EXCLUDED_SOURCES: Mapping[str, str] = MappingProxyType(_EXCLUDED_SOURCES_MUTABLE)

_INT_FIELDS = frozenset({
    "id","adv_id","wb_cabinet_id","_search_adv_id","automatic_version","pass_days","type",
    "min_views_for_ml_predict","max_cpm","max_place","min_block_position",
    "hide_small_query_keywords","bidder_step","plan_for_sales_for_day","max_price_for_order",
    "cpm","max_balance_adding_for_day","auto_budget_daily_limit","search_auto_budget_daily_limit",
    "common_budget_daily_limit","auto_budget_total_limit","search_auto_budget_total_limit",
    "common_budget_total_limit","aggressiveness","keyword_calibration_max_step",
    "card_ab_hold_warmup_duration_hours","card_ab_hold_generation","min_target_position",
    "adv_setting_id","hard_status","added_clicks","added_views","target_place","nmid",
    "max_bid_minor","min_bid_distance_minor","target_test_impressions",
    "target_test_observation_minutes","retest_interval_days","dow","hours_mask",
})


def _normalization_for(field_name: str) -> NormalizationPolicy:
    """Возвращает явную normalization policy из reviewed baseline."""
    matches = [policy for policy, names in _NORMALIZATION_FIELDS.items() if field_name in names]
    if field_name in _INT_FIELDS:
        matches.append(NormalizationPolicy.INT)
    if len(matches) != 1:
        raise ContractValidationError(
            f"normalization policy must be exactly one for field={field_name!r}; matches={matches}"
        )
    return matches[0]


def _excel_policy(source: str, field_name: str) -> tuple[ExcelPolicy, str | None]:
    """Строит Excel policy из единой reviewed projection map."""
    alias = _EXCEL_ALIASES[source].get(field_name)
    if field_name in _EXCEL_EDITABLE[source]:
        return ExcelPolicy.EDITABLE, alias
    if alias is not None:
        return ExcelPolicy.READ_ONLY, alias
    return ExcelPolicy.EXCLUDED, None


def _build_source_policy(source: str) -> SourcePolicy:
    """Материализует полную policy source без silent field defaults."""
    state = _STATE_FIELDS[source]
    metadata = _METADATA_FIELDS[source]
    excluded = _EXCLUDED_FIELD_REASONS[source]
    overlap = (state & metadata) | (state & excluded.keys()) | (metadata & excluded.keys())
    if overlap:
        raise ContractValidationError(f"overlapping field classifications source={source}: {sorted(overlap)}")

    fields: dict[str, FieldPolicy] = {}
    for field_name in sorted(state):
        excel, alias = _excel_policy(source, field_name)
        fields[field_name] = _field(
            field_name,
            role=SemanticRole.SETTING,
            history=HistoryPolicy.STATE,
            excel=excel,
            normalization=_normalization_for(field_name),
            alias=alias,
        )
    for field_name in sorted(metadata):
        excel, alias = _excel_policy(source, field_name)
        fields[field_name] = _field(
            field_name,
            role=SemanticRole.IDENTITY,
            history=HistoryPolicy.METADATA,
            excel=excel,
            normalization=_normalization_for(field_name),
            alias=alias,
        )
    for field_name, (role, reason) in sorted(excluded.items()):
        excel, alias = _excel_policy(source, field_name)
        fields[field_name] = _field(
            field_name,
            role=role,
            history=HistoryPolicy.EXCLUDED,
            excel=excel,
            normalization=_normalization_for(field_name),
            reason=reason,
            alias=alias,
        )
    return SourcePolicy(name=source, fields=_frozen(fields))


_REGISTERED_SOURCES_MUTABLE = {
    source: _build_source_policy(source) for source in sorted(_STATE_FIELDS)
}
REGISTERED_SOURCES: Mapping[str, SourcePolicy] = MappingProxyType(_REGISTERED_SOURCES_MUTABLE)


def validate_registry(
    registered: Mapping[str, SourcePolicy] = REGISTERED_SOURCES,
    excluded_sources: Mapping[str, str] = EXCLUDED_SOURCES,
) -> None:
    """Fail-closed validation самого registry для campaign-settings-history."""
    overlap = set(registered) & set(excluded_sources)
    if overlap:
        raise ContractValidationError(f"source cannot be registered and excluded: {sorted(overlap)}")
    for source_name, reason in excluded_sources.items():
        if not source_name or not reason.strip():
            raise ContractValidationError("excluded source requires non-empty name and reason")
    for source_name, source in registered.items():
        if source_name != source.name or not source.fields:
            raise ContractValidationError(f"invalid source policy: {source_name}")
        for field_name, policy in source.fields.items():
            if field_name != policy.name:
                raise ContractValidationError(f"field key/name mismatch: {source_name}.{field_name}")
            if policy.history is HistoryPolicy.EXCLUDED and not (policy.exclusion_reason or "").strip():
                raise ContractValidationError(f"excluded field requires reason: {source_name}.{field_name}")
            if policy.history is not HistoryPolicy.EXCLUDED and policy.exclusion_reason is not None:
                raise ContractValidationError(f"included field cannot have exclusion reason: {source_name}.{field_name}")
            if policy.normalization is NormalizationPolicy.ENUM and not policy.allowed_values:
                raise ContractValidationError(
                    f"enum field requires explicit allowed_values: {source_name}.{field_name}"
                )
            if policy.normalizer == "literal_str" and not policy.allowed_values:
                raise ContractValidationError(
                    f"literal field requires explicit allowed_values: {source_name}.{field_name}"
                )


def validate_registry_structure(
    registered: Mapping[str, SourcePolicy] = REGISTERED_SOURCES,
    excluded_sources: Mapping[str, str] = EXCLUDED_SOURCES,
) -> None:
    """Compatibility name for the same fail-closed registry validation."""
    validate_registry(registered, excluded_sources)


def validate_field_inventory(
    source_name: str,
    actual_fields: set[str] | frozenset[str],
    registered: Mapping[str, SourcePolicy] = REGISTERED_SOURCES,
) -> None:
    """Сверяет runtime/static mapped fields source с registry exact-set."""
    source = registered.get(source_name)
    if source is None:
        raise ContractValidationError(f"unregistered settings source: {source_name}")
    expected = set(source.fields)
    actual = set(actual_fields)
    if actual != expected:
        missing_policy = sorted(actual - expected)
        stale_policy = sorted(expected - actual)
        raise ContractValidationError(
            f"field inventory mismatch source={source_name}; "
            f"missing_policy={missing_policy}; stale_policy={stale_policy}"
        )


def validate_source_inventory(
    actual_source_names: set[str] | frozenset[str],
    registered: Mapping[str, SourcePolicy] = REGISTERED_SOURCES,
    excluded_sources: Mapping[str, str] = EXCLUDED_SOURCES,
) -> None:
    """Требует явное REGISTERED либо EXCLUDED_SOURCE(reason) для каждого ORM source."""
    expected = set(registered) | set(excluded_sources)
    actual = set(actual_source_names)
    if actual != expected:
        unknown = sorted(actual - expected)
        stale = sorted(expected - actual)
        raise ContractValidationError(
            f"source inventory mismatch; unknown_sources={unknown}; stale_policies={stale}"
        )


validate_registry()


_SHELF_EDITABLE_ALIAS_ORDER = (
    "max_bid_minor",
    "test_share",
    "target_test_impressions",
    "target_test_observation_minutes",
    "min_bid_distance_minor",
)


def excel_editable_fields(source_name: str) -> frozenset[str]:
    """Spec campaign-settings-history: editable source fields из canonical registry."""
    source = REGISTERED_SOURCES[source_name]
    return frozenset(
        name for name, policy in source.fields.items() if policy.excel is ExcelPolicy.EDITABLE
    )


def excel_read_only_fields(source_name: str) -> frozenset[str]:
    """Spec campaign-settings-history: read-only source fields из canonical registry."""
    source = REGISTERED_SOURCES[source_name]
    return frozenset(
        name for name, policy in source.fields.items() if policy.excel is ExcelPolicy.READ_ONLY
    )


def excel_alias(source_name: str, field_name: str) -> str | None:
    """Spec campaign-settings-history: human-facing alias поля без отдельного whitelist."""
    return REGISTERED_SOURCES[source_name].fields[field_name].excel_alias


def ordered_shelf_editable_aliases() -> tuple[str, ...]:
    """Spec campaign-settings-history: сохраняет существующий v8 порядок shelf EDIT колонок."""
    editable = excel_editable_fields("AutoShelfBidControlSettings")
    if set(_SHELF_EDITABLE_ALIAS_ORDER) != set(editable):
        raise ContractValidationError(
            "shelf editable presentation order drifted from registry membership"
        )
    aliases: list[str] = []
    for field_name in _SHELF_EDITABLE_ALIAS_ORDER:
        alias = excel_alias("AutoShelfBidControlSettings", field_name)
        if alias is None:
            raise ContractValidationError(
                f"editable shelf field requires Excel alias: {field_name}"
            )
        aliases.append(alias)
    return tuple(aliases)
