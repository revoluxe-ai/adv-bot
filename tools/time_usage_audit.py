import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATTERNS = {
    "datetime.now": r"datetime\.now",
    "datetime.utcnow": r"datetime\.utcnow",
    "datetime.today": r"datetime\.today",
    "date.today": r"date\.today",
    "time.time": r"time\.time",
    "time.monotonic": r"time\.monotonic",
    "time.perf_counter": r"time\.perf_counter",
}

def run_pattern(pattern: str) -> list[str]:
    result = subprocess.run(
        [
            "rg",
            "-n",
            "--no-heading",
            pattern,
            "--glob",
            "*.py",
            ".",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    output = result.stdout.strip()
    return output.splitlines() if output else []


def main() -> None:
    lines = ["# Time and Date Retrieval Usage Report", ""]
    for label, pattern in PATTERNS.items():
        matches = run_pattern(pattern)
        lines.append(f"## {label}")
        if matches:
            lines.append(f"Found {len(matches)} occurrence(s):")
            for match in matches:
                lines.append(f"- {match}")
        else:
            lines.append("No occurrences found.")
        lines.append("")

    report_path = REPO_ROOT / "TIME_USAGE_REPORT.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
