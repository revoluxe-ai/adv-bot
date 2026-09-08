INTAKE_RECORD

CASE_ID: BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z
INTAKE_ID: INTAKE-001
CREATED_AT: 2026-08-21T10:01:24.329377+00:00
SOURCE_TYPE: manual
SOURCE_REFERENCE: USER_MESSAGE / WEX/MATERIALIZER/56bd3ed61c
RAW_REPORT: Да, в таком случае убирать ключ нельзя
OBSERVED_SYMPTOM: При частичном live factual-position ответе W3 может сохранить только подмножество ключей и удалить ранее подтверждённый durable keyword.
KNOWN_CONTEXT: W3 concern from the preceding analysis: on_tp_confirm_all reads live factual positions through _load_factual_positions; _tp_rows_from_adv filters missing/non-positive facts; confirm_target_places_in_session persists card_ab_hold_confirmed_keywords_json from the submitted tp_map subset. The owner states that a key must not be removed in that situation. Affected areas supplied by intake: app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/confirm_handlers.py; app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/epoch_write.py.
STATUS: intake_recorded
LAST_ACTIVITY_AT: 2026-08-21T10:08:00+00:00
NEXT_ACTION: /opsx-classify-bug case=BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z finding=ROOT-001
DISPOSITION:
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID:
RESULT_PATH:

## Normalized intake

OBSERVED_BEHAVIOR: The supplied context describes a path where on_tp_confirm_all obtains a partial live factual-position result, _tp_rows_from_adv excludes missing or non-positive facts, and confirm_target_places_in_session persists the resulting subset as card_ab_hold_confirmed_keywords_json. The stated concern is that an already confirmed durable keyword can thereby disappear.
EXPECTED_BEHAVIOR_CANDIDATE: An already confirmed durable keyword must not be removed solely because a live factual-position read is partial. This remains a candidate expectation pending classification.
REPRODUCTION_INFORMATION: Trigger context is a partial live factual-position response during on_tp_confirm_all; no standalone reproduction steps or runtime capture were supplied.
EVIDENCE_REFERENCES: CURRENT_CHAT_CONTEXT in the input packet; affected-area candidates confirm_handlers.py and epoch_write.py; RAW_INTAKE_HASH c7da421822d1fdcfcbe074983e872b0434294e2e2f88e86de3dd42a606bf67cc.
INFERRED_ASSUMPTIONS: The partial live response is possible in the described execution path; the supplied persistence path is the relevant durable write path. These are intake assumptions, not a production classification or root-cause finding.
UNRESOLVED_QUESTIONS: Whether the partial response is distinguishable from an authoritative empty result; the exact merge/retention rule expected at the durable epoch boundary; whether the supplied path reproduces the report in the current repository state.
INTAKE_SUFFICIENCY: SUFFICIENT_FOR_CLASSIFICATION
