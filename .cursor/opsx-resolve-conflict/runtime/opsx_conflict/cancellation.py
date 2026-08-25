"""Process supervisor and cancellation barrier (RC04-H08)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from .errors import StopRequired
from .hashutil import sha256_text

_ledger_local = threading.local()


@contextmanager
def bind_execution_ledger(ledger: Any | None) -> Iterator[None]:
    """Bind the active run ledger so every spawn is recorded."""
    previous = getattr(_ledger_local, "ledger", None)
    _ledger_local.ledger = ledger
    try:
        yield
    finally:
        _ledger_local.ledger = previous


def set_execution_ledger(ledger: Any | None) -> None:
    """Set thread-local ledger for process spawn auditing."""
    _ledger_local.ledger = ledger


def clear_execution_ledger() -> None:
    """Clear thread-local process ledger binding."""
    _ledger_local.ledger = None


def _active_ledger() -> Any | None:
    return getattr(_ledger_local, "ledger", None)


def active_execution_ledger() -> Any | None:
    """Return the thread-local ledger bound for process/Git auditing."""
    return _active_ledger()


@dataclass
class TrackedProcess:
    pid: int
    argv: tuple[str, ...]
    started_at: float
    proc: subprocess.Popen[str]


class ProcessSupervisor:
    """Runtime-owned registry; must reach BACKGROUND_PROCESSES=0 before STOP."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._procs: dict[int, TrackedProcess] = {}
        self._stopping = False
        self.barrier_closed = False

    @property
    def stopping(self) -> bool:
        return self._stopping

    def register(self, proc: subprocess.Popen[str], argv: list[str] | tuple[str, ...]) -> None:
        with self._lock:
            if self._stopping:
                _terminate_tree(proc)
                raise StopRequired("REJECT_NEW_ACTIONS_WHILE_STOPPING")
            if proc.pid is None:
                return
            self._procs[proc.pid] = TrackedProcess(proc.pid, tuple(argv), time.time(), proc)

    def unregister(self, proc: subprocess.Popen[str]) -> None:
        with self._lock:
            if proc.pid is not None:
                self._procs.pop(proc.pid, None)

    def live_count(self) -> int:
        with self._lock:
            dead = [pid for pid, t in self._procs.items() if t.proc.poll() is not None]
            for pid in dead:
                self._procs.pop(pid, None)
            return len(self._procs)

    def cancel_all(self, *, reason: str = "STOP") -> dict[str, Any]:
        """Close the barrier, cancel children, then reopen process admission."""
        evidence = self.close_barrier(reason=reason)
        self.release_barrier()
        return evidence

    def close_barrier(self, *, reason: str = "STOP") -> dict[str, Any]:
        """Cancel children and keep process admission closed for publication."""
        with self._lock:
            self._stopping = True
            items = list(self._procs.values())
        for tracked in items:
            _terminate_tree(tracked.proc)
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if self.live_count() == 0:
                break
            time.sleep(0.05)
        remaining = self.live_count()
        self.barrier_closed = remaining == 0
        if remaining != 0:
            raise StopRequired(
                "CANCELLATION_BARRIER_FAILED",
                {"background_processes": remaining, "reason": reason},
            )
        return {
            "BACKGROUND_PROCESSES": 0,
            "CANCELLATION_BARRIER_CLOSED": True,
            "reason": reason,
        }

    def release_barrier(self) -> None:
        """Reopen admission only after terminal evidence is fully published."""
        with self._lock:
            if not self.barrier_closed or self.live_count() != 0:
                raise StopRequired("CANCELLATION_BARRIER_NOT_SAFE_TO_RELEASE")
            self._stopping = False


_SUPERVISOR = ProcessSupervisor()


def supervisor() -> ProcessSupervisor:
    return _SUPERVISOR


def reset_supervisor_for_tests() -> None:
    global _SUPERVISOR
    _SUPERVISOR = ProcessSupervisor()


def _terminate_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        proc.wait(timeout=2)
    except Exception:
        pass


def run_process(
    argv: list[str],
    *,
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 60.0,
    text: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Spawn a supervised subprocess; timeout kills the process group."""
    if supervisor().stopping:
        raise StopRequired("REJECT_NEW_ACTIONS_WHILE_STOPPING")
    ledger = _active_ledger()
    if ledger is not None:
        ledger.append(
            "COMMAND_START",
            {
                "kind": "process",
                "argv": list(argv),
                "cwd": str(cwd) if cwd is not None else None,
            },
        )
    popen_kwargs: dict[str, Any] = {
        "args": argv,
        "cwd": str(cwd) if cwd is not None else None,
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": text,
        "shell": False,
    }
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    else:
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    proc = subprocess.Popen(**popen_kwargs)
    supervisor().register(proc, argv)
    try:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _terminate_tree(proc)
            supervisor().unregister(proc)
            if ledger is not None:
                ledger.append(
                    "COMMAND_END",
                    {
                        "kind": "process",
                        "argv": list(argv),
                        "returncode": None,
                        "timeout": True,
                    },
                )
            raise StopRequired(
                "TOOL_OR_PROCESS_HANG",
                {"argv": argv, "timeout": timeout, "stdout_sha256": sha256_text("")},
            )
        completed = subprocess.CompletedProcess(
            argv, proc.returncode or 0, stdout or "", stderr or ""
        )
        if ledger is not None:
            ledger.append(
                "COMMAND_END",
                {
                    "kind": "process",
                    "argv": list(argv),
                    "returncode": completed.returncode,
                    "stdout_sha256": sha256_text(completed.stdout or ""),
                    "stderr_sha256": sha256_text(completed.stderr or ""),
                },
            )
        return completed
    finally:
        supervisor().unregister(proc)


# late import typing Path
from pathlib import Path  # noqa: E402
