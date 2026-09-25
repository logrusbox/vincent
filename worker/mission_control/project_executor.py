"""Prepared-workspace Codex execution, validation, and safe branch publication."""

from __future__ import annotations

from dataclasses import dataclass

from .provider import Provider, ValidatedProviderExecutor
from .execution import ExecutionOutcome, ExecutionStatus
from .models import Task
from .publication import GitPublisher, PublicationError, PublicationResult
from .validation import ValidationCommand
from .workspace import PreparedWorkspace, WorkspaceManager


@dataclass(slots=True)
class ProjectTaskExecutor:
    task: Task
    prepared: PreparedWorkspace
    provider: ValidatedProviderExecutor
    publication: PublicationResult | None = None

    def execute(self, task: Task) -> ExecutionOutcome:
        outcome = self.provider.execute(task)
        if outcome.status is not ExecutionStatus.SUCCESS:
            return outcome
        publisher = GitPublisher(self.prepared.path)
        changed = publisher._git("status", "--porcelain=v1", "--untracked-files=all").stdout.strip()
        if not changed:
            return ExecutionOutcome(ExecutionStatus.SUCCESS, "validated; no project changes")
        if not task.publish_paths:
            return ExecutionOutcome(ExecutionStatus.BLOCKED, "project changed but task has no explicit publish_paths")
        expected_remote = publisher._remote_head(self.prepared.branch)
        try:
            self.publication = publisher.publish(
                branch=self.prepared.branch,
                expected_remote_head=expected_remote,
                paths=task.publish_paths,
                message=f"Task {task.task_id}: implementation checkpoint",
            )
        except PublicationError as exc:
            return ExecutionOutcome(ExecutionStatus.BLOCKED, f"project publication blocked: {exc}")
        remaining = publisher._git("status", "--porcelain=v1", "--untracked-files=all").stdout.strip()
        if remaining:
            return ExecutionOutcome(ExecutionStatus.BLOCKED, "unpublished workspace evidence remains")
        return ExecutionOutcome(ExecutionStatus.SUCCESS, "validated and remotely verified")


class ProjectExecutorFactory:
    def __init__(self, worker_id: str, workspaces: WorkspaceManager, runner: Provider, *, git_author_name: str = "Mission Control Worker", git_author_email: str = "worker@localhost.invalid") -> None:
        self.worker_id = worker_id
        self.workspaces = workspaces
        self.runner = runner
        self.git_author_name = git_author_name
        self.git_author_email = git_author_email
        self.last_executor: ProjectTaskExecutor | None = None

    def __call__(self, task: Task) -> ProjectTaskExecutor:
        prepared = self.workspaces.prepare(
            project_id=task.project_id,
            repository=task.repository,
            base_branch=task.base_branch,
            worker_id=self.worker_id,
            task_id=task.task_id,
        )
        validations = tuple(
            ValidationCommand(f"validation-{index + 1}", command)
            for index, command in enumerate(task.validation_commands)
        )
        GitPublisher(prepared.path)._git("config", "user.name", self.git_author_name)
        GitPublisher(prepared.path)._git("config", "user.email", self.git_author_email)
        provider = ValidatedProviderExecutor(self.runner, prepared.path, validations)
        self.last_executor = ProjectTaskExecutor(task, prepared, provider)
        return self.last_executor
