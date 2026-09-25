"""Noninteractive Codex boundary with explicit interruption classification."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable
from threading import Event
import math

from .process_control import run_bounded, ExecutionInterrupted

from .execution import ExecutionOutcome, ExecutionStatus
from .models import Task
from .validation import ValidationCommand, ValidationResult, run_validation, validation_passed


# Compatibility exports for the original Codex adapter API.
from .provider import ProviderFailure as CodexFailure, ProviderResult as CodexResult
from .provider import ValidatedProviderExecutor as ValidatedCodexExecutor


def classify_failure(exit_status: int | None, text: str) -> CodexFailure | None:
    if exit_status == 0:
        return None
    normalized = text.lower()
    if any(marker in normalized for marker in ("usage limit", "rate limit", "quota exceeded", "capacity")):
        return CodexFailure.USAGE_LIMIT
    if any(marker in normalized for marker in ("unauthorized", "authentication", "not logged in", "invalid api key")):
        return CodexFailure.AUTHENTICATION_FAILURE
    if any(marker in normalized for marker in ("timed out", "connection reset", "temporarily unavailable")):
        return CodexFailure.TRANSIENT_CODEX_FAILURE
    if any(marker in normalized for marker in ("task failed", "turn.failed")):
        return CodexFailure.TASK_FAILURE
    return CodexFailure.UNKNOWN_FAILURE


class CodexRunner:
    def __init__(
        self,
        executable: str = "codex",
        process_runner: Callable[..., subprocess.CompletedProcess[str]] = run_bounded,
        *,
        timeout_seconds: float | None = None,
        cancel: Event | None = None,
    ) -> None:
        self.executable = executable
        self.process_runner = process_runner
        self.timeout_seconds = timeout_seconds
        self.cancel = cancel

    def execute(self, workspace: Path, prompt: str) -> CodexResult:
        if (isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float))
                or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0):
            return CodexResult(None, (), "explicit provider execution bound required", CodexFailure.UNKNOWN_FAILURE)
        command = [
            self.executable,
            "exec",
            "--json",
            "--sandbox",
            "workspace-write",
            "-",
        ]
        forced_failure = None
        try:
            completed = self.process_runner(
                command,
                cwd=workspace,
                input=prompt,
                text=True,
                capture_output=True,
                check=False,
                timeout=self.timeout_seconds,
                cancel=self.cancel,
            )
        except (subprocess.TimeoutExpired, ExecutionInterrupted) as exc:
            forced_failure = CodexFailure.TIMEOUT if isinstance(exc, subprocess.TimeoutExpired) else CodexFailure.INTERRUPTED
            def decoded(value):
                return value.decode(errors="replace") if isinstance(value, bytes) else (value or "")
            completed = subprocess.CompletedProcess(command, None, decoded(exc.output), decoded(exc.stderr))
        except FileNotFoundError:
            return CodexResult(None, (), "Codex executable not found", CodexFailure.UNKNOWN_FAILURE)
        events: list[dict] = []
        invalid_lines: list[str] = []
        for line in completed.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines.append(line)
                continue
            if isinstance(event, dict):
                events.append(event)
        evidence = "\n".join([completed.stderr, *invalid_lines, *(json.dumps(e) for e in events)])
        failure = forced_failure or classify_failure(completed.returncode, evidence)
        return CodexResult(completed.returncode, tuple(events), completed.stderr, failure)


def retry_allowed(failure: CodexFailure | None, attempt: int, *, maximum_attempts: int = 3) -> bool:
    return failure is CodexFailure.TRANSIENT_CODEX_FAILURE and attempt < maximum_attempts
