"""CAS-like publication of authoritative task-state files."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Task
from .publication import GitPublisher, PublicationError, PublicationResult


class TaskRepository:
    def __init__(self, repository: Path, *, branch: str = "main", tasks_path: str = "coordination/tasks") -> None:
        self.repository = repository.resolve()
        self.branch = branch
        self.tasks_path = tasks_path
        self.publisher = GitPublisher(self.repository)
        self.journal = Path(self.publisher._git("rev-parse", "--absolute-git-dir").stdout.strip()) / "vincent-task-publication.json"

    def publish(self, task: Task, *, expected_commit: str) -> PublicationResult:
        path = (self.repository / self.tasks_path / f"{task.task_id}.json").resolve()
        if self.repository not in path.parents:
            raise PublicationError("task path escapes repository")
        current = self.publisher._git("rev-parse", "HEAD").stdout.strip()
        if current != expected_commit:
            raise PublicationError("coordination checkout changed before task update")
        if self.journal.exists():
            raise PublicationError(f"pending task publication requires recovery: {self.journal}")
        if self.publisher._git("status", "--porcelain=v1", "--untracked-files=all").stdout.strip():
            raise PublicationError("coordination checkout must be clean before recording publication intent")
        relative = str(path.relative_to(self.repository))
        content = json.dumps(task.to_mapping(), sort_keys=True, indent=2) + "\n"
        intent = {"schema_version": 1, "repository": str(self.repository), "branch": self.branch,
                  "expected_commit": expected_commit, "path": relative, "content": content}
        descriptor = os.open(self.journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as journal:
            journal.write(json.dumps(intent, sort_keys=True) + "\n")
            journal.flush()
            os.fsync(journal.fileno())
        self._sync_journal_directory()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(task.to_mapping(), sort_keys=True, indent=2) + "\n", encoding="utf-8")
        relative = str(path.relative_to(self.repository))
        result = self.publisher.publish(
            branch=self.branch,
            expected_remote_head=expected_commit,
            paths=(relative,),
            message=f"Task {task.task_id}: {task.state.value}",
        )
        self._clear_journal()
        return result

    def _sync_journal_directory(self) -> None:
        descriptor = os.open(self.journal.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _clear_journal(self) -> None:
        self.journal.unlink()
        self._sync_journal_directory()

    def recover(self) -> PublicationResult:
        """Retry only the exact recorded transition; never discard or reset state."""
        try:
            intent = json.loads(self.journal.read_text())
            if (intent['schema_version'] != 1 or intent['repository'] != str(self.repository)
                    or intent['branch'] != self.branch):
                raise ValueError('journal authority mismatch')
            relative, content, base = intent['path'], intent['content'], intent['expected_commit']
            task = Task.from_mapping(json.loads(content))
            path = (self.repository / relative).resolve()
            expected_path = (self.repository / self.tasks_path / (task.task_id + '.json')).resolve()
            if path != expected_path or self.repository not in path.parents:
                raise ValueError('journal path mismatch')
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise PublicationError('invalid/missing publication journal; preserve for manual recovery') from exc
        publisher = self.publisher
        if publisher._git('symbolic-ref', '--short', 'HEAD').stdout.strip() != self.branch:
            raise PublicationError('publication branch changed; preserve for manual recovery')
        current = publisher._git('rev-parse', 'HEAD').stdout.strip()
        changed = set()
        for args in (('diff', '--name-only', '-z'), ('diff', '--cached', '--name-only', '-z'),
                     ('ls-files', '--others', '--exclude-standard', '-z')):
            changed.update(filter(None, publisher._git(*args).stdout.split('\0')))
        if changed - {relative}:
            raise PublicationError('unrelated local changes preserved; manual recovery required')
        if current == base:
            observed = path.read_text() if path.exists() else None
            original = publisher._git('show', f'{base}:{relative}', check=False)
            if observed != content:
                if original.returncode or observed != original.stdout:
                    raise PublicationError('task content differs from intent and base; preserve for manual recovery')
                path.write_text(content)
            result = publisher.publish(branch=self.branch, expected_remote_head=base,
                                       paths=(relative,), message=f'Task {task.task_id}: {task.state.value}')
        else:
            parents = publisher._git('rev-list', '--parents', '-n', '1', current).stdout.split()
            delta = publisher._git('diff', '--name-only', base, current).stdout.splitlines()
            committed = publisher._git('show', f'{current}:{relative}').stdout
            if parents != [current, base] or delta != [relative] or committed != content or changed:
                raise PublicationError('local checkpoint differs from intent; preserve for manual recovery')
            remote = publisher._remote_head(self.branch)
            if remote == base:
                publisher._git('push', '--porcelain', publisher.remote, f'{current}:refs/heads/{self.branch}')
                remote = publisher._remote_head(self.branch)
            if remote != current:
                raise PublicationError('remote authority changed; checkpoint and journal preserved')
            result = PublicationResult(base, current, remote, self.branch)
        self._clear_journal()
        return result
