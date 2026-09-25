import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mission_control.cli import doctor, main
from mission_control.configuration import ConfigurationError, WorkerConfiguration


VALID = """[worker]
id = "worker-test-01"
poll_seconds = 30
[paths]
state_file = "/var/lib/mission-control/state.json"
workspace_root = "/srv/codex/worktrees"
identity_file = "/var/lib/mission-control/identity/identity.json"
[coordination]
checkout = "/srv/codex/platform"
branch = "main"
tasks_path = "coordination/tasks"
"""


class ConfigurationCliTests(unittest.TestCase):
    def config(self, content=VALID):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "worker.toml"
        path.write_text(content)
        return directory, path

    def test_loads_strict_configuration(self):
        directory, path = self.config()
        try:
            config = WorkerConfiguration.load(path)
            self.assertEqual(config.worker_id, "worker-test-01")
            self.assertEqual(config.poll_seconds, 30)
        finally:
            directory.cleanup()

    def test_provider_bound_is_explicit_and_validated(self):
        directory, path = self.config(VALID + '\n[provider]\nexecution_timeout_seconds = 45\n')
        try:
            self.assertEqual(WorkerConfiguration.load(path).provider_timeout_seconds, 45)
            for value in ('0', '-1', 'true', '"forty"'):
                path.write_text(VALID + '\n[provider]\nexecution_timeout_seconds = ' + value + '\n')
                with self.assertRaises(ConfigurationError):
                    WorkerConfiguration.load(path)
        finally:
            directory.cleanup()

    def test_relative_paths_are_rejected(self):
        directory, path = self.config(VALID.replace("/srv/codex/worktrees", "relative"))
        try:
            with self.assertRaises(ConfigurationError):
                WorkerConfiguration.load(path)
        finally:
            directory.cleanup()

    def test_doctor_reports_missing_codex(self):
        directory, path = self.config()
        try:
            config = WorkerConfiguration.load(path)
            with patch("mission_control.cli.shutil.which", side_effect=lambda name: "/usr/bin/git" if name == "git" else None):
                healthy, evidence = doctor(config)
            self.assertFalse(healthy)
            self.assertFalse(evidence["codex_available"])
        finally:
            directory.cleanup()

    def test_cli_returns_nonzero_when_dependency_missing(self):
        directory, path = self.config()
        try:
            with patch("mission_control.cli.shutil.which", return_value=None):
                self.assertEqual(main(["--config", str(path), "doctor"]), 1)
        finally:
            directory.cleanup()

    def test_enrollment_command_does_not_require_existing_config(self):
        with tempfile.TemporaryDirectory() as directory:
            identity_root = Path(directory) / "identity"
            self.assertEqual(
                main(["--identity-root", str(identity_root), "enroll"]), 0
            )
            self.assertTrue((identity_root / "enrollment-request.json").exists())


if __name__ == "__main__":
    unittest.main()
