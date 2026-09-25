import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from mission_control.authorization import AuthorizationError, ExecutionAuthority
from mission_control.codex_runner import CodexResult
from mission_control.execution import ExecutionStatus
from mission_control.models import Task
from mission_control.project_executor import ProjectExecutorFactory
from mission_control.workspace import WorkspaceManager


def git(path, *args):
    return subprocess.run(["git", *args], cwd=path, text=True, capture_output=True, check=True).stdout.strip()


class WritingRunner:
    def __init__(self, relative="result.txt"):
        self.relative = relative

    def execute(self, workspace, prompt):
        (workspace / self.relative).write_text("implemented\n")
        return CodexResult(0, (), "", None)


class ProjectExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.remote = self.root / "project.git"
        git(self.root, "init", "--bare", str(self.remote))
        seed = self.root / "seed"
        git(self.root, "clone", str(self.remote), str(seed))
        git(seed, "config", "user.name", "Test")
        git(seed, "config", "user.email", "test@example.invalid")
        git(seed, "switch", "-c", "main")
        (seed / "README.md").write_text("base\n")
        git(seed, "add", ".")
        git(seed, "commit", "-m", "base")
        git(seed, "push", "origin", "main")

    def tearDown(self):
        self.temporary.cleanup()

    def task(self, publish_paths=None):
        return Task.from_mapping({
            "schema_version": 1, "task_id": "MCP-1001", "project_id": "platform",
            "repository": str(self.remote), "base_branch": "main", "objective": "Write result",
            "acceptance_criteria": ["result exists"], "state": "ACTIVE", "revision": 3,
            "created_at": "2026-08-24T00:00:00Z", "claim_worker_id": "worker-1",
            "claim_nonce": "nonce", "publish_paths": publish_paths or [],
            "validation_commands": [[sys.executable, "-c", "from pathlib import Path; assert Path('result.txt').read_text() == 'implemented\\n'"]],
        })

    def test_validates_commits_pushes_and_verifies_project_work(self):
        task = self.task(["result.txt"])
        factory = ProjectExecutorFactory("worker-1", WorkspaceManager(self.root / "worktrees"), WritingRunner(), authority=ExecutionAuthority("worker-1", "standalone", (str(self.remote),)))
        executor = factory(task)
        git(executor.prepared.path, "config", "user.name", "Worker")
        git(executor.prepared.path, "config", "user.email", "worker@example.invalid")
        outcome = executor.execute(task)
        self.assertEqual(outcome.status, ExecutionStatus.SUCCESS)
        self.assertEqual(executor.publication.ending_commit, executor.publication.remote_commit)

    def test_revocation_after_execution_preserves_unpublished_work(self):
        task = self.task(["result.txt"])
        authority = ExecutionAuthority("worker-1", "standalone", (str(self.remote),))
        factory = ProjectExecutorFactory("worker-1", WorkspaceManager(self.root / "worktrees"), WritingRunner(), authority=authority)
        with patch.object(ExecutionAuthority, 'require', side_effect=[None, None, AuthorizationError('revoked')]):
            executor = factory(task)
            outcome = executor.execute(task)
        self.assertEqual(outcome.status, ExecutionStatus.BLOCKED)
        self.assertIn('revoked', outcome.reason)
        self.assertIsNone(executor.publication)
        self.assertTrue((executor.prepared.path / 'result.txt').exists())

    def test_changes_without_explicit_publish_contract_block(self):
        task = self.task()
        factory = ProjectExecutorFactory("worker-1", WorkspaceManager(self.root / "worktrees"), WritingRunner(), authority=ExecutionAuthority("worker-1", "standalone", (str(self.remote),)))
        executor = factory(task)
        outcome = executor.execute(task)
        self.assertEqual(outcome.status, ExecutionStatus.BLOCKED)
        self.assertTrue((executor.prepared.path / "result.txt").exists())


if __name__ == "__main__":
    unittest.main()
