"""
MVP CONTROL helper: provenance-bound acquire (stub until CONTROL image lands).

Не исполняет RELEASE image. Ожидаемые env:
  RELEASE_ID, RELEASE_PLATFORM_MANIFEST_DIGEST, DATABASE_URL,
  EXPECTED_TARGET_REVISION, TARGET_PLATFORM.
"""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    """Печатает PRECONDITION_FAILED пока registry-extract/attestation не подключены."""
    required = [
        "RELEASE_ID",
        "RELEASE_PLATFORM_MANIFEST_DIGEST",
        "DATABASE_URL",
        "EXPECTED_TARGET_REVISION",
    ]
    missing = [k for k in required if not os.environ.get(k, "").strip()]
    payload = {
        "outcome": "PRECONDITION_FAILED",
        "detail": (
            "CONTROL acquire stub: wire attestation verify or registry-layer "
            "extract before PROD_AUTOMATION_ENABLEMENT_ALLOWED=YES"
        ),
        "missing_env": missing,
        "target_platform": os.environ.get("TARGET_PLATFORM", "linux/amd64"),
        "release_id": os.environ.get("RELEASE_ID", ""),
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return 2


if __name__ == "__main__":
    sys.exit(main())
