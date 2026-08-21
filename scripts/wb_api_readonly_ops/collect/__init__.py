"""Full READ_ONLY collect pipeline (JSONL raw store + coverage metadata).

Product increment для `--mode collect` без contract: сохраняет полный
fetched volume без sample truncation; preflight path не затрагивается.
"""

from scripts.wb_api_readonly_ops.collect.runner import run_full_collect

__all__ = ["run_full_collect"]
