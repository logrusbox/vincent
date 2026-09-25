import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('installer', Path(__file__).parents[1] / 'bootstrap/install-provider.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ProviderInstallTests(unittest.TestCase):
    def fixture(self, root):
        artifacts = {}
        for name in installer.NAMES:
            source = root / name
            source.write_bytes(b'reviewed-test-fixture-' + name.encode())
            artifacts[name] = {'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
        manifest = root / 'manifest.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'provider': 'codex', 'version': '0.1.0', 'artifacts': artifacts}))
        return manifest

    def test_complete_runtime_installs_atomically_and_resumes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest=self.fixture(root);target=root/'installed'
            release=installer.install(manifest,target)
            self.assertEqual((target/'bin').resolve(),release)
            for name in installer.NAMES:
                self.assertEqual((target/'bin'/name).read_bytes(),(root/name).read_bytes())
            self.assertEqual(installer.install(manifest,target),release)

    def test_bad_companion_does_not_replace_active_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest=self.fixture(root);target=root/'installed'
            release=installer.install(manifest,target)
            (root/'codex-code-mode-host').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                installer.install(manifest,target)
            self.assertEqual((target/'bin').resolve(),release)

    def test_tampered_installed_runtime_is_not_silently_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest=self.fixture(root);target=root/'installed'
            release=installer.install(manifest,target)
            (release/'codex').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'release differs'):
                installer.install(manifest,target)

    def test_manifest_requires_both_expected_digests(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest=self.fixture(root)
            data=json.loads(manifest.read_text());del data['artifacts']['codex-code-mode-host']
            manifest.write_text(json.dumps(data))
            with self.assertRaises(ValueError):installer.install(manifest,root/'installed')
