## 1. <!-- Task Group Name -->

- [ ] 1.1 <!-- Task description -->
- [ ] 1.2 <!-- Task description -->

## 2. <!-- Task Group Name -->

- [ ] 2.1 <!-- Task description -->
- [ ] 2.2 <!-- Task description -->

## Telegram UI / Message Safety

Required if this change creates or modifies Telegram bot UI text, captions, callback answers, inline keyboards, polls, invoices, or checklist text.

- [ ] Identify every changed Telegram payload surface.
- [ ] Add/update tests with worst-case dynamic placeholder data.
- [ ] Assert Telegram Bot API limits from `openspec/policies/telegram_bot_api_limits.md`.
- [ ] Assert valid parse_mode / escaping.
- [ ] Assert callback_data length in UTF-8 bytes.
- [ ] Assert no raw technical text leaks to user.
