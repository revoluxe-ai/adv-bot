"""Accept-gate: clean_dump / require-preflight-pass без Web PASS claim.

Spec: Clean dump without pass fails closed; Collect without accept cannot
claim clean dump readiness. Job MUST NOT declare READ_ONLY_PREFLIGHT_PASS.
"""

from __future__ import annotations

from pathlib import Path


class PreflightPassRequiredError(Exception):
    """Нет evidenced READ_ONLY_PREFLIGHT_PASS=YES — fail-closed до API."""


def read_preflight_pass_accepted(path: Path | None) -> bool:
    """True только если файл явно содержит READ_ONLY_PREFLIGHT_PASS=YES.

    Args:
        path: путь к accept-файлу; None → не принято.

    Returns:
        True при явном YES; иначе False.
    """
    if path is None:
        return False
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "READ_ONLY_PREFLIGHT_PASS" and value.strip() == "YES":
            return True
    return False


def require_preflight_pass_or_raise(path: Path | None) -> None:
    """Raise PreflightPassRequiredError если accept не доказан.

    Используется до любых WB API calls (0 calls при fail).
    """
    if not read_preflight_pass_accepted(path):
        raise PreflightPassRequiredError(
            "READ_ONLY_PREFLIGHT_PASS=YES required before clean_dump/collect "
            "under --require-preflight-pass; 0 API calls"
        )
