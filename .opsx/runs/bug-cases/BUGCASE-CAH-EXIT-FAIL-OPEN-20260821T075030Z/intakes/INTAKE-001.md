INTAKE_RECORD

CASE_ID: BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z
INTAKE_ID: INTAKE-001
CREATED_AT: 2026-08-21T07:50:30.480015+00:00
SOURCE_TYPE: manual
SOURCE_REFERENCE: USER_MESSAGE / invocation payload WEX/MATERIALIZER/168da3e259
RAW_INTAKE_HASH: 555464264d871defb3cead4a8ca662d47e2b8f220e2e1ddb4f13cfb3c72cb8a8
RAW_INTAKE_SOURCE: USER_MESSAGE
RAW_INTAKE_RECEIVED_AT: 2026-08-21T07:50:30.480015+00:00

RAW_REPORT:
Исправь баг

OBSERVED_SYMPTOM: Исправь баг
KNOWN_CONTEXT: |
  Prior Bugbot High finding in this chat (card_ab_hold EXIT ownership):
  handlers.py disable_card_ab_hold passes telegram_user_id=_callback_actor_id(query).
  When _callback_actor_id returns None (missing/invalid from_user.id), disable_card_ab_hold_in_session skips ownership because `if telegram_user_id is not None` and still performs mode->OFF / clear epoch.
  Expected fail-closed: public EXIT handler must reject when actor is absent/invalid; telegram_user_id=None only for internal session-seam callers.

NORMALIZED_OBSERVATIONS:
  OBSERVED_BEHAVIOR: Public EXIT path disable_card_ab_hold may call disable_card_ab_hold_in_session with telegram_user_id=None when _callback_actor_id returns None; ownership check is skipped and mode->OFF / epoch clear still runs (fail-open).
  EXPECTED_BEHAVIOR_CANDIDATE: Public EXIT handler rejects when actor is absent/invalid; telegram_user_id=None reserved for internal session-seam callers only (fail-closed).
  AFFECTED_AREA_CANDIDATE: app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/handlers.py
  REPRODUCTION_INFORMATION: Trigger EXIT callback with missing/invalid from_user.id so _callback_actor_id returns None; observe disable still proceeds.
  EVIDENCE_REFERENCES: CURRENT_CHAT_CONTEXT from WORKER_INPUT PAYLOAD; RAW_INTAKE_TEXT preserved verbatim above.
  INFERRED_ASSUMPTIONS: Chat context describes the intended defect under adjudication; not confirmed production classification.
  UNRESOLVED_QUESTIONS: Confirm exact call sites and ownership gate semantics during classification (Materializer does not classify).

INTAKE_SUFFICIENCY: SUFFICIENT_FOR_CLASSIFICATION

STATUS: intake_recorded
LAST_ACTIVITY_AT: 2026-08-21T07:55:30Z
NEXT_ACTION: /opsx-classify-bug case=BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z finding=ROOT-001
DISPOSITION:
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID:
RESULT_PATH:
