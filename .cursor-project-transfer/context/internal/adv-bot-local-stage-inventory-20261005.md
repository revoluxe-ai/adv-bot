# Local stage inventory (2026-10-05)

Source: [Inventory local adv-bot stage](bc-ef73ba6e-862f-5554-b14b-4e9523f76ab6). HOST: `HOME-PC` (`C:\Users\vkita`). Read-only. GO_TO_BOOTSTRAP: **NO**.

| | |
|---|---|
| LOCAL_STAGE_HEAD | `0653c286648be99acf564b6c4a268b9452333805` |
| ORIGIN_STAGE_HEAD | `4763b0a1602d00da285739f2be9af5a553ef3c0a` |
| ahead / behind origin | **33 / 0** |
| MAIN_DIRTY | **26** paths |

Not safe to touch: main checkout (executor moved HEAD during the run; uncommitted wb_sky_control_plane, snapshot archive move, decisions index, bounded-verify commands). `campaign-settings-history` worktree @ `4fe28087a` is 8 behind stage, dirty runs. `shop-wide-campaign-data-collection` @ `47a94d4eb` dirty `.venv` only. Keyword history and full export exist as archives on stage; full-export worktree removed during the run.

Do not push, do not clean unknown dirty paths.
