"""One-off: extract conversation text from ChatGPT share HTML capture."""
import json
import re
from pathlib import Path
from typing import Any

HTML = Path(
    r"C:/Users/vkita/Documents/Ссылка в markdown/_chatgpt_share_downloads/"
    r"CHATGPT_SHARE_6abd1faa_20260930_raw_capture/share_page_raw.html"
)
OUT_RAW = Path(__file__).with_name("chatgpt-6abd1faa-messages.txt")
OUT_META = Path(__file__).with_name("chatgpt-6abd1faa-parse-meta.json")


def load_dehydrated(html: str) -> Any:
    """Найти и распарсить крупный dehydrated JSON из RSC payload (escaped в HTML)."""
    markers = ['[{"_1":2', '[{\\"_1\\":2']
    start = -1
    escaped = False
    for m in markers:
        start = html.find(m)
        if start >= 0:
            escaped = m.startswith("[{\\")
            break
    if start < 0:
        raise ValueError("dehydrated payload not found")

    chunk = html[start:]
    depth = 0
    end = 0
    for i, ch in enumerate(chunk):
        prev = chunk[i - 1] if i else ""
        if ch == "[" and prev != "\\":
            depth += 1
        elif ch == "]" and prev != "\\":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end <= 0:
        raise ValueError("dehydrated payload end not found")

    raw = chunk[:end]
    if escaped:
        raw = bytes(raw, "utf-8").decode("unicode_escape")
    decoder = json.JSONDecoder()
    obj, _end = decoder.raw_decode(raw)
    return obj


def collect_strings(node: Any, out: list[str]) -> None:
    """Рекурсивно собрать все строки из JSON."""
    if isinstance(node, str):
        if len(node) >= 40:
            out.append(node)
        return
    if isinstance(node, dict):
        for v in node.values():
            collect_strings(v, out)
        return
    if isinstance(node, list):
        for v in node:
            collect_strings(v, out)


def is_message_like(text: str) -> bool:
    """Отфильтровать осмысленные фрагменты переписки / стратегии."""
    if len(text) < 120:
        return False
    if text.startswith("{") or text.startswith("[{"):
        return False
    keywords = (
        "adv-bot",
        "WB Sky",
        "OPSX",
        "worktree",
        "stage",
        "Tempo",
        "tempo",
        "перенос",
        "Project",
        "Owner",
        "change",
        "OpenSpec",
    )
    if any(k in text for k in keywords):
        return True
    return bool(re.search(r"[а-яА-ЯёЁ]{30}", text))


def main() -> None:
    html = HTML.read_text(encoding="utf-8", errors="replace")
    payload = load_dehydrated(html)
    all_strings: list[str] = []
    collect_strings(payload, all_strings)

    messages = sorted(
        {s for s in all_strings if is_message_like(s)},
        key=len,
        reverse=True,
    )

    with OUT_RAW.open("w", encoding="utf-8") as f:
        for i, m in enumerate(messages):
            f.write(f"\n\n===== MSG {i} len={len(m)} =====\n")
            f.write(m[:25000])
            if len(m) > 25000:
                f.write("\n...[truncated]...\n")

    meta = {
        "share_id": "6abd1faa-9cc4-83ed-8620-25ff5dc9065b",
        "title": "Стратегия доработки",
        "all_strings": len(all_strings),
        "message_like": len(messages),
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"all_strings={len(all_strings)} message_like={len(messages)} out={OUT_RAW}")


if __name__ == "__main__":
    main()
