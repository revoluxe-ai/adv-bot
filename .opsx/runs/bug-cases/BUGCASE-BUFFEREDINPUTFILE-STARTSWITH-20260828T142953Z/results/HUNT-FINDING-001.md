# Bounded hunt — FINDING-001

## Result

HUNT_RESULT: CLEAR

WORKER_ID: BOUNDED_HUNTER
WORKER_EXECUTION_ID: WEX/BOUNDED_HUNTER/c9a36b66db
CASE_ID: BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z
FINDING_ID: FINDING-001
ATTEMPT: 1

## Root (already GREEN — not re-fixed)

- Site: `app/file_handler.py:_get_telegram_file`
- Bug: `image_path.startswith("http")` when `image_path` is `BufferedInputFile`
- Fix present: `isinstance(image_path, BufferedInputFile)` passthrough before str branch

## ROOT_INVARIANT

Callers/helpers must not assume image/path args are `str` when API accepts
`BufferedInputFile`/`InputFile`; never call str methods (`startswith` /
`endswith` / …) without `isinstance`/type guard.

## HUNT_BOUNDS

1. `app/**` for `BufferedInputFile` / `InputFile` used with `.startswith` /
   `.endswith` / other str methods
2. `client_bot` message templates / `file_handler` callers
3. Candidates only — no fix, no RED, no route choice

## Search performed

| Probe | Result |
|---|---|
| `BufferedInputFile` / `InputFile` / `FSInputFile` / `URLInputFile` under `app/` | Usages only in `file_handler.py`, `message_templates/templates.py`, and document-send handlers that construct `BufferedInputFile` and pass it straight to `send_document` |
| All `.startswith(` / `.endswith(` under `app/` | Only `file_handler.py:95` touches an image/path union that can be `BufferedInputFile`; remaining hits are command tokens, callback data, CSV text, filenames (`str`), phrase templates — not InputFile unions |
| `get_telegram_image` / `_get_telegram_file` / `manage_file_id` callers | Sole consumer: `templates.py:manage_file_id` → wraps `BytesIO` → `BufferedInputFile`, else passes `str \| BufferedInputFile` into fixed helper |
| `send_photo` / `send_document` sites with BufferedInputFile | Construct-and-send only; no intermediate str methods on the InputFile object |
| `admin_bot` image/path str methods | No matches |

## Sites reviewed (same-family candidates)

### Root site (fixed — not a candidate)

- `app/file_handler.py` lines 86–95: `BufferedInputFile` / `BytesIO` guards precede `startswith("http")`.
- After guards, remaining branch is `str | None`; `None` short-circuits before `startswith`.

### Callers / templates — no violation

- `app/client_bot/user_interface/message_templates/templates.py`
  - `manage_file_id`: `isinstance(old_image, io.BytesIO)` then wrap; else pass through; calls `get_telegram_image` (now safe).
  - `TextWithImage` / `TextWithKeyboardAndImage`: wrap `BytesIO` or cast to `InputFile | str` for `send_photo` — no str methods on the photo object.

### Document BufferedInputFile constructors — out of failure mode

- `handlers/cpm_builder.py`, `adv_excel_roundtrip.py`, `add_relevant_phrase_templates.py`, `add_black_phrases.py`, `download_keywords.py`
- Pattern: build `BufferedInputFile(...)` → `bot.send_document(document=...)`.
- Filename `.endswith(".xlsx")` checks operate on Telegram `document.file_name` (`str`), not on InputFile.

### Residual note (not promoted to HC-*)

- Guard is `isinstance(..., BufferedInputFile)`, not base `InputFile`.
- No `FSInputFile` / `URLInputFile` usage under `app/`; public typing of `get_telegram_image` is `str | BufferedInputFile`.
- Speculative hardening only — no observed sibling path.

## Disposition

- CANDIDATES: []
- No findings/ candidate stubs created (policy stubs only when CANDIDATES_FOUND).
- HUNT_EFFECTIVENESS: HIGH_WITHIN_DECLARED_SCOPE
- HUNT_FALSE_NEGATIVE_RISK: LOW_WITHIN_DECLARED_SCOPE; code outside `app/` and generated WB clients not treated as same-invariant siblings.
