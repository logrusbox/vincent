"""Worker administrative CLI; service activation remains gated by enrollment."""

from __future__ import annotations

import argparse
import json
import shutil
import signal
from threading import Event
from pathlib import Path

from .configuration import ConfigurationError, WorkerConfiguration
from .durable_state import DurableStateStore, recovery_action
from .enrollment import EnrollmentError, initialize_identity, request_enrollment
from .claims import GitClaimStore
from .providers import create_provider
from .discovery import GitTaskSource
from .engine import WorkerEngine
from .engine_reporting import EngineReportWriter
from .project_executor import ProjectExecutorFactory
from .service import WorkerService
from .reporting import ReportPublisher
from .task_repository import TaskRepository
from .workspace import WorkspaceManager


def doctor(configuration: WorkerConfiguration) -> tuple[bool, dict]:
    state = DurableStateStore(configuration.state_file).load()
    identity_matches = False
    try:
        identity = json.loads(configuration.identity_file.read_text(encoding="utf-8"))
        identity_matches = identity.get("schema_version") == 1 and identity.get("worker_id") == configuration.worker_id
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    coordination_checkout_valid = (
        configuration.coordination_checkout.is_dir()
        and (configuration.coordination_checkout / ".git").exists()
    )
    checks = {
        "worker_id": configuration.worker_id,
        "provider_bound_configured": configuration.provider_timeout_seconds is not None,
        "git_available": shutil.which("git") is not None,
        "codex_available": shutil.which("codex") is not None,
        "workspace_root_absolute": configuration.workspace_root.is_absolute(),
        "identity_matches": identity_matches,
        "coordination_checkout_valid": coordination_checkout_valid,
        "recovery_action": recovery_action(state).value,
    }
    return all((checks["provider_bound_configured"], checks["git_available"], checks["codex_available"], checks["workspace_root_absolute"], identity_matches, coordination_checkout_valid)), checks


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="mission-control-worker")
    result.add_argument("--config", type=Path, default=Path("/etc/mission-control/worker.toml"))
    result.add_argument("--identity-root", type=Path, default=Path("/var/lib/vincent/identity"))
    result.add_argument("command", choices=("doctor", "initialize", "enroll", "serve"))
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.command in ("initialize", "enroll"):
        try:
            if arguments.command == "initialize":
                request = initialize_identity(arguments.identity_root)
            else:
                if not (arguments.identity_root / "identity.json").exists():
                    initialize_identity(arguments.identity_root)
                request = request_enrollment(arguments.identity_root)
        except (EnrollmentError, OSError, ValueError) as exc:
            print(json.dumps({"created": False, "error": str(exc)}, sort_keys=True))
            return 2
        print(request.to_json(), end="")
        return 0
    try:
        configuration = WorkerConfiguration.load(arguments.config)
        healthy, evidence = doctor(configuration)
    except (ConfigurationError, ValueError) as exc:
        print(json.dumps({"healthy": False, "error": str(exc)}, sort_keys=True))
        return 2
    if arguments.command == "doctor":
        print(json.dumps({"healthy": healthy, **evidence}, sort_keys=True))
        return 0 if healthy else 1
    if not healthy:
        print(json.dumps({"started": False, **evidence}, sort_keys=True))
        return 1
    state_store = DurableStateStore(configuration.state_file)
    action = recovery_action(state_store.load())
    if action.value != "IDLE":
        print(json.dumps({"started": False, "recovery_action": action.value, "error": "manual or remote reconciliation required"}, sort_keys=True))
        return 3
    checkout = configuration.coordination_checkout
    source = GitTaskSource(checkout, branch=configuration.coordination_branch, tasks_path=configuration.tasks_path)
    task_repository = TaskRepository(checkout, branch=configuration.coordination_branch, tasks_path=configuration.tasks_path)
    stop = Event()
    factory = ProjectExecutorFactory(
        configuration.worker_id,
        WorkspaceManager(configuration.workspace_root),
        create_provider("codex", timeout_seconds=configuration.provider_timeout_seconds, cancel=stop),
        git_author_name=configuration.git_author_name,
        git_author_email=configuration.git_author_email,
    )
    engine = WorkerEngine(
        worker_id=configuration.worker_id,
        capabilities=configuration.capabilities,
        source=source,
        task_repository=task_repository,
        claims=GitClaimStore(checkout),
        state=state_store,
        executor_factory=factory,
        reporter=EngineReportWriter(
            ReportPublisher(checkout, branch=configuration.coordination_branch),
            configuration.worker_id,
            "0.1.0",
        ),
    )
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    return WorkerService(engine, configuration.poll_seconds, stop).run()
