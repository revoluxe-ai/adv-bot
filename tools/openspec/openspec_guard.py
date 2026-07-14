"""Check OpenSpec and Cursor workflow artifact sizes deterministically."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import yaml


EXIT_OK = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
DEFAULT_CONFIG_PATH = Path(__file__).resolve().with_name("openspec_guard.yaml")
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
STATUS_GREEN = "GREEN"
STATUS_WARN = "WARN"
STATUS_FAIL = "FAIL"
VALID_BASELINE_STATUSES = frozenset({STATUS_WARN})


class GuardError(Exception):
    """Base exception for expected guard failures that should exit with code 2."""


class ConfigError(GuardError):
    """Raised when the guard YAML is missing, malformed, or semantically invalid."""


class ReadError(GuardError):
    """Raised when an included workflow artifact cannot be read as UTF-8 text."""


@dataclass(frozen=True)
class SizeLimit:
    """Character thresholds loaded from guard YAML for one artifact or scenario."""

    green_chars: int
    warn_chars: int
    fail_chars: int


@dataclass(frozen=True)
class ArtifactLimit:
    """A glob pattern and its loaded character thresholds."""

    pattern: str
    limit: SizeLimit


@dataclass(frozen=True)
class Baseline:
    """A known oversized baseline that may warn until it grows."""

    baseline_chars: int
    allowed_growth_chars: int
    status: str


@dataclass(frozen=True)
class IncludePattern:
    """A scenario include glob with optional required-file behavior."""

    pattern: str
    required: bool


@dataclass(frozen=True)
class Scenario:
    """A scenario bundle definition loaded from YAML."""

    name: str
    limit: SizeLimit
    reserved_chars: Mapping[str, int]
    includes: tuple[IncludePattern, ...]
    baseline: Baseline | None


@dataclass(frozen=True)
class GuardConfig:
    """Parsed guard configuration used by the checker."""

    chars_per_token: int
    fail_on_missing_includes: bool
    fail_on_broken_glob: bool
    artifact_limits: tuple[ArtifactLimit, ...]
    artifact_baselines: Mapping[str, Baseline]
    scenarios: Mapping[str, Scenario]


@dataclass(frozen=True)
class CheckResult:
    """Result row for a checked artifact or scenario bundle."""

    kind: str
    name: str
    status: str
    chars: int
    estimated_tokens: int
    reason: str
    file_count: int = 1
    reserved_chars: int = 0


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    """Return a YAML value as a mapping or raise a config error."""
    if not isinstance(value, Mapping):
        raise ConfigError(f"{label} must be a mapping.")
    return value


def _as_sequence(value: Any, label: str) -> Sequence[Any]:
    """Return a YAML value as a sequence or raise a config error."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ConfigError(f"{label} must be a list.")
    return value


def _positive_int(value: Any, label: str) -> int:
    """Read a positive integer config value."""
    if not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{label} must be a positive integer.")
    return value


def _non_negative_int(value: Any, label: str) -> int:
    """Read a non-negative integer config value."""
    if not isinstance(value, int) or value < 0:
        raise ConfigError(f"{label} must be a non-negative integer.")
    return value


def _bool_value(value: Any, label: str) -> bool:
    """Read a boolean config value."""
    if not isinstance(value, bool):
        raise ConfigError(f"{label} must be a boolean.")
    return value


