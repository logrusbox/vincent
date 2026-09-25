import json
from pathlib import Path
import tempfile
import unittest
from mission_control.versioning import version_info

class VersioningTests(unittest.TestCase):
    def test_runtime_and_installer_counters_are_independent(self):
        with tempfile.TemporaryDirectory() as d:
            manifest=Path(d)/'manifest.json'
            manifest.write_text(json.dumps({'installer_version':'0.0.9','installer_build':'0007',
                'runtime_version':'0.0.8','runtime_build':'0006','platform_commit':'a'*40}))
            info=version_info(manifest)
            root=Path(__file__).parents[1]
            self.assertEqual(info['runtime']['build'],(root/'BUILD_NUMBER').read_text().strip())
            self.assertEqual(info['installer']['build'],'0007')
            self.assertEqual(info['installer']['original_runtime_build'],'0006')

    def test_missing_installer_is_not_inferred_from_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(version_info(Path(d)/'missing')['installer'])
