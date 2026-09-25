import unittest
from types import SimpleNamespace

from mission_control.engine_reporting import EngineReportWriter
from mission_control.execution import ExecutionOutcome, ExecutionStatus
from mission_control.models import Task


def task(state="COMPLETED"):
    return Task.from_mapping({"schema_version": 1, "task_id": "MCP-1201", "project_id": "platform", "repository": "owner/repo", "base_branch": "main", "objective": "Report", "acceptance_criteria": ["report exists"], "state": state, "revision": 4, "created_at": "2026-09-25T00:00:00Z", "claim_worker_id": "worker-1", "claim_nonce": "nonce"})


class FakePublisher:
    def __init__(self):
        self.report = None

    def publish(self, report, expected_commit):
        self.report = report
        return SimpleNamespace(ending_commit="b" * 40)


class EngineReportingTests(unittest.TestCase):
    def test_success_creates_completion_report(self):
        publisher = FakePublisher()
        result = EngineReportWriter(publisher, "worker-1", "0.1.0")(task(), ExecutionOutcome(ExecutionStatus.SUCCESS, "done"), object(), "a" * 40, "start", "end")
        self.assertEqual(result, "b" * 40)
        self.assertEqual(publisher.report.status, "COMPLETED")

    def test_non_success_creates_blocked_report(self):
        publisher = FakePublisher()
        EngineReportWriter(publisher, "worker-1", "0.1.0")(task("BLOCKED"), ExecutionOutcome(ExecutionStatus.BLOCKED, "credential missing"), object(), "a" * 40, "start", "end")
        self.assertEqual(publisher.report.reason_code, "BLOCKED")
        self.assertIn("credential missing", publisher.report.unsafe_reason)


if __name__ == "__main__":
    unittest.main()
