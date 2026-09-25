import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'installer/debian13/payload.py'
spec = importlib.util.spec_from_file_location('payload', MODULE)
payload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(payload)
COMMIT = 'a' * 40


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'platform.tar.gz'
        self.manifest = self.root / 'manifest.json'
        self.destination = self.root / 'source'
        self.make_bundle()

    def make_bundle(self, extra=None, commit=COMMIT):
        with tarfile.open(self.bundle, 'w:gz', format=tarfile.PAX_FORMAT,
                          pax_headers={'comment': commit}) as archive:
            for name, data in [('VERSION', b'0.1.0\n'), ('BUILD_NUMBER', b'0023\n'),
                               ('installer/install.sh', b'#!/bin/sh\nexit 0\n')]:
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mode = 0o755 if name.endswith('.sh') else 0o644
                archive.addfile(member, io.BytesIO(data))
            if extra is not None:
                archive.addfile(extra)
        self.manifest.write_text(json.dumps({
            'schema_version': 1, 'platform_commit': COMMIT, 'installer_build': '0024',
            'runtime_version': '0.1.0', 'runtime_build': '0023',
            'sha256': hashlib.sha256(self.bundle.read_bytes()).hexdigest(),
        }))

    def unpack(self):
        return payload.unpack(self.bundle, self.manifest, COMMIT, '0024', self.destination)

    def test_verified_extraction_and_resume_preserve_build_evidence(self):
        self.unpack()
        evidence = self.destination / 'build-evidence.txt'
        evidence.write_text('preserve')
        self.unpack()
        self.assertEqual(evidence.read_text(), 'preserve')
        self.assertEqual((self.destination / 'installer/install.sh').stat().st_mode & 0o777, 0o755)

    def test_corruption_fails_before_destination_creation(self):
        self.bundle.write_bytes(self.bundle.read_bytes() + b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.unpack()
        self.assertFalse(self.destination.exists())

    def test_wrong_commit_build_and_runtime_identity_fail(self):
        self.make_bundle(commit='b' * 40)
        with self.assertRaisesRegex(ValueError, 'commit'):
            self.unpack()
        self.make_bundle()
        with self.assertRaisesRegex(ValueError, 'provenance'):
            payload.verify(self.bundle, self.manifest, COMMIT, '9999')
        metadata = json.loads(self.manifest.read_text())
        metadata['runtime_build'] = '9999'
        self.manifest.write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, 'runtime identity'):
            self.unpack()

    def test_traversal_links_devices_and_duplicates_are_rejected(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('/escape', tarfile.REGTYPE),
                           ('link', tarfile.SYMTYPE), ('device', tarfile.CHRTYPE),
                           ('VERSION', tarfile.REGTYPE)]:
            with self.subTest(name=name):
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = '/etc'
                self.make_bundle(extra=member)
                with self.assertRaisesRegex(ValueError, 'unsafe'):
                    self.unpack()
                self.assertFalse(self.destination.exists())

    def test_modified_source_is_preserved_and_blocks_resume(self):
        self.unpack()
        version = self.destination / 'VERSION'
        version.write_text('unexpected work')
        with self.assertRaisesRegex(ValueError, 'preserved'):
            self.unpack()
        self.assertEqual(version.read_text(), 'unexpected work')

    def test_existing_symlink_cannot_redirect_verification(self):
        self.unpack()
        version = self.destination / 'VERSION'
        version.unlink()
        version.symlink_to(self.manifest)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.unpack()


if __name__ == '__main__':
    unittest.main()
