from __future__ import annotations

from opsx_conflict.runtime import detect_logical_conflict_candidates


def test_logical_conflict_without_markers_is_detected() -> None:
    source = {
        "api.py": """
def calculate_total(items):
    return {"total": sum(items), "currency": "RUB"}
""",
    }
    target = {
        "consumer.py": """
from api import calculate_total

def render(items):
    value = calculate_total(items)
    return f"Total: {value:.2f}"
""",
    }
    found = detect_logical_conflict_candidates(source, target, textual_conflict_paths=[])
    assert found
    assert found[0]["source_path"] == "api.py"
    assert found[0]["target_path"] == "consumer.py"
    assert "calculate_total" in found[0]["source_defs_target_calls"]
