"""Provider-neutral execution result and independent validation contract."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from .execution import ExecutionOutcome, ExecutionStatus
from .models import Task
from .validation import ValidationCommand, ValidationResult, run_validation, validation_passed

class ProviderFailure(StrEnum):
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    TRANSIENT_CODEX_FAILURE = "TRANSIENT_FAILURE"  # compatibility alias
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    USAGE_LIMIT = "USAGE_LIMIT"
    TASK_FAILURE = "TASK_FAILURE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"
    TIMEOUT = "TIMEOUT"
    INTERRUPTED = "INTERRUPTED"


@dataclass(frozen=True, slots=True)
class ProviderResult:
    exit_status: int | None
    events: tuple[dict, ...]
    stderr: str
    failure: ProviderFailure | None

    @property
    def succeeded(self) -> bool:
        return self.exit_status == 0 and self.failure is None



class Provider(Protocol):
    def execute(self, workspace: Path, prompt: str) -> ProviderResult: ...


class ValidatedProviderExecutor:
    """Run a provider in one prepared workspace, then independently validate its work."""

    def __init__(
        self,
        runner: Provider,
        workspace: Path,
        validations: tuple[ValidationCommand, ...],
    ) -> None:
        self.runner = runner
        self.workspace = workspace
        self.validations = validations
        self.last_provider_result: ProviderResult | None = None
        self.last_validation: tuple[ValidationResult, ...] = ()

    @staticmethod
    def prompt(task: Task) -> str:
        acceptance = "\n".join(f"- {criterion}" for criterion in task.acceptance_criteria)
        forbidden = "\n".join(f"- {action}" for action in task.forbidden_actions) or "- None specified"
        return (
            f"Task ID: {task.task_id}\nObjective: {task.objective}\n\n"
            f"Acceptance criteria:\n{acceptance}\n\nForbidden actions:\n{forbidden}\n\n"
            "Work only in the prepared repository. Preserve unexpected state. Do not push or merge; "
            "the supervisor owns validation and Git publication."
        )

    def execute(self, task: Task) -> ExecutionOutcome:
        self.last_provider_result = self.runner.execute(self.workspace, self.prompt(task))
        if not self.last_provider_result.succeeded:
            status = {
                ProviderFailure.USAGE_LIMIT: ExecutionStatus.USAGE_LIMITED,
                ProviderFailure.AUTHENTICATION_FAILURE: ExecutionStatus.BLOCKED,
                ProviderFailure.TASK_FAILURE: ExecutionStatus.TASK_FAILURE,
                ProviderFailure.TRANSIENT_FAILURE: ExecutionStatus.BLOCKED,
                ProviderFailure.UNKNOWN_FAILURE: ExecutionStatus.BLOCKED,
                ProviderFailure.TIMEOUT: ExecutionStatus.BLOCKED,
                ProviderFailure.INTERRUPTED: ExecutionStatus.BLOCKED,
            }[self.last_provider_result.failure]
            return ExecutionOutcome(status, self.last_provider_result.failure.value)
        self.last_validation = tuple(
            run_validation(command, self.workspace) for command in self.validations
        )
        if not validation_passed(self.last_validation):
            return ExecutionOutcome(ExecutionStatus.TASK_FAILURE, "independent validation failed")
        return ExecutionOutcome(ExecutionStatus.SUCCESS, "Provider and independent validation passed")