def _normalize_rel_path(path: Path, repo_root: Path) -> str:
    """Return a deterministic repo-relative path with forward slashes."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _load_limit(data: Mapping[str, Any], label: str) -> SizeLimit:
    """Load and validate ordered character thresholds."""
    limit = SizeLimit(
        green_chars=_positive_int(data.get("green_chars"), f"{label}.green_chars"),
        warn_chars=_positive_int(data.get("warn_chars"), f"{label}.warn_chars"),
        fail_chars=_positive_int(data.get("fail_chars"), f"{label}.fail_chars"),
    )
    if not (limit.green_chars < limit.warn_chars < limit.fail_chars):
        raise ConfigError(
            f"{label} thresholds must satisfy green_chars < warn_chars < fail_chars."
        )
    return limit


def _load_baseline(data: Mapping[str, Any], label: str, default_growth: int) -> Baseline:
    """Load a baseline config entry for a known oversized item."""
    status = data.get("status", STATUS_WARN)
    if status not in VALID_BASELINE_STATUSES:
        allowed = ", ".join(sorted(VALID_BASELINE_STATUSES))
        raise ConfigError(f"{label}.status must be one of: {allowed}.")
    return Baseline(
        baseline_chars=_non_negative_int(data.get("baseline_chars"), f"{label}.baseline_chars"),
        allowed_growth_chars=_non_negative_int(
            data.get("allowed_growth_chars", default_growth),
            f"{label}.allowed_growth_chars",
        ),
        status=status,
    )


def _load_reserved_chars(value: Any, label: str) -> Mapping[str, int]:
    """Load reserved scenario budgets from a YAML mapping."""
    if value is None:
        return {}
    data = _as_mapping(value, label)
    reserved: dict[str, int] = {}
    for key, amount in data.items():
        reserved[str(key)] = _non_negative_int(amount, f"{label}.{key}")
    return reserved


def _load_include(value: Any, label: str) -> IncludePattern:
    """Load a scenario include pattern from a string or mapping."""
    if isinstance(value, str):
        return IncludePattern(pattern=value, required=False)
    data = _as_mapping(value, label)
    pattern = data.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        raise ConfigError(f"{label}.pattern must be a non-empty string.")
    required = data.get("required", False)
    return IncludePattern(pattern=pattern, required=_bool_value(required, f"{label}.required"))


def load_config(config_path: Path) -> GuardConfig:
    """Load and validate the guard YAML from disk."""
    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"guard config not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid guard YAML: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read guard config: {exc}") from exc

    root = _as_mapping(loaded, "guard config")
    token_estimate = _as_mapping(root.get("token_estimate"), "token_estimate")
    chars_per_token = _positive_int(
        token_estimate.get("chars_per_token"), "token_estimate.chars_per_token"
    )

    defaults = _as_mapping(root.get("defaults", {}), "defaults")
    fail_on_missing = _bool_value(
        defaults.get("fail_on_missing_includes", False),
        "defaults.fail_on_missing_includes",
    )
    fail_on_broken_glob = _bool_value(
        defaults.get("fail_on_broken_glob", False),
        "defaults.fail_on_broken_glob",
    )
    default_growth = _non_negative_int(
        defaults.get("baseline_allowed_growth_chars", 0),
        "defaults.baseline_allowed_growth_chars",
    )

    artifact_limits: list[ArtifactLimit] = []
    for index, item in enumerate(_as_sequence(root.get("artifact_limits"), "artifact_limits")):
        data = _as_mapping(item, f"artifact_limits[{index}]")
        pattern = data.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise ConfigError(f"artifact_limits[{index}].pattern must be a non-empty string.")
        artifact_limits.append(
            ArtifactLimit(
                pattern=pattern,
                limit=_load_limit(data, f"artifact_limits[{index}]"),
            )
        )

    artifact_baselines: dict[str, Baseline] = {}
    for rel_path, item in _as_mapping(root.get("artifact_baselines", {}), "artifact_baselines").items():
        artifact_baselines[str(rel_path)] = _load_baseline(
            _as_mapping(item, f"artifact_baselines.{rel_path}"),
            f"artifact_baselines.{rel_path}",
            default_growth,
        )

    scenario_defaults = _as_mapping(root.get("scenario_defaults", {}), "scenario_defaults")
    default_scenario_limit = _load_limit(scenario_defaults, "scenario_defaults")
    default_reserved = _load_reserved_chars(
        scenario_defaults.get("reserved_chars"), "scenario_defaults.reserved_chars"
    )

    scenarios: dict[str, Scenario] = {}
    for name, item in _as_mapping(root.get("scenarios"), "scenarios").items():
        data = _as_mapping(item, f"scenarios.{name}")
        includes = tuple(
            _load_include(include, f"scenarios.{name}.includes[{index}]")
            for index, include in enumerate(_as_sequence(data.get("includes"), f"scenarios.{name}.includes"))
        )
        if not includes:
            raise ConfigError(f"scenarios.{name}.includes must not be empty.")

        limit = (
            _load_limit(data, f"scenarios.{name}")
            if all(key in data for key in ("green_chars", "warn_chars", "fail_chars"))
            else default_scenario_limit
        )
        reserved = dict(default_reserved)
        reserved.update(_load_reserved_chars(data.get("reserved_chars"), f"scenarios.{name}.reserved_chars"))
        baseline = (
            _load_baseline(data, f"scenarios.{name}", default_growth)
            if "baseline_chars" in data
            else None
        )
        scenarios[str(name)] = Scenario(
            name=str(name),
            limit=limit,
            reserved_chars=reserved,
            includes=includes,
            baseline=baseline,
        )

    return GuardConfig(
        chars_per_token=chars_per_token,
        fail_on_missing_includes=fail_on_missing,
        fail_on_broken_glob=fail_on_broken_glob,
        artifact_limits=tuple(artifact_limits),
        artifact_baselines=artifact_baselines,
        scenarios=scenarios,
    )


def estimate_tokens(chars: int, chars_per_token: int) -> int:
    """Estimate token count as a deterministic ceiling division."""
    return (chars + chars_per_token - 1) // chars_per_token


def read_chars(path: Path) -> int:
    """Count text characters in a UTF-8 artifact."""
    try:
        return len(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ReadError(f"cannot decode {path} as UTF-8: {exc}") from exc
    except OSError as exc:
        raise ReadError(f"cannot read {path}: {exc}") from exc


def _expand_pattern(
    repo_root: Path,
    pattern: str,
    *,
    fail_on_broken_glob: bool,
) -> tuple[Path, ...]:
    """Expand a repo-relative glob pattern into sorted files."""
    try:
        matches = repo_root.glob(pattern)
        return tuple(sorted(path.resolve() for path in matches if path.is_file()))
    except (OSError, ValueError) as exc:
        if fail_on_broken_glob:
            raise ConfigError(f"broken glob {pattern!r}: {exc}") from exc
        return ()


def _evaluate_status(chars: int, limit: SizeLimit, baseline: Baseline | None) -> tuple[str, str]:
    """Evaluate a character count against thresholds and optional baseline."""
    if baseline is not None:
        max_baseline_chars = baseline.baseline_chars + baseline.allowed_growth_chars
        if chars > max_baseline_chars:
            return (
                STATUS_FAIL,
                f"grew over baseline {baseline.baseline_chars} by {chars - baseline.baseline_chars} chars",
            )

    if chars <= limit.green_chars:
        return STATUS_GREEN, f"within green limit {limit.green_chars}"

    if chars < limit.fail_chars:
        return STATUS_WARN, f"over green limit {limit.green_chars}, below fail limit {limit.fail_chars}"

    if baseline is not None:
        return baseline.status, f"known baseline {baseline.baseline_chars} over fail limit {limit.fail_chars}"

    return STATUS_FAIL, f"over fail limit {limit.fail_chars}"


def _result_for_artifact(
    path: Path,
    repo_root: Path,
    config: GuardConfig,
    artifact_limit: ArtifactLimit,
) -> CheckResult:
    """Build one artifact check result."""
    rel_path = _normalize_rel_path(path, repo_root)
    chars = read_chars(path)
    status, reason = _evaluate_status(
        chars,
        artifact_limit.limit,
        config.artifact_baselines.get(rel_path),
    )
    return CheckResult(
        kind="artifact",
        name=rel_path,
        status=status,
        chars=chars,
        estimated_tokens=estimate_tokens(chars, config.chars_per_token),
        reason=f"{reason}; pattern={artifact_limit.pattern}",
    )


def check_artifacts(config: GuardConfig, repo_root: Path) -> list[CheckResult]:
    """Check all configured artifact limits."""
    results: list[CheckResult] = []
    seen: set[Path] = set()
    for artifact_limit in config.artifact_limits:
        paths = _expand_pattern(
            repo_root,
            artifact_limit.pattern,
            fail_on_broken_glob=config.fail_on_broken_glob,
        )
        for path in paths:
            if path in seen:
                continue
            seen.add(path)
            results.append(_result_for_artifact(path, repo_root, config, artifact_limit))
    return results


def check_file(config: GuardConfig, repo_root: Path, file_path: Path) -> list[CheckResult]:
    """Check one file against the first configured artifact pattern that matches it."""
    target = (repo_root / file_path).resolve() if not file_path.is_absolute() else file_path.resolve()
    if not target.is_file():
        raise ReadError(f"file not found: {file_path}")

    for artifact_limit in config.artifact_limits:
        matches = _expand_pattern(
            repo_root,
            artifact_limit.pattern,
            fail_on_broken_glob=config.fail_on_broken_glob,
        )
        if target in matches:
            return [_result_for_artifact(target, repo_root, config, artifact_limit)]

    rel_path = _normalize_rel_path(target, repo_root)
    raise ConfigError(f"file is outside configured artifact limits: {rel_path}")


def _unique_included_files(config: GuardConfig, repo_root: Path, scenario: Scenario) -> tuple[Path, ...]:
    """Expand scenario includes and dedupe matched files by resolved path."""
    files: dict[Path, None] = {}
    for include in scenario.includes:
        paths = _expand_pattern(
            repo_root,
            include.pattern,
            fail_on_broken_glob=config.fail_on_broken_glob,
        )
        if not paths and (include.required or config.fail_on_missing_includes):
            raise ReadError(f"scenario {scenario.name} include matched no files: {include.pattern}")
        for path in paths:
            files[path] = None
    return tuple(sorted(files))


def check_scenario(config: GuardConfig, repo_root: Path, name: str) -> CheckResult:
    """Check one configured scenario bundle."""
    try:
        scenario = config.scenarios[name]
    except KeyError as exc:
        available = ", ".join(sorted(config.scenarios))
        raise ConfigError(f"unknown scenario {name!r}; available scenarios: {available}") from exc

    files = _unique_included_files(config, repo_root, scenario)
    file_chars = sum(read_chars(path) for path in files)
    reserved_total = sum(scenario.reserved_chars.values())
    chars = file_chars + reserved_total
    status, reason = _evaluate_status(chars, scenario.limit, scenario.baseline)
    return CheckResult(
        kind="scenario",
        name=name,
        status=status,
        chars=chars,
        estimated_tokens=estimate_tokens(chars, config.chars_per_token),
        reason=reason,
        file_count=len(files),
        reserved_chars=reserved_total,
    )


def check_scenarios(config: GuardConfig, repo_root: Path) -> list[CheckResult]:
    """Check every configured scenario bundle."""
    return [check_scenario(config, repo_root, name) for name in sorted(config.scenarios)]


def format_results(results: Iterable[CheckResult]) -> str:
    """Render check results as deterministic text."""
    lines: list[str] = []
    for result in results:
        if result.kind == "scenario":
            lines.append(
                f"{result.status:5s} {result.kind:8s} chars={result.chars} "
                f"est_tokens={result.estimated_tokens} files={result.file_count} "
                f"reserved_chars={result.reserved_chars} name={result.name} "
                f"reason={result.reason}"
            )
            continue
        lines.append(
            f"{result.status:5s} {result.kind:8s} chars={result.chars} "
            f"est_tokens={result.estimated_tokens} path={result.name} "
            f"reason={result.reason}"
        )
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse CLI arguments for the standalone guard."""
    parser = argparse.ArgumentParser(description="Check OpenSpec/Cursor artifact sizes.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero for FAIL results.")
    parser.add_argument("--scenario", help="Check a single named scenario bundle.")
    parser.add_argument("--file", type=Path, help="Check a single artifact file.")
    args = parser.parse_args(argv)
    if args.scenario and args.file:
        parser.error("--scenario and --file are mutually exclusive")
    return args


def run(
    argv: Sequence[str] | None = None,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    repo_root: Path = DEFAULT_REPO_ROOT,
) -> int:
    """Run the guard and return a process exit code."""
    try:
        args = _parse_args(argv)
        config = load_config(config_path)
        if args.scenario:
            results = [check_scenario(config, repo_root, args.scenario)]
        elif args.file:
            results = check_file(config, repo_root, args.file)
        else:
            results = [*check_artifacts(config, repo_root), *check_scenarios(config, repo_root)]

        output = format_results(results)
        if output:
            print(output)

        has_fail = any(result.status == STATUS_FAIL for result in results)
        return EXIT_FAIL if args.strict and has_fail else EXIT_OK
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else EXIT_ERROR
        return code if code != 0 else EXIT_OK
    except GuardError as exc:
        print(f"OpenSpec guard error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:  # pragma: no cover - defensive CLI boundary.
        print(f"OpenSpec guard implementation error: {exc}", file=sys.stderr)
        return EXIT_ERROR


def main() -> int:
    """Run the standalone CLI with process arguments."""
    return run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
