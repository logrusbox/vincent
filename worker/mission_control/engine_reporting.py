"""Translate engine outcomes into durable coordination reports."""

from __future__ import annotations

from .execution import ExecutionOutcome, ExecutionStatus
from .models import Task
from .project_executor import ProjectTaskExecutor
from .reporting import BlockedReport, CompletionReport, ReportPublisher


class EngineReportWriter:
    def __init__(self, publisher: ReportPublisher, worker_id: str, platform_version: str) -> None:
        self.publisher = publisher
        self.worker_id = worker_id
        self.platform_version = platform_version

    def __call__(self, task: Task, outcome: ExecutionOutcome, executor, expected_commit: str, started_at: str, completed_at: str) -> str:
        project = executor if isinstance(executor, ProjectTaskExecutor) else None
        if outcome.status is ExecutionStatus.SUCCESS:
            starting = project.prepared.starting_commit if project else task.claim_nonce or "unknown"
            ending = project.publication.ending_commit if project and project.publication else starting
            validation = project.provider.last_validation if project else ()
            report = CompletionReport(
                1, task.task_id, self.worker_id, task.project_id, task.repository,
                project.prepared.branch if project else "unknown", starting, ending,
                task.state.value, started_at, completed_at, (outcome.reason,), validation,
                "VERIFIED" if project and project.publication else "NO_CHANGES",
                (), (), self.platform_version,
            )
        else:
            preserved = (
                f"workspace: {project.prepared.path}" if project else "coordination state and local state retained",
            )
            report = BlockedReport(
                1, task.task_id, self.worker_id, outcome.status.value,
                ("Codex execution and supervisor validation pipeline",), preserved,
                outcome.reason or "automatic continuation is not proven safe",
                ("Inspect preserved evidence", "Provide a durable decision or corrected task"),
                "What action should the worker take next?", completed_at,
            )
        result = self.publisher.publish(report, expected_commit=expected_commit)
        return result.ending_commit
