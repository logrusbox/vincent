import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from mission_control import vincent_cli
from mission_control.enrollment import initialize_identity, request_enrollment


class VincentCliTests(unittest.TestCase):
    def test_standalone_ready_without_provider_network_or_enrollment(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity = initialize_identity(root / 'identity')
            self.assertFalse((root / 'identity/enrollment-request.json').exists())
            ready = root / 'ready.json'
            ready.write_text(json.dumps({'schema_version': 1, 'state': 'READY',
                                         'worker_id': identity.worker_id, 'verified_at': 'test'}))
            with patch('socket.create_connection', side_effect=AssertionError('network prohibited')):
                with patch('shutil.which', return_value=None):
                    status = vincent_cli.local_status(root / 'identity', ready)
            self.assertEqual(status['local_state'], 'READY')
            self.assertFalse(status['provider_available'])
            enrolled = request_enrollment(root / 'identity')
            self.assertEqual(enrolled.worker_id, identity.worker_id)
            self.assertEqual(enrolled.fingerprint, identity.fingerprint)

    def test_missing_or_mismatched_readiness_does_not_claim_ready(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_identity(root / 'identity')
            ready = root / 'ready.json'
            self.assertEqual(vincent_cli.local_status(root / 'identity', ready)['local_state'], 'SETUP_REQUIRED')
            ready.write_text(json.dumps({'schema_version': 1, 'state': 'READY', 'worker_id': 'other'}))
            self.assertEqual(vincent_cli.local_status(root / 'identity', ready)['local_state'], 'SETUP_REQUIRED')

    def test_enrollment_rejects_substituted_public_key(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_identity(root / 'first')
            initialize_identity(root / 'other')
            (root / 'first/worker_ed25519.pub').write_text((root / 'other/worker_ed25519.pub').read_text())
            with self.assertRaisesRegex(RuntimeError, 'disagree'):
                request_enrollment(root / 'first')


if __name__ == '__main__':
    unittest.main()
