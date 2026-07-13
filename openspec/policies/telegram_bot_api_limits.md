# Telegram Bot API Limits Policy

## Rule

Any change that creates or modifies Telegram bot messages, captions, callback answers, inline keyboards, invoices, polls, or checklist text MUST include automated tests for Telegram payload limits.

Tests MUST validate the rendered payload with worst-case dynamic data, not only static template length.

## Core limits

- sendMessage.text: 4096 characters after HTML/Markdown/entity parsing.
- InputTextMessageContent.message_text: 4096 characters.
- media caption: 1024 characters after entity parsing.
- story caption: 2048 characters.
- poll question: 300 characters.
- poll option: 100 characters.
- poll explanation: 200 characters, max 2 line feeds.
- poll description: 1024 characters.
- answerCallbackQuery.text: 200 characters.
- InlineKeyboardButton.callback_data: 1–64 bytes.
- inline query text from user: 256 characters.
- checklist title: 255 characters.
- checklist task text: 100 characters.
- invoice title: 32 characters.
- invoice description: 255 characters.
- invoice payload: 128 bytes.

## Required worst-case data

Message tests MUST render with max realistic placeholders:

- long shop name;
- long campaign name;
- long card / nm title;
- long cluster / keyword names;
- max numeric values: adv_id, nm_id, money, percent, CTR, CPO, DRR;
- multiple rows/items where the UI can list campaigns/cards/keywords;
- Cyrillic text;
- emoji and multibyte characters;
- HTML escaping cases: `<`, `>`, `&`, quotes;
- disabled/paid/free state labels;
- error reasons and fallback text.

## Required assertions

For every changed Telegram UI surface:

- assert rendered text/caption/callback answer length is within Telegram limit;
- assert HTML/Markdown parse mode is valid or escaped;
- assert no raw technical placeholders leak to user;
- assert inline button callback_data is measured in UTF-8 bytes;
- assert keyboard buttons still exist and point to expected callbacks;
- assert long dynamic data is truncated or split intentionally.
