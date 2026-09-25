"""Strict protocol-v1 models with no third-party runtime dependency."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import StrEnum
import re
from typing import Any, Mapping


SUPPORTED_PRIORITIES = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
SUPPORTED_SCHEMA_VERSION = 1
SUPPORTED_INTEGRATION_POLICIES = {"HUMAN_APPROVAL_REQUIRED"}


class ProtocolError(ValueError):
    """An object cannot be interpreted safely under the supported protocol."""


class TaskState(StrEnum):
    QUEUED = "QUEUED"
    CLAIMING = "CLAIMING"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    USAGE_LIMITED = "USAGE_LIMITED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


def parse_created_at(value: str) -> datetime:
    """Protocol v1 uses UTC calendar timestamps with at most microsecond precision."""
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z", value
    ):
        raise ProtocolError("created_at must be a UTC timestamp ending in Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProtocolError("created_at is not a valid calendar timestamp") from exc


def _required_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(f"{key} must be a non-empty string")
    return value


def _string_list(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ProtocolError(f"{key} must be a list of non-empty strings")
    return tuple(value)


def _command_list(data: Mapping[str, Any], key: str) -> tuple[tuple[str, ...], ...]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise ProtocolError(f"{key} must be a list of argument lists")
    commands = []
    for command in value:
        if not isinstance(command, list) or not command or any(
            not isinstance(argument, str) or not argument for argument in command
        ):
            raise ProtocolError(f"{key} must contain non-empty argument lists")
        commands.append(tuple(command))
    return tuple(commands)


@dataclass(frozen=True, slots=True)
class Task:
    schema_version: int
    task_id: str
    project_id: str
    repository: str
    base_branch: str
    objective: str
    acceptance_criteria: tuple[str, ...]
    state: TaskState
    revision: int
    created_at: str
    assigned_worker: str | None = None
    required_capabilities: tuple[str, ...] = ()
    minimum_ram_gb: int | None = None
    priority: str = "NORMAL"
    dependencies: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    integration_policy: str = "HUMAN_APPROVAL_REQUIRED"
    can_continue_unattended: bool = False
    claim_worker_id: str | None = None
    claim_nonce: str | None = None
    validation_commands: tuple[tuple[str, ...], ...] = ()
    publish_paths: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Task":
        if not isinstance(data, Mapping):
            raise ProtocolError("task must be an object")

        version = data.get("schema_version")
        if type(version) is not int or version != SUPPORTED_SCHEMA_VERSION:
            raise ProtocolError(
                f"unsupported schema_version {version!r}; expected {SUPPORTED_SCHEMA_VERSION}"
            )

        revision = data.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ProtocolError("revision must be an integer greater than zero")

        try:
            state = TaskState(data.get("state"))
        except (TypeError, ValueError) as exc:
            raise ProtocolError(f"invalid task state {data.get('state')!r}") from exc

        minimum_ram = data.get("minimum_ram_gb")
        if minimum_ram is not None and (
            not isinstance(minimum_ram, int)
            or isinstance(minimum_ram, bool)
            or minimum_ram < 1
        ):
            raise ProtocolError("minimum_ram_gb must be a positive integer or null")

        unattended = data.get("can_continue_unattended", False)
        if not isinstance(unattended, bool):
            raise ProtocolError("can_continue_unattended must be boolean")
        if unattended:
            raise ProtocolError(
                "can_continue_unattended=true is not supported until automatic recovery policy is implemented"
            )

        assigned = data.get("assigned_worker")
        if assigned is not None and (not isinstance(assigned, str) or not assigned.strip()):
            raise ProtocolError("assigned_worker must be a non-empty string or null")

        criteria = _string_list(data, "acceptance_criteria")
        if not criteria:
            raise ProtocolError("acceptance_criteria must not be empty")

        integration_policy = (
            _required_text(data, "integration_policy")
            if "integration_policy" in data
            else "HUMAN_APPROVAL_REQUIRED"
        )
        if integration_policy not in SUPPORTED_INTEGRATION_POLICIES:
            raise ProtocolError(f"unsupported integration_policy {integration_policy!r}")

        forbidden_actions = _string_list(data, "forbidden_actions")
        if forbidden_actions:
            raise ProtocolError(
                "forbidden_actions are not mechanically enforceable in protocol v1; use repository/task authority boundaries instead"
            )

        created_at = _required_text(data, "created_at")
        parse_created_at(created_at)
        priority = _required_text(data, "priority") if "priority" in data else "NORMAL"
        if priority not in SUPPORTED_PRIORITIES:
            raise ProtocolError(f"unsupported priority {priority!r}")

        task = cls(
            schema_version=version,
            task_id=_required_text(data, "task_id"),
            project_id=_required_text(data, "project_id"),
            repository=_required_text(data, "repository"),
            base_branch=_required_text(data, "base_branch"),
            objective=_required_text(data, "objective"),
            acceptance_criteria=criteria,
            state=state,
            revision=revision,
            created_at=created_at,
            assigned_worker=assigned,
            required_capabilities=_string_list(data, "required_capabilities"),
            minimum_ram_gb=minimum_ram,
            priority=priority,
            dependencies=_string_list(data, "dependencies"),
            forbidden_actions=forbidden_actions,
            integration_policy=integration_policy,
            can_continue_unattended=unattended,
            claim_worker_id=data.get("claim_worker_id"),
            claim_nonce=data.get("claim_nonce"),
            validation_commands=_command_list(data, "validation_commands"),
            publish_paths=_string_list(data, "publish_paths"),
        )
        task._validate_claim_fields()
        return task

    def _validate_claim_fields(self) -> None:
        claim_values = (self.claim_worker_id, self.claim_nonce)
        if any(value is not None for value in claim_values) and not all(
            isinstance(value, str) and value.strip() for value in claim_values
        ):
            raise ProtocolError("claim_worker_id and claim_nonce must be set together")
        if self.state in {TaskState.CLAIMING, TaskState.ACTIVE} and not all(claim_values):
            raise ProtocolError(f"{self.state} requires claim_worker_id and claim_nonce")

    def with_state(self, state: TaskState, **changes: Any) -> "Task":
        task = replace(self, state=state, revision=self.revision + 1, **changes)
        task._validate_claim_fields()
        return task

    def to_mapping(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        for key in ("acceptance_criteria", "required_capabilities", "dependencies", "forbidden_actions"):
            data[key] = list(data[key])
        data["validation_commands"] = [list(command) for command in self.validation_commands]
        data["publish_paths"] = list(self.publish_paths)
        return data
