import os
import re

EXCLUDE_DIRS = {
    ".venv", "__pycache__", ".git", ".idea",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", ".tox", ".cache"
}


COMMENT_PATTERN = re.compile(
    r"(?m)^[ \t]*#\s*TODO[:\s]*(.+)$", re.IGNORECASE
)

STRING_PATTERN = re.compile(
    r"""(?ix)
    (['"]{1,3})                # кавычки
    ([^'"]*?\bTODO\b[^'"]*?)   
    \1
    """,
    re.DOTALL,
)

def clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[:\-–\s]+", "", text)
    text = re.sub(r"[\s\-–]+$", "", text)
    return text


def collect_todos(root="."):
    todos = []
    seen = set()  # для устранения дублей

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            path = os.path.join(dirpath, filename)
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # --- Комментарии ---
                for m in COMMENT_PATTERN.finditer(content):
                    text = clean_text(m.group(1))
                    if not text or (path, text) in seen:
                        continue
                    seen.add((path, text))
                    line = content.count("\n", 0, m.start()) + 1
                    todos.append({
                        "file": path,
                        "line": line,
                        "text": text,
                        "context": "comment",
                    })

                # --- Внутри строк ---
                for m in STRING_PATTERN.finditer(content):
                    text = clean_text(m.group(2))
                    if not text or (path, text) in seen:
                        continue
                    seen.add((path, text))
                    line = content.count("\n", 0, m.start()) + 1
                    todos.append({
                        "file": path,
                        "line": line,
                        "text": text,
                        "context": "string",
                    })

            except Exception as e:
                print(f"Ошибка при чтении {path}: {e}")

    return todos


if __name__ == "__main__":
    todos = collect_todos(".")
    print(f"Всего найдено {len(todos)} TODO:\n")
    for t in sorted(todos, key=lambda x: (x["file"], x["line"])):
        rel_path = os.path.relpath(t["file"], ".")
        prefix = "[#]" if t["context"] == "comment" else "[str]"
        print(f".\\{rel_path}:{t['line']} {prefix} {t['text']}")
