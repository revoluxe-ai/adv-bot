"""Unit-тесты локального supervisor prod-стека."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import run_adv_bot_stack as stack


def test_default_services_match_prod_k8s_deployments() -> None:
    names = {spec.name for spec in stack.DEFAULT_SERVICES}
    assert names == {
        "active_shop_ids",
        "shop_worker",
        "updater",
        "client_bot",
        "arq_worker",
    }
    k8s = {spec.k8s_deployment for spec in stack.DEFAULT_SERVICES}
    assert "run-update-active-shop-ids" in k8s
    assert "adv-bot-asq-worker" in k8s


def test_default_services_start_groups() -> None:
    by_name = {spec.name: spec.group for spec in stack.DEFAULT_SERVICES}
    assert by_name["active_shop_ids"] == "bootstrap"
    assert by_name["shop_worker"] == "core"
    assert by_name["updater"] == "parallel"
    assert by_name["client_bot"] == "parallel"
    assert by_name["arq_worker"] == "parallel"


def test_python_script_argv_uses_executable_and_repo_path() -> None:
    argv = stack._python_script("updater.py")
    assert argv[0] == stack.sys.executable
    assert argv[1].endswith("updater.py")


def test_arq_worker_argv() -> None:
    argv = stack._arq_worker_argv()
    assert argv[:3] == (stack.sys.executable, "-m", "arq")
    assert argv[3] == "app.arq_workers.workers.WorkerSettings"


def test_filter_services_only_preserves_order() -> None:
    selected = stack.filter_services(
        stack.DEFAULT_SERVICES,
        only=frozenset({"updater", "active_shop_ids"}),
        exclude=frozenset(),
    )
    assert [spec.name for spec in selected] == ["active_shop_ids", "updater"]


def test_filter_services_exclude() -> None:
    selected = stack.filter_services(
        stack.DEFAULT_SERVICES,
        only=None,
        exclude=frozenset({"client_bot", "arq_worker"}),
    )
    names = [spec.name for spec in selected]
    assert "client_bot" not in names
    assert "arq_worker" not in names
    assert len(names) == 3


def test_filter_services_unknown_only_raises() -> None:
    with pytest.raises(ValueError, match="unknown_service"):
        stack.filter_services(
            stack.DEFAULT_SERVICES,
            only=frozenset({"unknown_service"}),
            exclude=frozenset(),
        )


def test_services_in_start_order() -> None:
    subset = stack.filter_services(
        stack.DEFAULT_SERVICES,
        only=frozenset({"arq_worker", "active_shop_ids", "shop_worker"}),
        exclude=frozenset(),
    )
    ordered = stack.services_in_start_order(subset)
    assert [spec.name for spec in ordered] == [
        "active_shop_ids",
        "shop_worker",
        "arq_worker",
    ]


@patch("run_adv_bot_stack.time.sleep")
@patch("run_adv_bot_stack.start_process")
def test_staggered_start_bootstrap_sleep_before_core(
    mock_start: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    mock_start.side_effect = lambda spec, **_: MagicMock(
        spec=spec,
        poll=MagicMock(return_value=None),
    )
    subset = stack.filter_services(
        stack.DEFAULT_SERVICES,
        only=frozenset({"active_shop_ids", "shop_worker", "updater"}),
        exclude=frozenset(),
    )
    managed = {spec.name: stack.ManagedProcess(spec=spec) for spec in subset}
    stack.staggered_start(
        managed,
        stack.services_in_start_order(subset),
        bootstrap_sec=15.0,
        separate_windows=False,
    )
    assert mock_start.call_count == 3
    mock_sleep.assert_called_once_with(15.0)
    call_names = [call.args[0].name for call in mock_start.call_args_list]
    assert call_names[0] == "active_shop_ids"
    assert call_names[1] == "shop_worker"
    assert call_names[2] == "updater"


@patch("run_adv_bot_stack.stop_process")
@patch("run_adv_bot_stack.staggered_start")
@patch("run_adv_bot_stack.signal.signal")
def test_run_supervisor_no_restart_exits_when_children_done(
    _mock_signal: MagicMock,
    mock_staggered: MagicMock,
    mock_stop: MagicMock,
) -> None:
    subset = (stack.DEFAULT_SERVICES[0],)

    def _mark_started(
        managed: dict[str, stack.ManagedProcess],
        ordered_specs: object,
        **kwargs: object,
    ) -> None:
        for entry in managed.values():
            proc = MagicMock()
            proc.poll.return_value = 0
            entry.process = proc

    mock_staggered.side_effect = _mark_started

    stack.run_supervisor(
        subset,
        bootstrap_sec=0,
        separate_windows=False,
        auto_restart=False,
    )
    mock_staggered.assert_called_once()
    assert mock_stop.call_count == len(subset)


@patch("run_adv_bot_stack.subprocess.Popen")
def test_start_process_invokes_popen_with_repo_cwd(
    mock_popen: MagicMock,
) -> None:
    spec = stack.DEFAULT_SERVICES[0]
    stack.start_process(spec, separate_windows=False)
    mock_popen.assert_called_once()
    _, kwargs = mock_popen.call_args
    assert kwargs["cwd"] == stack.REPO_ROOT
    assert mock_popen.call_args[0][0] == spec.argv


def test_main_list_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = stack.main(["--list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "active_shop_ids" in out
    assert "run-update-active-shop-ids" in out
