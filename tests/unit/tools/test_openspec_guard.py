"""Unit tests for the standalone OpenSpec/Cursor artifact size guard."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest
import yaml

pytestmark = pytest.mark.unit


def _load_guard_module():
    """Загружает guard script напрямую, чтобы тестировать standalone tooling."""
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "openspec" / "openspec_guard.py"
    spec = importlib.util.spec_from_file_location("openspec_guard", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_config(root: Path, data: dict) -> Path:
    """Пишет test-only YAML config для проверки parser и CLI behavior."""
    config_path = root / "tools" / "openspec" / "openspec_guard.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return config_path


def _write_openspec_config(root: Path, data: dict) -> Path:
    """Пишет test-only openspec/config.yaml для проверки section guard."""
    config_path = root / "openspec" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return config_path


def _base_config() -> dict:
    """Возвращает минимальный guard config, пригодный для большинства tests."""
    return {
        "token_estimate": {"chars_per_token": 3},
        "defaults": {
            "fail_on_missing_includes": False,
            "fail_on_broken_glob": False,
            "baseline_allowed_growth_chars": 0,
        },
        "artifact_limits": [
            {
                "pattern": "workflow/*.md",
                "green_chars": 5,
                "warn_chars": 10,
                "fail_chars": 11,
            }
        ],
        "artifact_baselines": {},
        "scenario_defaults": {
            "green_chars": 10,
            "warn_chars": 20,
            "fail_chars": 21,
            "reserved_chars": {},
        },
        "scenarios": {
            "sample": {
                "includes": ["workflow/*.md"],
            }
        },
    }


def _config_section_guard_config() -> dict:
    """Возвращает guard config с лимитами для openspec/config.yaml sections."""
    config_data = _base_config()
    config_data["artifact_limits"] = [
        {
            "pattern": "openspec/config.yaml",
            "green_chars": 1000,
            "warn_chars": 2000,
            "fail_chars": 2001,
        }
    ]
    config_data["config_section_limits"] = {
        "context": {
            "green_chars": 5,
            "warn_chars": 9,
            "fail_chars": 10,
        },
        "rules": {
            "green_chars": 10,
            "warn_chars": 20,
            "fail_chars": 21,
        },
        "rules.*": {
            "green_chars": 5,
            "warn_chars": 9,
            "fail_chars": 10,
        },
    }
    return config_data


def test_load_config_parses_valid_yaml(tmp_path: Path) -> None:
    """Проверяет, что valid YAML превращается в typed guard config."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _base_config())

    config = mod.load_config(config_path)

    assert config.chars_per_token == 3
    assert config.artifact_limits[0].pattern == "workflow/*.md"
    assert "sample" in config.scenarios


