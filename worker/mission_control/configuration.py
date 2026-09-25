"""Strict worker configuration loaded from standard-library TOML."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class WorkerConfiguration:
    worker_id: str
    state_file: Path
    workspace_root: Path
    coordination_checkout: Path
    identity_file: Path
    capabilities: frozenset[str] = frozenset()
    coordination_branch: str = "main"
    tasks_path: str = "coordination/tasks"
    git_author_name: str = "Mission Control Worker"
    git_author_email: str = "worker@localhost.invalid"
    poll_seconds: int = 60
    provider_timeout_seconds: int | None = None

    @classmethod
    def load(cls, path: Path) -> "WorkerConfiguration":
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
            raise ConfigurationError(f"cannot load worker configuration: {exc}") from exc
        worker = data.get("worker")
        paths = data.get("paths")
        coordination = data.get("coordination")
        git_config = data.get("git", {})
        if not isinstance(worker, dict) or not isinstance(paths, dict) or not isinstance(coordination, dict):
            raise ConfigurationError("configuration requires [worker], [paths], and [coordination]")
        worker_id = worker.get("id")
        if not isinstance(worker_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,62}", worker_id):
            raise ConfigurationError("worker.id must be a stable lowercase identifier")
        poll = worker.get("poll_seconds", 60)
        if not isinstance(poll, int) or isinstance(poll, bool) or not 5 <= poll <= 3600:
            raise ConfigurationError("worker.poll_seconds must be between 5 and 3600")
        try:
            state_file = Path(paths["state_file"])
            workspace_root = Path(paths["workspace_root"])
            coordination_checkout = Path(coordination["checkout"])
            identity_file = Path(paths["identity_file"])
        except (KeyError, TypeError) as exc:
            raise ConfigurationError("state, workspace, and coordination paths are required") from exc
        if not all(path.is_absolute() for path in (state_file, workspace_root, coordination_checkout, identity_file)):
            raise ConfigurationError("worker paths must be absolute")
        capabilities = worker.get("capabilities", [])
        if not isinstance(capabilities, list) or any(not isinstance(item, str) or not item for item in capabilities):
            raise ConfigurationError("worker.capabilities must be a list of strings")
        branch = coordination.get("branch", "main")
        tasks_path = coordination.get("tasks_path", "coordination/tasks")
        author_name = git_config.get("author_name", "Mission Control Worker")
        author_email = git_config.get("author_email", "worker@localhost.invalid")
        if not all(isinstance(item, str) and item for item in (branch, tasks_path, author_name, author_email)):
            raise ConfigurationError("coordination and Git strings must not be empty")
        provider = data.get("provider", {})
        if not isinstance(provider, dict):
            raise ConfigurationError("provider must be a table")
        timeout = provider.get("execution_timeout_seconds")
        if timeout is not None and (type(timeout) is not int or timeout <= 0):
            raise ConfigurationError("provider.execution_timeout_seconds must be a positive integer")
        return cls(worker_id, state_file, workspace_root, coordination_checkout, identity_file, frozenset(capabilities), branch, tasks_path, author_name, author_email, poll, timeout)
