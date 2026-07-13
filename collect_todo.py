from __future__ import annotations

import io
import json
import re
import tokenize
from pathlib import Path


ROOT = Path(".")

OUTPUT_MD = "code_todos.md"
OUTPUT_JSONL = "code_todos.jsonl"

TODO_MARKER_RE = re.compile(
    r"\b(TODO|FIXME|HACK|XXX|WORKLOG|BUG|DOTO)\b\s*:?",
    re.IGNORECASE,
)

CODE_SUFFIXES = {
    ".py",
    ".pyi",
    ".sql",
    ".sh",
    ".bash",
    ".ps1",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".dockerfile",
}

CODE_FILENAMES = {
    "Dockerfile",
    "Makefile",
}

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "docs",
    "docks",
    "DOTO",
}

EXCLUDE_FILES = {
    OUTPUT_MD,
    OUTPUT_JSONL,
    "todo_scan.txt",
    "todo_full_scan.md",
    "todo_full_scan.jsonl",
    "collect_worklog_candidates.py",
    "collect_code_todos.py",
}

MAX_FILE_SIZE = 2_000_000


COMMENT_PREFIX_RE = re.compile(r"^\s*(#|//|--|;)\s?(.*)$")


def should_skip(path: Path) -> bool:
    if path.name in EXCLUDE_FILES:
        return True

    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True

    if path.name not in CODE_FILENAMES and path.suffix.lower() not in CODE_SUFFIXES:
        return True

    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return True
    except OSError:
        return True

    return False


def read_text(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None

    if b"\x00" in raw:
        return None

    for encoding in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass

    return raw.decode("utf-8", errors="ignore")


def clean_comment_text(text: str) -> str:
    text = text.strip()

    for prefix in ("#", "//", "--", ";"):
        if text.startswith(prefix):
            return text[len(prefix):].strip()

    return text


def marker_name(text: str) -> str:
    match = TODO_MARKER_RE.search(text)
    if not match:
        return "UNKNOWN"
    return match.group(1).upper()


def add_item(
    items: list[dict],
    *,
    file: Path,
    start_line: int,
    end_line: int,
    source: str,
    text: str,
) -> None:
    text = text.strip()
    if not text:
        return

    if not TODO_MARKER_RE.search(text):
        return

    items.append(
        {
            "file": str(file).replace("\\", "/"),
            "start_line": start_line,
            "end_line": end_line,
            "source": source,
            "marker": marker_name(text),
            "text": text,
        }
    )


def collect_python_comments(path: Path, text: str) -> list[dict]:
    items: list[dict] = []

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except tokenize.TokenError:
        return collect_generic_comments(path, text)

    lines = text.splitlines()

    full_comment_block: list[tuple[int, str]] = []

    def flush_full_comment_block() -> None:
        nonlocal full_comment_block

        if not full_comment_block:
            return

        start_index = None

        for index, (_, comment_text) in enumerate(full_comment_block):
            if TODO_MARKER_RE.search(comment_text):
                start_index = index
                break

        if start_index is not None:
            useful_block = full_comment_block[start_index:]
            start_line = useful_block[0][0]
            end_line = useful_block[-1][0]
            block_text = "\n".join(comment for _, comment in useful_block)

            add_item(
                items,
                file=path,
                start_line=start_line,
                end_line=end_line,
                source="python_comment_block",
                text=block_text,
            )

        full_comment_block = []

    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            line_no = tok.start[0]
            col = tok.start[1]
            line = lines[line_no - 1] if 0 <= line_no - 1 < len(lines) else ""

            is_full_line_comment = not line[:col].strip()
            comment_text = clean_comment_text(tok.string)

            if is_full_line_comment:
                if full_comment_block and line_no != full_comment_block[-1][0] + 1:
                    flush_full_comment_block()

                full_comment_block.append((line_no, comment_text))
            else:
                flush_full_comment_block()

                add_item(
                    items,
                    file=path,
                    start_line=line_no,
                    end_line=line_no,
                    source="python_inline_comment",
                    text=comment_text,
                )
        else:
            flush_full_comment_block()

    flush_full_comment_block()
    return items


def collect_generic_comments(path: Path, text: str) -> list[dict]:
    items: list[dict] = []
    lines = text.splitlines()

    i = 0

    while i < len(lines):
        match = COMMENT_PREFIX_RE.match(lines[i])

        if not match:
            i += 1
            continue

        block: list[tuple[int, str]] = []

        while i < len(lines):
            current_match = COMMENT_PREFIX_RE.match(lines[i])

            if not current_match:
                break

            line_no = i + 1
            comment_text = current_match.group(2).rstrip()
            block.append((line_no, comment_text))
            i += 1

        start_index = None

        for index, (_, comment_text) in enumerate(block):
            if TODO_MARKER_RE.search(comment_text):
                start_index = index
                break

        if start_index is not None:
            useful_block = block[start_index:]
            start_line = useful_block[0][0]
            end_line = useful_block[-1][0]
            block_text = "\n".join(comment for _, comment in useful_block)

            add_item(
                items,
                file=path,
                start_line=start_line,
                end_line=end_line,
                source="comment_block",
                text=block_text,
            )

    return items


def dedupe(items: list[dict]) -> list[dict]:
    result: list[dict] = []
    seen: set[tuple] = set()

    for item in items:
        key = (
            item["file"],
            item["start_line"],
            item["end_line"],
            item["source"],
            item["text"],
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def scan(root: Path) -> list[dict]:
    items: list[dict] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if should_skip(path):
            continue

        text = read_text(path)
        if text is None:
            continue

        rel_path = path.relative_to(root)

        if path.suffix.lower() in {".py", ".pyi"}:
            items.extend(collect_python_comments(rel_path, text))
        else:
            items.extend(collect_generic_comments(rel_path, text))

    items = dedupe(items)
    items.sort(key=lambda x: (x["file"], x["start_line"], x["end_line"]))
    return items


def write_jsonl(items: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def write_markdown(items: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("# Code TODO scan\n\n")
        f.write(f"Total items: {len(items)}\n\n")

        for index, item in enumerate(items, start=1):
            f.write(
                f"## {index}. {item['file']}:{item['start_line']}-{item['end_line']}\n\n"
            )
            f.write(f"- marker: `{item['marker']}`\n")
            f.write(f"- source: `{item['source']}`\n\n")
            f.write("```text\n")
            f.write(item["text"].strip())
            f.write("\n```\n\n")


def main() -> None:
    root = ROOT.resolve()
    items = scan(root)

    md_path = root / OUTPUT_MD
    jsonl_path = root / OUTPUT_JSONL

    write_markdown(items, md_path)
    write_jsonl(items, jsonl_path)

    print(f"Collected: {len(items)} code TODO comments")
    print(f"Wrote: {md_path}")
    print(f"Wrote: {jsonl_path}")


if __name__ == "__main__":
    main()
