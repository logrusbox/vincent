"""One-cycle worker engine joining discovery, claiming, state, and execution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .authorization import AuthorizationError
from .claims import Claim, ClaimConflict, ClaimStore
from .discovery import GitTaskSource
from .durable_state import DurableStateStore, OperationalState
from .execution import ExecutionOutcome, ExecutionStatus
from .models import Task, TaskState
from .state_machine import Actor, transition_task
from .supervisor import Executor
from typing import Callable
from .task_repository import TaskRepository


def physical_memory_gb() -> float:
    """Return installed physical memory in decimal GB for hard task eligibility."""
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if isinstance(pages, int) and isinstance(page_size, int) and pages > 0 and page_size > 0:
            return pages * page_size / 1_000_000_000
    except (OSError, ValueError):
        pass
    try:
        for line in open("/proc/meminfo", encoding="utf-8"):
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024 / 1_000_000_000
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


@dataclass(frozen=True, slots=True)
class EngineResult:
    task: Task
    coordination_commit: str


class WorkerEngine:
    def __init__(
        self,
        *,
        worker_id: str,
        capabilities: frozenset[str],
        source: GitTaskSource,
        task_repository: TaskRepository,
        claims: ClaimStore,
        state: DurableStateStore,
        executor: Executor | None = None,
        executor_factory: Callable[[Task], Executor] | None = None,
        reporter: Callable[[Task, ExecutionOutcome, Executor, str, str, str], str] | None = None,
        available_ram_gb: float | None = None,
    ) -> None:
        self.worker_id = worker_id
        self.capabilities = capabilities
        self.source = source
        self.task_repository = task_repository
        self.claims = claims
        self.state = state
        self.executor = executor
        self.executor_factory = executor_factory
        self.reporter = reporter
        self.available_ram_gb = physical_memory_gb() if available_ram_gb is None else available_ram_gb
        if self.executor is None and self.executor_factory is None:
            raise ValueError("worker engine requires an executor or executor factory")

    def run_once(self) -> EngineResult | None:
        started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        source_commit = self.source.synchronize()
        candidates = self.source.eligible(
            self.worker_id,
            self.capabilities,
            available_ram_gb=self.available_ram_gb,
        )
        for task in candidates:
            nonce = uuid4().hex
            claim = Claim(task.task_id, task.revision, self.worker_id, nonce, source_commit)

            # Persist intent before attempting remote ownership. If the process or
            # network fails at any point after this write, startup recovery knows
            # exactly which claim must be reconciled instead of leaving an
            # untraceable remote claim on a still-QUEUED task.
            self.state.save(
                OperationalState(
                    worker_id=self.worker_id,
                    task_id=task.task_id,
                    task_revision=task.revision,
                    task_state=TaskState.QUEUED.value,
                    claim_nonce=nonce,
                    claim_phase="INTENT",
                    source_commit=source_commit,
                    report_pending=False,
                )
            )
            try:
                self.claims.create(claim)
            except ClaimConflict:
                self.state.clear()
                continue

            self.state.save(
                OperationalState(
                    worker_id=self.worker_id,
                    task_id=task.task_id,
                    task_revision=task.revision,
                    task_state=TaskState.QUEUED.value,
                    claim_nonce=nonce,
                    claim_phase="REMOTE_CREATED",
                    source_commit=source_commit,
                    report_pending=False,
                )
            )
            if not self.claims.verify(claim):
                # Ownership is ambiguous. Preserve REMOTE_CREATED state so the
                # next startup blocks for deterministic reconciliation.
                return None

            claiming = transition_task(
                task, TaskState.CLAIMING, actor=Actor.WORKER,
                claim_worker_id=self.worker_id, claim_nonce=nonce,
            )
            published = self.task_repository.publish(claiming, expected_commit=source_commit)
            active = transition_task(
                claiming, TaskState.ACTIVE, actor=Actor.WORKER,
                claim_worker_id=self.worker_id,
            )
            published = self.task_repository.publish(active, expected_commit=published.ending_commit)
            self.state.save(
                OperationalState(
                    worker_id=self.worker_id,
                    task_id=task.task_id,
                    task_revision=task.revision,
                    task_state=active.state.value,
                    claim_nonce=nonce,
                    source_commit=source_commit,
                    report_pending=False,
                )
            )
            try:
                executor = self.executor_factory(active) if self.executor_factory else self.executor
                assert executor is not None
                outcome = executor.execute(active)
            except AuthorizationError as exc:
                outcome = ExecutionOutcome(ExecutionStatus.BLOCKED, str(exc))
            except Exception:
                outcome = ExecutionOutcome(ExecutionStatus.TASK_FAILURE, "executor raised an exception")
            if isinstance(outcome, ExecutionOutcome):
                normalized = outcome
                target = {
                    ExecutionStatus.SUCCESS: TaskState.COMPLETED,
                    ExecutionStatus.TASK_FAILURE: TaskState.FAILED,
                    ExecutionStatus.BLOCKED: TaskState.BLOCKED,
                    ExecutionStatus.WAITING_FOR_HUMAN: TaskState.WAITING_FOR_HUMAN,
                    ExecutionStatus.USAGE_LIMITED: TaskState.USAGE_LIMITED,
                }[outcome.status]
            else:
                normalized = ExecutionOutcome(
                    ExecutionStatus.SUCCESS if outcome else ExecutionStatus.TASK_FAILURE,
                    "legacy boolean executor result",
                )
                target = TaskState.COMPLETED if outcome else TaskState.FAILED
            terminal = transition_task(
                active, target, actor=Actor.WORKER,
                claim_worker_id=self.worker_id,
            )
            published = self.task_repository.publish(terminal, expected_commit=published.ending_commit)
            self.state.save(
                OperationalState(
                    worker_id=self.worker_id,
                    task_id=task.task_id,
                    task_revision=task.revision,
                    task_state=terminal.state.value,
                    claim_nonce=nonce,
                    source_commit=source_commit,
                    report_pending=self.reporter is not None,
                )
            )
            if self.reporter is not None:
                completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                report_commit = self.reporter(
                    terminal, normalized, executor, published.ending_commit, started_at, completed_at
                )
                published = type(published)(
                    published.starting_commit,
                    report_commit,
                    report_commit,
                    published.branch,
                )
                self.state.save(
                    OperationalState(
                        worker_id=self.worker_id,
                        task_id=task.task_id,
                        task_revision=task.revision,
                        task_state=terminal.state.value,
                        claim_nonce=nonce,
                        source_commit=source_commit,
                        report_pending=False,
                    )
                )
            return EngineResult(terminal, published.ending_commit)
        return None
