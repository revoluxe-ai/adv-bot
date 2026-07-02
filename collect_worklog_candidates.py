from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


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
}

EXCLUDE_SUFFIXES = {
    ".pyc", ".pyo", ".pyd",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".pdf", ".zip", ".gz", ".tar", ".rar", ".7z",
    ".sqlite", ".db",
    ".mp4", ".mov", ".avi",
}

MAX_FILE_SIZE = 2_000_000

MARKER_RE = re.compile(
    r"\b(TODO|FIXME|HACK|XXX|WORKLOG|BUG)\b\s*:?",
    re.IGNORECASE,
)

TASK_HEURISTIC_RE = re.compile(
    r"("
    r"надо|нужно|сделать|доделать|исправить|починить|переделать|"
    r"разобраться|проверить|добавить|внедрить|убрать|выпилить|"
    r"оптимизировать|ускорить|вынести|перенести|почистить|"
    r"ошибк|баг|упал|упало|падает|рантайм|runtime|прод|production|"
    r"временно|заглушк|костыл|срочно|deprecated|depricated|"
    r"fallback|фоллбек|timeout|таймаут|завис|hang"
    r")",
    re.IGNORECASE,
)

INVARIANT_RE = re.compile(
    r"("
    r"инвариант|должен|должна|должно|нельзя|обязательно|важно|"
    r"не должно|не должен|must|should|never|required|forbidden"
    r")",
    re.IGNORECASE,
)

FULL_COMMENT_RE = re.compile(r"^\s*(#|//|--|;)\s?(.*)$")
INLINE_COMMENT_RE = re.compile(r"(.+?)(#|//)\s+(.*)$")


def is_excluded(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    if path.name in {"todo_scan.txt", "todo_full_scan.md", "todo_full_scan.jsonl"}:
        return True
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return True
    except OSError:
        return True
    return False


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if b"\x00" in data:
        return None

    for encoding in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="ignore")


def classify(text: str) -> tuple[bool, bool, bool]:
    has_marker = bool(MARKER_RE.search(text))
    has_task = bool(TASK_HEURISTIC_RE.search(text))
    has_invariant = bool(INVARIANT_RE.search(text))
    return has_marker, has_task, has_invariant


def kind_from_flags(has_marker: bool, has_task: bool, has_invariant: bool) -> str:
    kinds = []
    if has_marker:
        kinds.append("marker")
    if has_task:
        kinds.append("heuristic_task")
    if has_invariant:
        kinds.append("invariant")
    return "+".join(kinds) if kinds else "unknown"


def clean_block(lines: list[str]) -> str:
    cleaned = []
    for line in lines:
        m = FULL_COMMENT_RE.match(line)
        if m:
            cleaned.append(m.group(2).rstrip())
        else:
            cleaned.append(line.rstrip())
    return "\n".join(cleaned).strip()


def collect_line_comment_blocks(path: Path, text: str) -> list[dict]:
    results = []
    lines = text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        if FULL_COMMENT_RE.match(line):
            start = i + 1
            block = []

            while i < len(lines) and FULL_COMMENT_RE.match(lines[i]):
                block.append(lines[i])
                i += 1

            block_text = clean_block(block)
            has_marker, has_task, has_invariant = classify(block_text)

            if has_marker or has_task or has_invariant:
                results.append({
                    "file": str(path),
                    "start_line": start,
                    "end_line": start + len(block) - 1,
                    "kind": kind_from_flags(has_marker, has_task, has_invariant),
                    "source": "comment_block",
                    "text": block_text,
                })
            continue

        inline = INLINE_COMMENT_RE.match(line)
        if inline:
            comment_text = inline.group(3).strip()
            has_marker, has_task, has_invariant = classify(comment_text)

            if has_marker or has_task or has_invariant:
                results.append({
                    "file": str(path),
                    "start_line": i + 1,
                    "end_line": i + 1,
                    "kind": kind_from_flags(has_marker, has_task, has_invariant),
                    "source": "inline_comment",
                    "text": comment_text,
                })

        i += 1

    return results


def collect_python_docstrings(path: Path, text: str) -> list[dict]:
    results = []

    if path.suffix != ".py":
        return results

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return results

    for node in ast.walk(tree):
        value = None

        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            value = ast.get_docstring(node, clean=False)

            if value:
                start_line = getattr(node, "lineno", 1)
                end_line = getattr(node, "end_lineno", start_line)
                has_marker, has_task, has_invariant = classify(value)

                if has_marker or has_task or has_invariant:
                    results.append({
                        "file": str(path),
                        "start_line": start_line,
                        "end_line": end_line,
                        "kind": kind_from_flags(has_marker, has_task, has_invariant),
                        "source": "docstring",
                        "text": value.strip(),
                    })

    return results


def collect_markdown_paragraphs(path: Path, text: str) -> list[dict]:
    results = []

    if path.suffix.lower() not in {".md", ".txt", ".rst"}:
        return results

    lines = text.splitlines()
    i = 0

    while i < len(lines):
        while i < len(lines) and not lines[i].strip():
            i += 1

        if i >= len(lines):
            break

        start = i + 1
        block = []

        while i < len(lines) and lines[i].strip():
            block.append(lines[i])
            i += 1

        block_text = "\n".join(block).strip()
        has_marker, has_task, has_invariant = classify(block_text)

        if has_marker or has_task or has_invariant:
            results.append({
                "file": str(path),
                "start_line": start,
                "end_line": start + len(block) - 1,
                "kind": kind_from_flags(has_marker, has_task, has_invariant),
                "source": "text_paragraph",
                "text": block_text,
            })

    return results


def dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []

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
        unique.append(item)

    return unique


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    root = root.resolve()

    items: list[dict] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if is_excluded(path):
            continue

        text = read_text(path)
        if text is None:
            continue

        rel_path = path.relative_to(root)

        items.extend(collect_line_comment_blocks(rel_path, text))
        items.extend(collect_python_docstrings(rel_path, text))
        items.extend(collect_markdown_paragraphs(rel_path, text))

    items = dedupe(items)
    items.sort(key=lambda x: (x["file"], x["start_line"], x["source"]))

    jsonl_path = root / "todo_full_scan.jsonl"
    md_path = root / "todo_full_scan.md"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# Full TODO / task / invariant scan\n\n")
        f.write(f"Total items: {len(items)}\n\n")

        for idx, item in enumerate(items, start=1):
            f.write(f"## {idx}. {item['file']}:{item['start_line']}-{item['end_line']}\n\n")
            f.write(f"- kind: `{item['kind']}`\n")
            f.write(f"- source: `{item['source']}`\n\n")
            f.write("```text\n")
            f.write(item["text"].strip())
            f.write("\n```\n\n")

    print(f"Collected {len(items)} candidates")
    print(f"Wrote: {jsonl_path}")
    print(f"Wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
