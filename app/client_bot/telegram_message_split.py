"""Split long plain text for Telegram ``sendMessage`` without breaking lines first."""

from __future__ import annotations

from app.client_bot.const import TELEGRAM_TEXT_MESSAGE_LIMIT


def split_telegram_plain_text(
    text: str,
    max_chars: int = TELEGRAM_TEXT_MESSAGE_LIMIT,
) -> list[str]:
    """Return segments each no longer than ``max_chars`` in Python ``len`` (code points).

    Telegram Bot API documents a 4096-character cap on message text. Packing prefers
    newline boundaries so formatted lines (e.g. ``✓ …`` per phrase) stay intact.
    If a single line exceeds ``max_chars``, it is split on code-point indices (safe
    for scalar values; extremely long lines are the only case where a chunk may end
    mid-line).
    """
    if max_chars < 1:
        msg = "max_chars must be >= 1"
        raise ValueError(msg)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    lines = text.split("\n")
    buf: list[str] = []
    buf_len = 0

    def flush_buf() -> None:
        nonlocal buf, buf_len
        if buf:
            chunks.append("\n".join(buf))
            buf = []
            buf_len = 0

    for line in lines:
        line_len = len(line)
        if line_len > max_chars:
            flush_buf()
            for i in range(0, line_len, max_chars):
                chunks.append(line[i : i + max_chars])
            continue

        sep_len = 0 if not buf else 1
        if buf_len + sep_len + line_len > max_chars:
            flush_buf()
            sep_len = 0

        buf.append(line)
        buf_len += sep_len + line_len

    flush_buf()
    return chunks
