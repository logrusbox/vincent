from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from mission_control.authorization import AuthorizationError, ExecutionAuthority, repository_identity
from mission_control.project_executor import ProjectExecutorFactory
from test_models import valid_task
from mission_control.models import Task


class AuthorizationTests(unittest.TestCase):
    def task(self, repository='logrusbox/vincent'):
        return Task.from_mapping(valid_task(repository=repository))

    def test_unconfigured_or_out_of_scope_denied_before_workspace(self):
        workspace = Mock()
        factory = ProjectExecutorFactory('worker-1', workspace, Mock())
        with self.assertRaises(AuthorizationError):
            factory(self.task())
        workspace.prepare.assert_not_called()
        authority = ExecutionAuthority('worker-1', 'standalone', ('logrusbox/cic-station',))
        with self.assertRaises(AuthorizationError):
            authority.require(self.task())

    def test_equivalent_git_locators_and_strict_repository_boundaries(self):
        authority = ExecutionAuthority('worker-1', 'standalone', ('logrusbox/vincent',))
        for locator in ('logrusbox/vincent', 'https://github.com/logrusbox/vincent.git',
                        'git@github.com:logrusbox/vincent.git'):
            authority.require(self.task(locator))
        for locator in ('https://github.com.evil.invalid/logrusbox/vincent',
                        'https://github.com/logrusbox/vincent-extra',
                        'https://user:pass@github.com/logrusbox/vincent',
                        'https://github.com/logrusbox/%76incent',
                        'https://github.com/logrusbox/vincent?redirect=elsewhere'):
            with self.subTest(locator=locator), self.assertRaises(AuthorizationError):
                authority.require(self.task(locator))

    def test_managed_grant_checks_identity_revocation_expiry_and_scope(self):
        expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
        grant = {'schema_version': 1, 'worker_id': 'worker-1', 'status': 'active',
                 'expires_at': expiry, 'repository_scopes': ['logrusbox/vincent']}
        authority = ExecutionAuthority('worker-1', 'managed', grant_path=Path('/etc/vincent/grant.json'))
        with patch('mission_control.authorization.read_protected_grant', return_value=grant):
            authority.require(self.task())
        for change in ({'worker_id': 'other'}, {'status': 'revoked'}, {'expires_at': '2020-01-01T00:00:00Z'},
                       {'repository_scopes': []}, {'repository_scopes': ['logrusbox/other']},
                       {'expires_at': None}, {'schema_version': True}):
            with patch('mission_control.authorization.read_protected_grant', return_value={**grant, **change}):
                with self.assertRaises(AuthorizationError):
                    authority.require(self.task())

    def test_local_scope_cannot_follow_a_changed_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'first').mkdir()
            (root / 'second').mkdir()
            alias = root / 'alias'
            alias.symlink_to(root / 'first')
            authority = ExecutionAuthority('worker-1', 'standalone', (str(alias),))
            with self.assertRaises(AuthorizationError):
                authority.require(self.task(str(root / 'first')))
            alias.unlink()
            alias.symlink_to(root / 'second')
            with self.assertRaises(AuthorizationError):
                authority.require(self.task(str(root / 'second')))

    def test_missing_managed_grant_never_uses_standalone_scopes(self):
        authority = ExecutionAuthority('worker-1', 'managed', ('logrusbox/vincent',))
        with self.assertRaises(AuthorizationError):
            authority.require(self.task())

    def test_managed_file_in_worker_writable_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            grant = Path(d) / 'grant.json'
            grant.write_text('{}')
            grant.chmod(0o666)
            authority = ExecutionAuthority('worker-1', 'managed', grant_path=grant)
            with self.assertRaises(AuthorizationError):
                authority.require(self.task())


if __name__ == '__main__':
    unittest.main()
