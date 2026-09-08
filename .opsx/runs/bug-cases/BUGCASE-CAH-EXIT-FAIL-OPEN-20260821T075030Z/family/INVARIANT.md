# INVARIANT

```text
INVARIANT_ID: INV/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/ROOT-001/EXIT-FAIL-CLOSED
```

## PLAIN_LANGUAGE_INVARIANT

Every public destructive Telegram EXIT callback must reject a missing or invalid actor before any write session is opened or external mutation is attempted.

## TECHNICAL_INVARIANT

For the public `disable_card_ab_hold` EXIT handler, actor extraction and validation must complete before entering `async with sm(read_only=False)`. Missing or invalid actor identity must terminate the handler without invoking `disable_card_ab_hold_in_session`, PostgreSQL mutation, or commit. The internal session seam may retain its explicit `telegram_user_id=None` behavior for trusted internal callers.

## SCOPE

The `card_ab_hold` Telegram EXIT callback path in `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/handlers.py`, including its actor boundary and write-session handoff. This invariant does not redefine the internal session seam or unrelated callback operations.

## ENTRY_CONDITIONS

An external Telegram update reaches the public `disable_card_ab_hold` EXIT handler with an absent, malformed, or otherwise invalid actor identity.

## REQUIRED_BEHAVIOR

Validate the actor before opening the write session; reject invalid input and perform no PostgreSQL mutation or commit.

## FORBIDDEN_BEHAVIOR

Do not interpret a missing actor as an ownership-check bypass, open a write session for that input, invoke the session seam, mutate PostgreSQL, or commit.

## KNOWN_WRITERS

- `disable_card_ab_hold` public Telegram EXIT handler
- `disable_card_ab_hold_in_session` internal session seam

## KNOWN_READERS

- Telegram callback actor extraction
- Card A/B hold ownership and disable flow
- PostgreSQL write-session boundary

## PROOF_FROM_ROOT_FINDING

Root finding ROOT-001 identified `_callback_actor_id` returning `None` while the session seam interpreted `None` as an ownership-check bypass. The root fix validates the actor at the public EXIT boundary before opening the write session while preserving the explicit internal seam behavior. Independent GREEN verification passed 4 frozen tests and 31 adjacent tests, confirmed the frozen test hash, and verified no PostgreSQL mutation or commit for missing or invalid actors.

## HUNT_SCOPE

Future family hunting is limited to public destructive EXIT callback paths that can receive absent or invalid actor identity and that open a write session or trigger an external mutation. Include only violations of the same fail-closed actor-before-write invariant; do not hunt unrelated authorization, callback, or internal-seam behavior.
