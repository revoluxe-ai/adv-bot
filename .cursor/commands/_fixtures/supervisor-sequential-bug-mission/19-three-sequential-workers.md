# 19 — Three sequential workers succeed; mission progresses (SUP-LIVE-001)

```text
MISSION unfinished
WORKERS: W1, W2, W3 sequential READY
W1 PRIMARY_TASK_HANDLE recorded at launch
W1 returns ACCEPTED / COMPLETED
```

## Expected

One iteration MAY chain:

```text
TERMINAL_RESULT(W1)
→ STATE_ADVANCE (W1 leaves RUNNING; handle cleared)
→ DISPATCH(W2)
```

Then the same for W2 → W3. After W3 terminal, either next READY dispatch
or mission COMPLETED / all-terminal proof.

```text
exactly-one-of-four-outcomes: NOT REQUIRED
silent stall with no active worker: FORBIDDEN
```
