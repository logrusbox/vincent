import unittest

from mission_control.models import ProtocolError, Task, TaskState


def valid_task(**changes):
    data = {
        "schema_version": 1,
        "task_id": "MCP-001",
        "project_id": "vincent",
        "repository": "Gordonfive/vincent",
        "base_branch": "main",
        "objective": "Test protocol parsing.",
        "acceptance_criteria": ["pytest"],
        "state": "QUEUED",
        "revision": 1,
        "created_at": "2026-08-24T20:00:00Z",
    }
    data.update(changes)
    return data


class TaskModelTests(unittest.TestCase):
    def test_parses_executable_validation_and_publish_contract(self):
        data = valid_task()
        data["validation_commands"] = [["python3", "-m", "unittest"]]
        data["publish_paths"] = ["worker/"]
        task = Task.from_mapping(data)
        self.assertEqual(task.validation_commands, (("python3", "-m", "unittest"),))
        self.assertEqual(task.publish_paths, ("worker/",))
        self.assertEqual(task.to_mapping()["validation_commands"], [["python3", "-m", "unittest"]])

    def test_rejects_unknown_priority_and_invalid_time(self):
        for priority in ("urgent", "normal", "HIGH ", "", 1):
            with self.subTest(priority=priority), self.assertRaises(ProtocolError):
                Task.from_mapping(valid_task(priority=priority))
        for created in ("yesterday", "2026-02-30T00:00:00Z", "2026-01-01T00:00:00",
                        "2026-01-01T00:00:00+01:00", "2026-01-01T00:00:60Z",
                        "2026-01-01T00:00:00.1234567Z"):
            with self.subTest(created=created), self.assertRaises(ProtocolError):
                Task.from_mapping(valid_task(created_at=created))
        for version in (True, 1.0):
            with self.assertRaises(ProtocolError):
                Task.from_mapping(valid_task(schema_version=version))

    def test_parses_valid_task(self):
        task = Task.from_mapping(valid_task())
        self.assertIs(task.state, TaskState.QUEUED)
        self.assertEqual(task.integration_policy, "HUMAN_APPROVAL_REQUIRED")

    def test_rejects_unknown_schema_version(self):
        with self.assertRaisesRegex(ProtocolError, "unsupported schema_version"):
            Task.from_mapping(valid_task(schema_version=2))

    def test_rejects_empty_acceptance_contract(self):
        with self.assertRaisesRegex(ProtocolError, "must not be empty"):
            Task.from_mapping(valid_task(acceptance_criteria=[]))

    def test_active_task_requires_complete_claim(self):
        with self.assertRaisesRegex(ProtocolError, "requires claim_worker_id"):
            Task.from_mapping(valid_task(state="ACTIVE"))

    def test_rejects_partial_claim(self):
        with self.assertRaisesRegex(ProtocolError, "must be set together"):
            Task.from_mapping(valid_task(claim_worker_id="worker-01"))

    def test_rejects_unimplemented_unattended_recovery_policy(self):
        with self.assertRaisesRegex(ProtocolError, "can_continue_unattended=true"):
            Task.from_mapping(valid_task(can_continue_unattended=True))

    def test_rejects_unimplemented_forbidden_action_policy(self):
        with self.assertRaisesRegex(ProtocolError, "not mechanically enforceable"):
            Task.from_mapping(valid_task(forbidden_actions=["do not deploy"]))

    def test_rejects_unknown_integration_policy(self):
        with self.assertRaisesRegex(ProtocolError, "unsupported integration_policy"):
            Task.from_mapping(valid_task(integration_policy="AUTO_MERGE"))


if __name__ == "__main__":
    unittest.main()
