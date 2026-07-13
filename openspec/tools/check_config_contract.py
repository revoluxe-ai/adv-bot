"""Validate openspec/config.yaml against the supported OpenSpec config keys."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"
ALLOWED_TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "context",
        "rules",
        "references",
        "store",
    }
)


def _load_config(path: Path) -> dict[Any, Any] | None:
    """Read the YAML config as UTF-8 and require a top-level mapping."""
    try:
        with path.open("r", encoding="utf-8") as config_file:
            loaded = yaml.safe_load(config_file)
    except FileNotFoundError:
        print(f"OpenSpec config contract check failed: {path} not found.", file=sys.stderr)
        return None
    except yaml.YAMLError as exc:
        print(f"OpenSpec config contract check failed: YAML parse error: {exc}", file=sys.stderr)
        return None

    if loaded is None:
        return {}

    if not isinstance(loaded, dict):
        print(
            "OpenSpec config contract check failed: "
            "openspec/config.yaml top-level value must be a mapping.",
            file=sys.stderr,
        )
        return None

    return loaded


def _sorted_key_names(keys: list[Any]) -> list[str]:
    """Return deterministic string names for YAML mapping keys."""
    return sorted(str(key) for key in keys)


def _unknown_top_level_keys(config: dict[Any, Any]) -> list[str]:
    """Return top-level keys unsupported by OpenSpec core config parsing."""
    unknown_keys = [key for key in config if key not in ALLOWED_TOP_LEVEL_KEYS]
    return _sorted_key_names(unknown_keys)


def _rules_contract_errors(config: dict[Any, Any]) -> list[str]:
    """Validate rules as a mapping of artifact names to string lists."""
    if "rules" not in config:
        return []

    rules = config["rules"]
    if not isinstance(rules, dict):
        return ["rules must be a mapping."]

    errors: list[str] = []
    for artifact, values in rules.items():
        artifact_name = str(artifact)
        if not isinstance(values, list):
            errors.append(f"rules.{artifact_name} must be a list of strings.")
            continue

        for index, value in enumerate(values):
            if not isinstance(value, str):
                errors.append(f"rules.{artifact_name}[{index}] must be a string.")

    return errors


def main() -> int:
    """Run the config contract validation and return a process exit code."""
    config = _load_config(CONFIG_PATH)
    if config is None:
        return 1

    unknown_keys = _unknown_top_level_keys(config)
    rules_errors = _rules_contract_errors(config)

    if not unknown_keys and not rules_errors:
        print("OpenSpec config contract check passed.")
        return 0

    print("OpenSpec config contract check failed.", file=sys.stderr)

    if unknown_keys:
        print("Unknown top-level keys in openspec/config.yaml:", file=sys.stderr)
        for key in unknown_keys:
            print(f"- {key}", file=sys.stderr)
        allowed = ", ".join(sorted(ALLOWED_TOP_LEVEL_KEYS))
        print(f"Allowed top-level keys: {allowed}", file=sys.stderr)

    if rules_errors:
        print("Rules contract violations:", file=sys.stderr)
        for error in rules_errors:
            print(f"- {error}", file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