def test_invalid_yaml_exits_2(tmp_path: Path) -> None:
    """Фиксирует exit code 2 для YAML, который нельзя разобрать."""
    mod = _load_guard_module()
    config_path = tmp_path / "tools" / "openspec" / "openspec_guard.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("token_estimate: [", encoding="utf-8")

    assert mod.run(["--strict"], config_path=config_path, repo_root=tmp_path) == 2


def test_invalid_openspec_config_yaml_exits_2(tmp_path: Path) -> None:
    """Фиксирует exit code 2 для битого openspec/config.yaml."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _config_section_guard_config())
    target = tmp_path / "openspec" / "config.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("context: [", encoding="utf-8")

    assert (
        mod.run(
            ["--file", "openspec/config.yaml", "--strict"],
            config_path=config_path,
            repo_root=tmp_path,
        )
        == 2
    )


def test_counts_utf8_russian_chars_and_estimates_tokens(tmp_path: Path) -> None:
    """Доказывает chars count для русского UTF-8 и ceil(chars / 3)."""
    mod = _load_guard_module()
    config_data = _base_config()
    config_data["artifact_limits"][0]["green_chars"] = 20
    config_data["artifact_limits"][0]["warn_chars"] = 30
    config_data["artifact_limits"][0]["fail_chars"] = 31
    config_path = _write_config(tmp_path, config_data)
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    target = workflow_dir / "ru.md"
    target.write_text("привет", encoding="utf-8")

    config = mod.load_config(config_path)
    result = mod.check_file(config, tmp_path, Path("workflow/ru.md"))[0]

    assert result.chars == 6
    assert result.estimated_tokens == 2


def test_file_green_warn_and_fail_statuses(tmp_path: Path) -> None:
    """Проверяет individual artifact limits для GREEN, WARN и FAIL."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _base_config())
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    (workflow_dir / "green.md").write_text("abcde", encoding="utf-8")
    (workflow_dir / "warn.md").write_text("abcdef", encoding="utf-8")
    (workflow_dir / "fail.md").write_text("abcdefghijk", encoding="utf-8")
    config = mod.load_config(config_path)

    statuses = {
        path.name: mod.check_file(config, tmp_path, path.relative_to(tmp_path))[0].status
        for path in sorted(workflow_dir.glob("*.md"))
    }

    assert statuses == {
        "green.md": "GREEN",
        "warn.md": "WARN",
        "fail.md": "FAIL",
    }


def test_strict_fail_returns_exit_code_1(tmp_path: Path) -> None:
    """Фиксирует CLI contract: FAIL limits возвращают exit code 1."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _base_config())
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    (workflow_dir / "fail.md").write_text("abcdefghijk", encoding="utf-8")

    assert mod.run(["--file", "workflow/fail.md", "--strict"], config_path=config_path, repo_root=tmp_path) == 1


def test_non_strict_fail_returns_exit_code_0(tmp_path: Path) -> None:
    """Фиксирует, что FAIL не ломает запуск без explicit --strict."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _base_config())
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    (workflow_dir / "fail.md").write_text("abcdefghijk", encoding="utf-8")

    assert mod.run(["--file", "workflow/fail.md"], config_path=config_path, repo_root=tmp_path) == 0


def test_warn_does_not_fail_exit_code(tmp_path: Path) -> None:
    """Фиксирует, что WARN остается exit code 0 даже в strict mode."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _base_config())
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    (workflow_dir / "warn.md").write_text("abcdef", encoding="utf-8")

    assert mod.run(["--file", "workflow/warn.md", "--strict"], config_path=config_path, repo_root=tmp_path) == 0


def test_scenario_bundle_sums_unique_matched_files(tmp_path: Path) -> None:
    """Доказывает scenario bundle sum и dedupe overlapping globs по resolved path."""
    mod = _load_guard_module()
    config_data = _base_config()
    config_data["scenario_defaults"] = {
        "green_chars": 20,
        "warn_chars": 30,
        "fail_chars": 31,
        "reserved_chars": {"output": 2},
    }
    config_data["scenarios"]["sample"]["includes"] = ["workflow/*.md", "workflow/a.md"]
    config_path = _write_config(tmp_path, config_data)
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    (workflow_dir / "a.md").write_text("12345", encoding="utf-8")
    (workflow_dir / "b.md").write_text("6789", encoding="utf-8")
    config = mod.load_config(config_path)

    result = mod.check_scenario(config, tmp_path, "sample")

    assert result.file_count == 2
    assert result.reserved_chars == 2
    assert result.chars == 11


def test_missing_optional_glob_does_not_fail(tmp_path: Path) -> None:
    """Проверяет optional missing include при fail_on_missing_includes=false."""
    mod = _load_guard_module()
    config_data = _base_config()
    config_data["scenarios"]["sample"]["includes"] = ["missing/*.md"]
    config_path = _write_config(tmp_path, config_data)

    assert mod.run(["--scenario", "sample", "--strict"], config_path=config_path, repo_root=tmp_path) == 0


def test_required_missing_glob_exits_2(tmp_path: Path) -> None:
    """Проверяет read/config error для required missing include."""
    mod = _load_guard_module()
    config_data = _base_config()
    config_data["scenarios"]["sample"]["includes"] = [
        {"pattern": "missing/*.md", "required": True}
    ]
    config_path = _write_config(tmp_path, config_data)

    assert mod.run(["--scenario", "sample", "--strict"], config_path=config_path, repo_root=tmp_path) == 2


def test_scenario_cli_checks_named_scenario(tmp_path: Path) -> None:
    """Проверяет CLI --scenario на конкретном real config scenario name."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _base_config())
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    (workflow_dir / "ok.md").write_text("abc", encoding="utf-8")

    assert mod.run(["--scenario", "sample", "--strict"], config_path=config_path, repo_root=tmp_path) == 0


def test_file_cli_checks_single_path(tmp_path: Path) -> None:
    """Проверяет CLI --file для одиночного workflow artifact."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _base_config())
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    (workflow_dir / "ok.md").write_text("abc", encoding="utf-8")

    assert mod.run(["--file", "workflow/ok.md", "--strict"], config_path=config_path, repo_root=tmp_path) == 0


def test_config_context_section_warn_and_fail(tmp_path: Path) -> None:
    """Проверяет WARN и FAIL budgets для openspec/config.yaml::context."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _config_section_guard_config())
    target = _write_openspec_config(tmp_path, {"context": "123456"})
    config = mod.load_config(config_path)

    warn_result = {
        result.name: result for result in mod.check_config_sections(config, target)
    }["openspec/config.yaml::context"]
    target = _write_openspec_config(tmp_path, {"context": "1234567890"})
    fail_result = {
        result.name: result for result in mod.check_config_sections(config, target)
    }["openspec/config.yaml::context"]

    assert warn_result.status == "WARN"
    assert fail_result.status == "FAIL"


def test_config_rules_total_section_warn_and_fail(tmp_path: Path) -> None:
    """Проверяет WARN и FAIL budgets для openspec/config.yaml::rules."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _config_section_guard_config())
    target = _write_openspec_config(tmp_path, {"rules": {"alpha": "1"}})
    config = mod.load_config(config_path)

    warn_result = {
        result.name: result for result in mod.check_config_sections(config, target)
    }["openspec/config.yaml::rules"]
    target = _write_openspec_config(
        tmp_path,
        {"rules": {"alpha": "1", "beta": "2"}},
    )
    fail_result = {
        result.name: result for result in mod.check_config_sections(config, target)
    }["openspec/config.yaml::rules"]

    assert warn_result.status == "WARN"
    assert fail_result.status == "FAIL"


def test_config_rules_artifact_section_warn_and_fail(tmp_path: Path) -> None:
    """Проверяет WARN и FAIL budgets для rules.<artifact> pseudo-targets."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _config_section_guard_config())
    target = _write_openspec_config(
        tmp_path,
        {
            "rules": {
                "alpha": "123456",
                "beta": "1234567890",
            }
        },
    )
    config = mod.load_config(config_path)

    results = {
        result.name: result for result in mod.check_config_sections(config, target)
    }

    assert results["openspec/config.yaml::rules.alpha"].status == "WARN"
    assert results["openspec/config.yaml::rules.beta"].status == "FAIL"


def test_config_missing_optional_sections_do_not_fail(tmp_path: Path) -> None:
    """Проверяет, что отсутствие optional context/rules не создает section errors."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _config_section_guard_config())
    _write_openspec_config(tmp_path, {"other": "value"})
    config = mod.load_config(config_path)

    results = mod.check_file(config, tmp_path, Path("openspec/config.yaml"))

    assert [result.name for result in results] == ["openspec/config.yaml"]
    assert all(result.status != "FAIL" for result in results)


def test_config_whole_file_and_section_results_are_both_present(
    tmp_path: Path,
) -> None:
    """Доказывает, что whole-file artifact check не заменен section checks."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _config_section_guard_config())
    _write_openspec_config(
        tmp_path,
        {
            "context": "abc",
            "rules": {"verify": "abc"},
        },
    )
    config = mod.load_config(config_path)

    names = [
        result.name
        for result in mod.check_file(config, tmp_path, Path("openspec/config.yaml"))
    ]

    assert names == [
        "openspec/config.yaml",
        "openspec/config.yaml::context",
        "openspec/config.yaml::rules",
        "openspec/config.yaml::rules.verify",
    ]


def test_file_cli_includes_config_sections(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет, что --file openspec/config.yaml выводит section pseudo-targets."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _config_section_guard_config())
    _write_openspec_config(
        tmp_path,
        {
            "context": "abc",
            "rules": {"verify": "abc"},
        },
    )

    exit_code = mod.run(
        ["--file", "openspec/config.yaml", "--strict"],
        config_path=config_path,
        repo_root=tmp_path,
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "path=openspec/config.yaml " in output
    assert "path=openspec/config.yaml::context " in output
    assert "path=openspec/config.yaml::rules.verify " in output


def test_cli_misuse_exits_2(tmp_path: Path) -> None:
    """Фиксирует exit code 2 для несовместимых CLI options."""
    mod = _load_guard_module()
    config_path = _write_config(tmp_path, _base_config())

    assert (
        mod.run(
            ["--scenario", "sample", "--file", "workflow/ok.md", "--strict"],
            config_path=config_path,
            repo_root=tmp_path,
        )
        == 2
    )


def test_baseline_warn_allows_current_oversized_file_but_detects_growth(
    tmp_path: Path,
) -> None:
    """Проверяет baseline-aware WARN и FAIL при росте сверх baseline."""
    mod = _load_guard_module()
    config_data = _base_config()
    config_data["artifact_baselines"] = {
        "workflow/large.md": {
            "baseline_chars": 12,
            "allowed_growth_chars": 0,
            "status": "WARN",
        }
    }
    config_path = _write_config(tmp_path, config_data)
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    target = workflow_dir / "large.md"
    target.write_text("abcdefghijkl", encoding="utf-8")
    config = mod.load_config(config_path)

    current = mod.check_file(config, tmp_path, Path("workflow/large.md"))[0]
    target.write_text("abcdefghijklm", encoding="utf-8")
    grown = mod.check_file(config, tmp_path, Path("workflow/large.md"))[0]

    assert current.status == "WARN"
    assert grown.status == "FAIL"


def _repo_guard_paths() -> tuple[object, Path, Path]:
    """Возвращает guard module, repo root и production config path."""
    mod = _load_guard_module()
    repo_root = Path(__file__).resolve().parents[3]
    config_path = repo_root / "tools" / "openspec" / "openspec_guard.yaml"
    return mod, repo_root, config_path


def test_opsx_verify_accepted_baseline_warn_strict_exit_zero() -> None:
    """На accepted stage opsx_verify: WARN, --strict exit 0, growth budget 0."""
    mod, repo_root, config_path = _repo_guard_paths()
    config = mod.load_config(config_path)
    scenario = config.scenarios["opsx_verify"]
    assert scenario.baseline is not None
    assert scenario.baseline.allowed_growth_chars == 0
    assert scenario.baseline.status == "WARN"

    result = mod.check_scenario(config, repo_root, "opsx_verify")
    assert result.chars == scenario.baseline.baseline_chars
    assert result.status == "WARN"

    assert (
        mod.run(
            ["--scenario", "opsx_verify", "--strict"],
            config_path=config_path,
            repo_root=repo_root,
        )
        == 0
    )


def test_scenario_baseline_plus_one_char_fails_strict(tmp_path: Path) -> None:
    """+1 char над scenario baseline => FAIL при --strict."""
    mod = _load_guard_module()
    config_data = _base_config()
    config_data["scenario_defaults"] = {
        "green_chars": 5,
        "warn_chars": 20,
        "fail_chars": 21,
        "reserved_chars": {},
    }
    config_data["scenarios"] = {
        "growth_probe": {
            "baseline_chars": 8,
            "allowed_growth_chars": 0,
            "status": "WARN",
            "includes": ["workflow/*.md"],
        }
    }
    config_path = _write_config(tmp_path, config_data)
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()
    target = workflow_dir / "bundle.md"
    target.write_text("12345678", encoding="utf-8")

    assert (
        mod.run(
            ["--scenario", "growth_probe", "--strict"],
            config_path=config_path,
            repo_root=tmp_path,
        )
        == 0
    )

    target.write_text("123456789", encoding="utf-8")
    assert (
        mod.run(
            ["--scenario", "growth_probe", "--strict"],
            config_path=config_path,
            repo_root=tmp_path,
        )
        == 1
    )


def test_opsx_propose_scenario_baseline_unchanged_by_opsx_verify_rebaseline() -> None:
    """Соседний scenario baseline не меняется при opsx_verify rebaseline."""
    mod, _, config_path = _repo_guard_paths()
    config = mod.load_config(config_path)
    propose = config.scenarios["opsx_propose"].baseline
    assert propose is not None
    assert propose.baseline_chars == 74485
    assert propose.allowed_growth_chars == 0
