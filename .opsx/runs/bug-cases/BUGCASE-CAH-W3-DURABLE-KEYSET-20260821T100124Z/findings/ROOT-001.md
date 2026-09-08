FINDING_PACKET

CASE_ID: BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z
FINDING_ID: ROOT-001
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: Partial live factual positions may shrink the durable confirmed keyword set
PRODUCTION_CLASSIFICATION: pending_adjudication
RELATION_TO_ROOT: root_tracking
STATUS: adjudicating
CHAT_REQUIRED: false
CLAIM_PRIORITY: 1
PACKET_PURPOSE: root_tracking
INVARIANT: needs extraction
ORIGINAL_FINDING: The owner confirms: «Да, в таком случае убирать ключ нельзя». The supplied W3 context describes a partial live factual-position response causing a subset to be persisted where a previously confirmed durable keyword may be removed.
EVIDENCE: Input packet CURRENT_CHAT_CONTEXT; RAW_INTAKE_TEXT; affected-area candidates confirm_handlers.py and epoch_write.py; RAW_INTAKE_HASH c7da421822d1fdcfcbe074983e872b0434294e2e2f88e86de3dd42a606bf67cc.
RUNTIME_PATH: on_tp_confirm_all -> _load_factual_positions -> _tp_rows_from_adv -> confirm_target_places_in_session
CAUSAL_BOUNDARY: Candidate boundary from live factual-position retrieval through filtered submitted tp_map into durable epoch persistence. Materializer does not assert that this is the confirmed root cause.
WRITE_BOUNDARY: Candidate durable write of card_ab_hold_confirmed_keywords_json through confirm_target_places_in_session; exact retention semantics remain for classification/adjudication.
SOURCE_SNAPSHOT: .opsx/runs/bug-cases/BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z/team/packets/WEX_MATERIALIZER_56bd3ed61c.in.json; INPUT_PACKET_RAW_SHA256 4f681373be037df937d332012585044e2008b218720563d45f163e35d5d29bea; RAW_INTAKE_HASH c7da421822d1fdcfcbe074983e872b0434294e2e2f88e86de3dd42a606bf67cc
DISPOSITION:
NEXT_ACTION: /opsx-classify-bug case=BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z finding=ROOT-001

NEXT_COMMAND:
/opsx-classify-bug case=BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z finding=ROOT-001

MODE: READ_ONLY

FORBIDDEN:
- do not edit production files
- do not use GO
- do not claim a second finding
- do not propose a fix
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not treat pending_adjudication as a classifier result
