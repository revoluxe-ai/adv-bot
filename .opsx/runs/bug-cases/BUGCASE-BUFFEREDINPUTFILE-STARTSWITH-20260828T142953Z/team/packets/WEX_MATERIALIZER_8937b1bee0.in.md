# MATERIALIZER input (companion)

WORKER_ID: MATERIALIZER
WORKER_EXECUTION_ID: WEX/MATERIALIZER/8937b1bee0
PARENT_ORCHESTRATION_ID: ORCH/bug-team/9745ba6a72d6
CASE_ID: BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z
FINDING_ID: null
ATTEMPT: 1
MAX_ATTEMPTS: 2
TIMEOUT_SECONDS: 600
INPUT_PACKET_JSON: C:/Users/vkita/my_code/meta-repo/adv-bot/.tmp/opsx-bug-cases/BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z/team/packets/WEX_MATERIALIZER_8937b1bee0.in.json
OUTPUT_PACKET_PATH: C:/Users/vkita/my_code/meta-repo/adv-bot/.tmp/opsx-bug-cases/BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z/team/packets/WEX_MATERIALIZER_8937b1bee0.out.json
HEARTBEAT_PATH: C:/Users/vkita/my_code/meta-repo/adv-bot/.tmp/opsx-bug-cases/BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z/team/heartbeats/WEX_MATERIALIZER_8937b1bee0.json
WRITE_BOUNDARY_SUMMARY: intakes/**, findings/**, CASE.md, LEDGER, team packets out under case
ALLOWED_INPUT_ARTIFACTS:
  - C:/Users/vkita/my_code/meta-repo/adv-bot/.tmp/opsx-bug-cases/BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z/intakes/_RAW_INTAKE_SEED.txt
  - C:/Users/vkita/my_code/meta-repo/adv-bot/.tmp/opsx-bug-cases/BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z/team/packets/WEX_MATERIALIZER_8937b1bee0.in.json
  - .cursor/commands/opsx-materialize-bug-queue.md
  - .cursor/pipeline/bug-team/workers/MATERIALIZER.md
  - .cursor/pipeline/bug-team/packets/RAW_INTAKE.md
  - .cursor/pipeline/bug-team/WRITE_BOUNDARY.md
  - .tmp/opsx-bug-cases/ (duplicate scan only)

TASK: Execute /opsx-materialize-bug-queue mode=intake using RAW_INTAKE_PATH verbatim.
Do duplicate check against existing .tmp/opsx-bug-cases/*/CASE.md and intakes.
Create durable case map; write OUTPUT_PACKET JSON with STATUS/TERMINAL_STATUS.
FORBIDDEN: classify, fix, Owner GO, production edits, git commit.
