import subprocess
import tempfile
import unittest
from pathlib import Path

from mission_control.codex_runner import CodexFailure, CodexRunner, classify_failure, retry_allowed


class CodexRunnerTests(unittest.TestCase):
    def test_builds_noninteractive_json_command_and_parses_events(self):
        observed = {}

        def process(command, **kwargs):
            observed["command"] = command
            observed.update(kwargs)
            return subprocess.CompletedProcess(command, 0, '{"type":"turn.completed"}\n', "")

        with tempfile.TemporaryDirectory() as directory:
            result = CodexRunner(process_runner=process, timeout_seconds=60).execute(Path(directory), "Implement task")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.events[0]["type"], "turn.completed")
        self.assertEqual(observed["command"], ["codex", "exec", "--json", "--sandbox", "workspace-write", "-"])
        self.assertEqual(observed["input"], "Implement task")

    def test_usage_limit_is_not_task_failure(self):
        self.assertEqual(classify_failure(1, "Usage limit reached"), CodexFailure.USAGE_LIMIT)

    def test_authentication_failure_is_distinct(self):
        self.assertEqual(classify_failure(1, "Not logged in"), CodexFailure.AUTHENTICATION_FAILURE)

    def test_only_transient_failures_receive_bounded_retry(self):
        self.assertTrue(retry_allowed(CodexFailure.TRANSIENT_CODEX_FAILURE, 1))
        self.assertFalse(retry_allowed(CodexFailure.TRANSIENT_CODEX_FAILURE, 3))
        self.assertFalse(retry_allowed(CodexFailure.USAGE_LIMIT, 1))

    def test_missing_executable_is_captured(self):
        def missing(*args, **kwargs):
            raise FileNotFoundError

        result = CodexRunner(process_runner=missing, timeout_seconds=60).execute(Path("."), "task")
        self.assertEqual(result.failure, CodexFailure.UNKNOWN_FAILURE)
        self.assertIsNone(result.exit_status)


if __name__ == "__main__":
    unittest.main()
